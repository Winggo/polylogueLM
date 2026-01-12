import { useState, useEffect } from "react"
import { useRouter } from 'next/navigation'
import { Controls, ControlButton, Panel, useStore } from "@xyflow/react"
import { useMediaQuery } from "react-responsive"
import { Button, Tooltip, Input, Popconfirm } from "antd"
import { WarningOutlined } from "@ant-design/icons"
import '@ant-design/v5-patch-for-react-19'

import CopyIcon from "../../icons/CopyIcon"


const selector = (s: { transform: [number, number, number] }) => s.transform
const polylogue = ['P', 'o', 'l', 'y', 'l', 'o', 'g', 'u', 'e']

type CanvasInfo = {
    canvasId?: string,
    canvasTitle?: string,
    handleSaveCanvas: ({ curCanvasTitle }: { curCanvasTitle: string }) => void,
    savingCanvas: boolean,
}

export default function CanvasInfo({ canvasId, canvasTitle, handleSaveCanvas, savingCanvas }: CanvasInfo) { 
    const router = useRouter()
    const isMobile = useMediaQuery({ maxWidth: 768 })
    const [x, y, zoom] = useStore(selector)
    const [curBrand, setCurBrand] = useState("")
    const [curCanvasTitle, setCurCanvasTitle] = useState("[Your Canvas]")
    const [copyTooltipTitle, setCopyTooltipTile] = useState("Copy canvas ID")

    useEffect(() => {
        if (curBrand !== 'Polylogue') {
            const timer = setTimeout(() => {
                setCurBrand(curBrand + polylogue[curBrand.length])
            }, 20)
            return () => {
                clearTimeout(timer)
            }
        }
    }, [curBrand])

    useEffect(() => {
        if (canvasTitle) {
            setCurCanvasTitle(canvasTitle)
        }
    }, [canvasTitle])

    const renderTopLeftPanel = () => {
        return (
            <Panel position="top-left" className="!z-5 text-black">
                <Popconfirm
                    title="Go to new canvas page"
                    description="Save your canvas before leaving!"
                    onConfirm={() => router.push("/canvas")}
                    onCancel={() => {}}
                    okText="Yes"
                    okType="default"
                    okButtonProps={{
                        style: {
                            border: '2px solid gray',
                            boxShadow: '0px 4px 15px rgba(0, 0, 0, 0.1)',
                            fontFamily: 'Barlow',
                            fontWeight: 500,
                        }
                    }}
                    cancelText="No"
                    icon={<WarningOutlined style={{ color: "red" }} />}
                >
                    <p className="text-2xl font-bold cursor-pointer">
                        {curBrand}
                    </p>
                </Popconfirm>
            </Panel>
        )
    }

    const renderTopCenterPanel = () => {
        if (isMobile) return
        return (
            <Panel position="top-center" className="top-center-panel">
                <Input
                    value={curCanvasTitle}
                    onChange={(e) => setCurCanvasTitle(e.target.value)}
                    variant="borderless"
                    size="large"
                    className="!text-lg text-center canvas-title-input"
                    maxLength={60}
                />
            </Panel>
        )
    }

    const renderTopRightPanel = () => {
        if (!canvasId) return
        return (
            <><Panel position="top-right" className="text-black text-right">
                <Tooltip
                    title={<div>
                        <b>Save & copy link</b>
                        <br />
                        <span>Revisit with link or share with others</span>
                    </div>}
                    placement="left"
                    mouseLeaveDelay={0}
                >
                    <Button
                        className="!pl-[20px] !pr-[20px] !pt-[20px] !pb-[20px] !shadow-xl"
                        loading={savingCanvas}
                        onClick={() => handleSaveCanvas({ curCanvasTitle })}
                    >
                        <div className="font-semibold">Save Canvas</div>
                    </Button>
                </Tooltip>
                </Panel>
                <Controls
                    position="top-right"
                    showInteractive={true}
                    className="shadow-xl"
                    style={{
                        "marginTop": "68px",
                    }}
                >
                    <Tooltip
                        title={copyTooltipTitle}
                        placement="left"
                        mouseLeaveDelay={0}
                    >
                        <ControlButton
                            onMouseLeave={() => setCopyTooltipTile("Copy canvas ID")}
                            onClick={() => {
                                if (!canvasId) return
                                navigator.clipboard.writeText(canvasId)
                                setCopyTooltipTile("Copied!")
                            }}
                        >
                            <CopyIcon />
                        </ControlButton>
                    </Tooltip>
            </Controls></>
        )
    }

    const renderBottomLeftPanel = () => {
        return (
            <Panel position="bottom-left" className="!z-3 text-black text-left text-md font">
                x: {(-x).toFixed(2)}
                <br />
                y: {y.toFixed(2)}
                <br />
                zoom: {zoom.toFixed(2)}
            </Panel>
        )
    }

    const renderBottomCenterPanel = () => {
        if (isMobile) return
        return (
            <Panel position="bottom-center" className="!z-3 text-black text-center !ml-0">
                Drag on background to move across canvas
                <br />
                Scroll with mouse or pinch on trackpad to zoom in & out
                <br />
                ⌘+&apos; to create new nodes -- ⌘+\ to view all nodes
            </Panel>
        )
    }

    const renderBottomRightPanel = () => {
        return (
            <Panel position="bottom-right" className="!z-3 text-black text-sm">
                © {new Date().getFullYear()} Winggo Tse
            </Panel>
        )
    }

    return (
        <>
            {renderTopLeftPanel()}
            {renderTopCenterPanel()}
            {renderTopRightPanel()}
            {renderBottomLeftPanel()}
            {renderBottomCenterPanel()}
            {renderBottomRightPanel()}
        </>
    )
}