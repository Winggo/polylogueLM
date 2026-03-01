'use client'

import React, { useCallback, useRef, useEffect, useState, useMemo } from 'react'
import { usePathname } from 'next/navigation'
import {
    ReactFlow,
    Background,
    addEdge,
    useEdgesState,
    useNodesState,
    useReactFlow,
    MarkerType,
    PanOnScrollMode,
    type Connection,
    type Node,
    type Edge,
    XYPosition,
} from '@xyflow/react'
import { Fade } from "react-awesome-reveal"
import { nanoid } from 'nanoid'
import { useMediaQuery } from "react-responsive"
import { Modal, Input, Tooltip, message } from "antd"
import { CopyFilled } from "@ant-design/icons"

import { useTheme } from "../../context/ThemeContext"
import LLMNode from "../LLMNode/LlmNode"
import ImageNode from "../ImageNode/ImageNode"
import CanvasInfo from "./CanvasInfo"
import AnimatedConnectionLine from "./AnimatedConnectionLine"
import {
    llmNodeSize,
    llmNewNodeDeltaX,
    imageNodeSize,
    backendServerURL,
} from "../../utils/constants"


const nodeTypes = {
    llmText: LLMNode,
    imageNode: ImageNode,
}


type createNewLlmTextNodeParams = {
    position: { x: number, y: number },
    selected?: boolean,
    origin?: [number, number] | null,
    data?: object,
}

function createNewLlmTextNode(
    {position, selected=true, origin, data={}}
    : createNewLlmTextNodeParams): ExtendedNode {
    const newNode = {
        id: nanoid(10),
        position,
        type: 'llmText',
        data: data as ExtendedNodeData,
        selected,
        origin: origin ?? [0, 0],
        measured: llmNodeSize,
    }
    return newNode
}

function createNewImageNode({
    position,
    imageDataUrl,
    fileName,
    data = {},
}: {
    position: { x: number, y: number },
    imageDataUrl: string,
    fileName: string,
    data?: object,
}): ExtendedNode {
    return {
        id: nanoid(10),
        position,
        type: 'imageNode',
        data: { imageDataUrl, fileName, ...data } as ExtendedNodeData,
        selected: true,
        origin: [0, 0],
        measured: imageNodeSize,
    }
}

export type ExtendedNodeData = {
    model?: string,
    prompt?: string,
    prompt_response?: string,
    parent_ids?: Array<string>,
    imageDataUrl?: string,
    fileName?: string,
    setNode: (nodeId: string, newData: ExtendedNodeData, selected: boolean) => void,
    createNextNode: (fromNodeId: string, newNodePosition: XYPosition, newNodeData: object) => ExtendedNode,
    canvasId: string,
}

export type ExtendedNode = Node & {
    id: string,
    type: string,
    position: {
        x: number,
        y: number,
    },
    data: ExtendedNodeData,
    selected: boolean,
    measured: {
        width: number,
        height: number,
    },
    origin: number[],
}

type FlowProps = {
    canvasId: string,
    canvasTitle?: string,
    existingNodes?: ExtendedNode[],
    newCanvas?: boolean,
}


function createEdge(sourceId: string, targetId: string) {
    return {
        id: `edge-${sourceId}-${targetId}`,
        source: sourceId,
        target: targetId,
        markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 20,
            height: 20,
            color: 'currentColor',
        },
    }
}


