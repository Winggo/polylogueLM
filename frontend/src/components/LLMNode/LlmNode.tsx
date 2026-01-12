'use client'

import { useState, useRef, useEffect } from "react"
import {
    Handle,
    Position,
    NodeToolbar,
    useNodeConnections,
    useNodesData,
    useReactFlow,
    type Node,
} from '@xyflow/react'
import { Skeleton, Tooltip } from "antd"
import ReactMarkdown from 'react-markdown'

import LLMNodeCard from "./LLMNodeCard"
import RightArrowCircle from "../../icons/RightArrowCircle"
import DottedSquare from "../../icons/DottedSquare"
import DownArrowCircle from "../../icons/DownArrowCircle"
import {
    backendServerURL,
    llmNodeSize,
    llmNewNodeDeltaX,
} from "../../utils/constants"


type LLMNodeProps = {
    id: string
    selected: boolean
    data: Record<string, any> // eslint-disable-line @typescript-eslint/no-explicit-any
    positionAbsoluteX: number
    positionAbsoluteY: number
}

const initialModel = "llama_8b"
const models = [
    { value: "llama_8b", label: "Meta Llama" },
    { value: "mixtral_56b", label: "MistralAI Mixtral" },
    { value: "openai_120b", label: "OpenAI GPT" },
]
const modelMapping = {
    "llama_8b": "Meta Llama",
    "mixtral_56b": "MistralAI Mixtral",
    "openai_120b": "OpenAI GPT",
}