export default function Flow({ canvasId, canvasTitle, existingNodes, newCanvas }: FlowProps) {
    const pathname = usePathname()
    const { theme } = useTheme()
    const reactFlowInstance = useReactFlow()
    const reactFlowWrapper = useRef<HTMLDivElement | null>(null)
    const isMobile = useMediaQuery({ maxWidth: 768 })
    const [messageApi, contextHolder] = message.useMessage()
    const [flowRendered, setFlowRendered] = useState(false)
    const [cursorPosition, setCursorPosition] = useState({ x: 0, y: 0 })
    const [savingCanvas, setSavingCanvas] = useState(false)
    const [saveModalOpen, setSaveModalOpen] = useState(false)
    const [copyTooltipText, setCopyTooltipText] = useState("Copy Link")
    const [nodes, setNodes, onNodesChange] = useNodesState<ExtendedNode>([])
    const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])

    const animatedEdges = useMemo(() => {
        const emptyNodeIds = new Set(
            nodes.filter(n => !n.data.prompt_response).map(n => n.id)
        )
        return edges.map(e => ({ ...e, animated: emptyNodeIds.has(e.target) }))
    }, [edges, nodes])

    const setNode = useCallback((nodeId: string, newData: ExtendedNodeData | object, selected: boolean) => {
        setNodes((nds) =>
            nds.map((node) => {
                if (node.id === nodeId) {
                    return {
                        ...node,
                        selected: selected ?? node.selected,
                        data: {
                            ...node.data,
                            ...newData,
                        }
                    }
                }
                return node
            })
        )
    }, [setNodes])

    // Existing nodes present, create edges & pass down setNodes for them
    useEffect(() => {
        if (existingNodes) {
            const edgesForExistingNodes: Edge[] = []
            for (const exNode of existingNodes) {
                if (exNode.data.parent_ids && exNode.data.parent_ids.length > 0) {
                    for (const parentId of exNode.data.parent_ids) {
                        edgesForExistingNodes.push(
                            createEdge(parentId, exNode.id)
                        )
                    }   
                }
            }
            setNodes((nds) => nds.concat(existingNodes || []).map((node) => ({
                ...node,
                data: {
                    ...node.data,
                    setNode,
                    createNextNode,
                    canvasId,
                }
            })))
            setEdges((eds) => {
                const existingIds = new Set(eds.map(e => e.id))
                return eds.concat(edgesForExistingNodes.filter(e => !existingIds.has(e.id)))
            })
            reactFlowInstance.fitView({ minZoom: 0.5, maxZoom: 0.9 })
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [existingNodes])

    // Upon new canvas, create single node in center of canvas
    useEffect(() => {
        if (!newCanvas || !canvasId) return
        if (!reactFlowWrapper?.current) return
        const { width, height } = reactFlowWrapper.current.getBoundingClientRect()
        const position = {
            x: ((width / 2) - (llmNodeSize.width / 2)) * (1 / 1.28), // account for 0.9 zoom
            y: (height / 2) * (1 / 1.2),
        };

        const newNode = createNewLlmTextNode({
            position,
            data: { setNode, createNextNode, canvasId },
            origin: [0.0, 0.5],
        })

        reactFlowInstance.addNodes(newNode)

        if (isMobile) {
            reactFlowInstance.fitView()
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [canvasId])

    // Create new node on Cmd/Ctrl + '
    useEffect(() => {
        const handleMouseMove = (event: MouseEvent) => {
            setCursorPosition({ x: event.clientX, y: event.clientY })
        }
        
        const handleKeyDown = (event: KeyboardEvent) => {
            if ((event.metaKey || event.ctrlKey) && event.key === '\'') {
                event.preventDefault()

                const nodePosition = reactFlowInstance.screenToFlowPosition({
                    x: cursorPosition.x,
                    y: cursorPosition.y,
                })
                const newNode = createNewLlmTextNode({
                    position: nodePosition,
                    data: { setNode, createNextNode, canvasId },
                })
                setNodes((nds) => {
                    return nds.map((n) => {
                        return { ...n, selected: false }
                    }).concat({ ...newNode, selected: true }) 
                })
            }
        }

        window.addEventListener('mousemove', handleMouseMove)
        window.addEventListener('keydown', handleKeyDown)
        return () => {
            window.removeEventListener('mousemove', handleMouseMove)
            window.removeEventListener('keydown', handleKeyDown)
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [setNodes, cursorPosition, reactFlowInstance])

    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            if ((event.metaKey || event.ctrlKey) && event.key === '\\') {
                event.preventDefault()
                reactFlowInstance.fitView()
            }
        }

        window.addEventListener('keydown', handleKeyDown)
        return () => {
            window.removeEventListener('keydown', handleKeyDown)
        }
    }, [reactFlowInstance])

    const handleSaveCanvas = async ({ curCanvasTitle }: { curCanvasTitle: string }) => {
        setSavingCanvas(true)
        try {
            const saveNodes = nodes.map((node) => ({
                id: node.id,
                type: node.type,
                position: node.position,
                data: node.data,
                selected: node.selected,
                measured: node.measured,
                origin: node.origin,
            }))
            const response = await fetch(`${backendServerURL}/ds/v1/canvases`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    canvasId,
                    title: curCanvasTitle,
                    nodes: saveNodes,
                }),
            })
            if (response.status === 200) {
                messageApi.open({
                    type: 'success',
                    content: 'Saved successfully!',
                    duration: 5,
                    style: {
                        marginTop: '50px',
                    },
                })
                setSaveModalOpen(true)
            } else {
                messageApi.error({
                    content: 'Cannot save canvas. Please try again in a moment.',
                    duration: 5,
                    style: {
                        marginTop: '50px',
                    },
                })
            }
        } catch {
            messageApi.error({
                content: 'Cannot save canvas. Please try again in a moment.',
                duration: 5,
                style: {
                    marginTop: '50px',
                },
            })
        } finally {
            setSavingCanvas(false)
        }
    }

    const createNextNode = useCallback(
        (fromNodeId: string, newNodePosition: XYPosition, newNodeData: object = {}) => {
            const newNode = createNewLlmTextNode({
                position: newNodePosition,
                origin: [0.0, 0.5],
                data: {
                    ...newNodeData,
                    setNode,
                    createNextNode,
                    canvasId,
                },
            })
            setNodes((nds) => nds.concat(newNode))

            const newEdge: Edge = createEdge(fromNodeId, newNode.id)
            setEdges((eds) => [...eds, newEdge])

            return newNode
        },
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [setNodes, setEdges, canvasId]
    )

    const handleDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
        event.preventDefault()
        event.dataTransfer.dropEffect = 'copy'
    }, [])

    const handleDrop = useCallback((event: React.DragEvent<HTMLDivElement>) => {
        event.preventDefault()
        const files = Array.from(event.dataTransfer.files)
        const imageFile = files.find(f =>
            f.type === 'image/png' || f.type === 'image/jpeg'
        )
        if (!imageFile) return

        const dropPosition = reactFlowInstance.screenToFlowPosition({
            x: event.clientX,
            y: event.clientY,
        })

        const reader = new FileReader()
        reader.onload = (e) => {
            const imageDataUrl = e.target?.result as string
            const newNode = createNewImageNode({
                position: dropPosition,
                imageDataUrl,
                fileName: imageFile.name,
                data: { setNode, createNextNode, canvasId },
            })
            setNodes((nds) => nds.map((n) => ({ ...n, selected: false })).concat(newNode))
        }
        reader.readAsDataURL(imageFile)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [reactFlowInstance, setNode, createNextNode, canvasId, setNodes])

    const handlePaneDoubleClick = useCallback((event: React.MouseEvent) => {
        if (event.detail !== 2) return
        const nodePosition = reactFlowInstance.screenToFlowPosition({
            x: event.clientX,
            y: event.clientY,
        })
        const newNode = createNewLlmTextNode({
            position: nodePosition,
            data: { setNode, createNextNode, canvasId },
            origin: [0, 0],
        })
        setNodes((nds) => nds.map((n) => ({ ...n, selected: false })).concat({ ...newNode, selected: true }))
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [reactFlowInstance, setNode, createNextNode, canvasId, setNodes])

    const onConnect = useCallback(
        (connection: Connection) => setEdges(
            (eds) => {
                const newEdge: Edge = createEdge(connection.source, connection.target)
                return addEdge(newEdge, eds)
            }
        ),
        [setEdges],
    )

    const onConnectEnd = useCallback(
        (
            event: MouseEvent | TouchEvent,
            connectionState: { isValid: boolean | null; fromNode: Node | null }
        ) => {
            if (!connectionState.isValid && connectionState.fromNode !== null) {
                const { clientX, clientY } =
                    'changedTouches' in event ? event.changedTouches[0] : event
                const nodePosition = reactFlowInstance.screenToFlowPosition({
                    x: clientX,
                    y: clientY,
                })

                // Clicked on right handle, set the new node position
                const rightDeltaX = nodePosition.x - connectionState.fromNode.position.x
                const deltaY = Math.abs(nodePosition.y - connectionState.fromNode.position.y)
                if (((rightDeltaX - llmNodeSize.width) < 50) && deltaY < 100) {
                    nodePosition.x += llmNewNodeDeltaX
                    nodePosition.y -= llmNodeSize.height/2 + 40
                }

                const nextNode = createNextNode(
                    connectionState.fromNode.id,
                    nodePosition,
                    { model: connectionState.fromNode.data.model }
                )

                if (isMobile) {
                    reactFlowInstance.setCenter(
                        nodePosition.x + llmNodeSize.width/2,
                        nodePosition.y,
                        { duration: 1000, zoom: 0.5 }
                    )
                } else {
                    reactFlowInstance.fitView({
                        nodes: [{ id: connectionState.fromNode.id }, { id: nextNode.id }],
                        duration: 1000,
                        padding: 0.07,
                    })
                }
            }
        },
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [reactFlowInstance, setEdges, setNodes],
    )

    const renderSaveModal = () => {
        return (
            <Modal
                title="Save this canvas link to continue the conversation 💡"
                centered
                closable={false}
                open={saveModalOpen}
                onOk={() => setSaveModalOpen(false)}
                okText="Got it"
                okType="default"
                okButtonProps={{
                    style: {
                        border: '2px solid gray',
                        boxShadow: '0px 4px 15px rgba(0, 0, 0, 0.1)',
                        fontFamily: 'Barlow',
                        fontWeight: 500,
                    }
                }}
                cancelButtonProps={{ style: { display: 'none' } }}
                afterClose={() => {
                    setCopyTooltipText("Copy Link")
                    if (pathname === "/canvas") {
                        window.history.replaceState(null, '', `/canvas/${canvasId}`)
                    }
                }}
            >
                <p className="mb-[5px]">Or... have your friends chime in</p>
                <Input
                    value={`https://polylogue.dev/canvas/${canvasId}`}
                    variant='filled'
                    suffix={
                        <Tooltip
                            title={copyTooltipText}
                        >
                            <CopyFilled
                                onClick={() => {
                                    navigator.clipboard.writeText(`https://polylogue.dev/canvas/${canvasId}`)
                                    setCopyTooltipText("Copied!")
                                }}
                            />
                        </Tooltip>
                    }
                />
            </Modal>
        )
    }

    return (
        <Fade delay={0} duration={2000} cascade damping={0.5} triggerOnce>
            <div className="h-screen w-screen bg-gray-200 dark:bg-neutral-800" ref={reactFlowWrapper}>
                {contextHolder}
                <ReactFlow
                    onInit={() => setFlowRendered(true)}
                    onPaneClick={handlePaneDoubleClick}
                    zoomOnDoubleClick={false}
                    nodes={nodes}
                    edges={animatedEdges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onConnect={onConnect}
                    onConnectEnd={onConnectEnd}
                    onDragOver={handleDragOver}
                    onDrop={handleDrop}
                    preventScrolling={false}
                    panOnScroll
                    panOnScrollMode={PanOnScrollMode.Free}
                    nodeTypes={nodeTypes}
                    connectionLineComponent={AnimatedConnectionLine}
                    defaultEdgeOptions={{ markerEnd: { type: MarkerType.ArrowClosed, width: 20, height: 20, color: 'currentColor' } }}
                    colorMode={theme}
                    defaultViewport={{ x: 0, y: 0, zoom: 1.2 }}
                >
                    <Background gap={25} />
                    {flowRendered && (
                        <CanvasInfo
                            canvasId={canvasId}
                            canvasTitle={canvasTitle}
                            handleSaveCanvas={handleSaveCanvas}
                            savingCanvas={savingCanvas}
                            newCanvas={newCanvas}
                        />
                    )}
                </ReactFlow>
            </div>
            {renderSaveModal()}
        </Fade>
    )
}