export default function LLMNode ({
    id: nodeId,
    selected,
    data={},
    positionAbsoluteX,
    positionAbsoluteY,
}: LLMNodeProps) {
    const {
        model: existingModel,
        prompt: exstingPrompt,
        prompt_response: existingResponse,
        setNode,
        createNextNode,
        canvasId,
    } = data

    const inputRef = useRef<HTMLTextAreaElement>(null)
    const reactFlowInstance = useReactFlow()

    const [placeholder, setPlaceholder] = useState("")
    const [curPlaceholder, setCurPlaceholder] = useState("⇥ ")
    const [placeholderIndex, setPlaceholderIndex] = useState(0)

    const [model, setModel] = useState<keyof typeof modelMapping>(existingModel || initialModel)
    const [prompt, setPrompt] = useState(exstingPrompt || "")
    
    const [promptResponse, setPromptResponse] = useState(existingResponse || "")

    const [loading, setLoading] = useState(false)
    const [isHovered, setIsHovered] = useState(false)

    const connections = useNodeConnections({
        handleType: 'target',
    })
    const parentNodes = useNodesData<Node>(
        connections.map((connection) => connection.source),
    )

    useEffect(() => {
        if (selected) {
            setTimeout(() => {
                inputRef.current?.focus()
            }, 0)
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    const fetchPrompt = async (signal: AbortSignal ) => {
        try {
            const response = await fetch(`${backendServerURL}/api/v1/prompt`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    parentNodes,
                }),
                signal,
            })
            const { prompt } = await response.json()
            setPlaceholder(prompt)
        } catch {
        }
    }

    // Fetch prompt suggestion on creation
    useEffect(() => {
        if (prompt) return

        // Prevent fetching twice
        const controller = new AbortController()
        const signal = controller.signal
        fetchPrompt(signal)
        return () => {
            controller.abort()
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    // Add prompt suggestion incremental typing affect
    useEffect(() => {
        if (prompt) return

        if (placeholder && placeholderIndex < placeholder.length) {
            const timer = setTimeout(() => {
                setCurPlaceholder(curPlaceholder + placeholder[placeholderIndex])
                setPlaceholderIndex(placeholderIndex + 1)
            }, 20)
            return () => {
                clearTimeout(timer)
            }
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [curPlaceholder, placeholderIndex, placeholder])

    // Update ReactFlow nodes state every time node state is updated
    useEffect(() => {
        if (!setNode) return
        setNode(nodeId, {
            model,
            prompt,
            prompt_response: promptResponse,
            parent_ids: parentNodes.map((nd) => nd.id),
        })
    }, [setNode, nodeId, model, prompt, promptResponse, parentNodes])

    const submitPrompt = async () => {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 15000)
        setLoading(true)

        try {
            const response = await fetch(`${backendServerURL}/api/v1/completion`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    model,
                    prompt,
                    nodeId,
                    parentNodes,
                    canvasId,
                }),
                signal: controller.signal,
            })
            const data = await response.json()
            setPromptResponse(data.response)

            // Deselect current node & auto-create follow up node
            // Add delay to allow promptResponse to be updated in parent node
            setTimeout(() => {
                setNode(nodeId, {}, false)
                const nextNode = createNextNode(
                    nodeId,
                    {
                        x: positionAbsoluteX + llmNodeSize.width + llmNewNodeDeltaX,
                        y: positionAbsoluteY + llmNodeSize.height + 40,
                    },
                    { model }
                )
                reactFlowInstance.fitView({
                    nodes: [{ id: nodeId }, { id: nextNode.id }],
                    duration: 1000,
                    padding: 0.07,
                })
            }, 200)
        } catch {
            setPromptResponse("An error occurred. Please try again.")
        } finally {
            clearTimeout(timeoutId)
            setLoading(false)
        }
    }

    const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => setPrompt(e.target.value)
    const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => setModel(e.target.value as keyof typeof modelMapping)

    const renderModelDropdown = () => {
        if (!selected && !isHovered) return
        return (
            <NodeToolbar isVisible className="top-[-16px] bg-gray-800 p-1 pr-1.5 rounded-[16px]">
                <select
                    value={model}
                    onChange={handleModelChange}
                    className={`
                        bg-gray-800
                        border-none
                        text-white
                        py-1
                        px-3
                        rounded-md
                        focus:outline-none
                    `}
                >
                    <option value="" disabled>Select a model</option>
                    {models.map((model) => (
                        <option key={model.value} value={model.value} disabled={model.apiKeyRequired}>
                            {model.apiKeyRequired ? `${model.label} (Future feature)` : model.label}
                        </option>
                    ))}
                </select>
            </NodeToolbar>
        )
    }

    const renderHandles = () => {
        const connectableStart = promptResponse !== ""
        return (
            <>
                <Handle
                    id={nodeId}
                    type="target"
                    isConnectable
                    isConnectableStart={false}
                    position={Position.Left}
                    className={`w-4 h-4 mt-[4px] rounded-lg !bg-white border-gray-800 border-2 !cursor-pointer`}
                />
                <Tooltip
                            title={<span className="text-sm">Click to start a branching conversation</span>}
                            placement="top"
                            mouseLeaveDelay={0}
                        >
                    <Handle
                        id={nodeId}
                        type="source"
                        isConnectable={connectableStart}
                        isConnectableEnd={false}
                        position={Position.Right}
                        className={`w-12 h-12 mt-[4px] rounded-lg !bg-transparent border-gray-800 !cursor-pointer`}
                        onClick={() => {
                            // Deselect current node after creating new one
                            setTimeout(() => {
                                setNode(nodeId, {}, false)
                            }, 0)
                        }}
                    >
                        {connectableStart && <RightArrowCircle />}
                    </Handle>
                </Tooltip>
            </>
        )
    }

    const renderHeaders = () => (
        <>
            <DottedSquare />
            <div className="absolute top-[-26px] right-[30px] w-[300px] h-[20px] text-black pointer-events-none text-right">
                {modelMapping[model]}
            </div>
        </>
    )

    const renderPromptInput = () => (
        <>
            <div className="flex justify-between">
                <textarea
                    ref={inputRef}
                    placeholder={curPlaceholder}
                    value={prompt}
                    onChange={handleInputChange}
                    onKeyDown={(e) => {
                        if (e.key === "Enter") {
                            e.preventDefault()
                            if (prompt !== "") {
                                submitPrompt()
                            }
                        } else if (e.key === "Tab" && prompt === "") {
                            e.preventDefault()
                            setPrompt(placeholder)
                        }
                    }}
                    className={`
                        h-8
                        pt-1
                        mr-1
                        flex-grow
                        focus:outline-none
                        resize-none
                    `}
                    rows={1}
                    onInput={(e) => {
                        const target = e.target as HTMLTextAreaElement
                        target.style.height = "32px"
                        target.style.height = `${target.scrollHeight}px`
                    }}
                ></textarea>
                {(selected || isHovered) ?
                    <DownArrowCircle onClick={() => submitPrompt()} loading={loading} /> :
                    <div className="h-[32px] w-[32px]"></div>
                }
            </div>
            <div className={`border-t border-gray-300 mt-1 mb-1 group-focus-within:border-gray-800`}></div>
        </>
    )

    const renderOutput = () => {
        if (loading) {
            return <Skeleton active paragraph={{rows: 10}} className="mt-[10px]" />
        } else if (promptResponse) {
            return (
                <div className="prompt-output p-1.5 w-full focus:outline-none resize-none select-text cursor-text">
                    <ReactMarkdown>{promptResponse}</ReactMarkdown>
                </div>
            )
        } else {
            return <LLMNodeCard />
        }
    }

    return (
        <div
            className="group"
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
        >
            {renderModelDropdown()}
            {renderHandles()}
            {renderHeaders()}
            <div className={`
                w-[650px]
                h-[700px]
                bg-white
                text-black
                border-gray-800
                rounded-[30px]
                shadow-xl
                ${isHovered && !selected && "outline-[2px] outline-orange-500"}
                ${selected && "outline-[2px] shadow-2xl"}
                group-focus-within:outline-[2px] shadow-2xl
                flex
                p-3
                flex-col
                cursor-default
                overflow-hidden
                nodrag
            `}>
                {renderPromptInput()}
                <div className="overflow-y-auto h-full flex">
                    {renderOutput()}
                </div>
            </div>
            {(promptResponse && 
                <div className="absolute left-1/2 -translate-x-1/2 mt-[3px] italic text-gray-700 whitespace-nowrap">
                    To start a branching conversation, click on the ⮕ icon
                </div>
            )}
        </div>
    )
}
