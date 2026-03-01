import { useState, useEffect } from "react"
import { Controls, ControlButton, Panel } from "@xyflow/react"
import { useMediaQuery } from "react-responsive"
import { Button, Tooltip, Input } from "antd"
import '@ant-design/v5-patch-for-react-19'

import { useTheme } from "../../context/ThemeContext"
import CopyIcon from "../../icons/CopyIcon"


type CanvasInfo = {
    canvasId?: string,
    canvasTitle?: string,
    handleSaveCanvas: ({ curCanvasTitle }: { curCanvasTitle: string }) => void,
    savingCanvas: boolean,
    newCanvas?: boolean,
}

export default function CanvasInfo({ canvasId, canvasTitle, handleSaveCanvas, savingCanvas, newCanvas }: CanvasInfo) { 
    const { theme, toggleTheme } = useTheme()
    const isMobile = useMediaQuery({ maxWidth: 768 })
    const [curCanvasTitle, setCurCanvasTitle] = useState(newCanvas ? "[Welcome to Polylogue]" : "")
    const [copyTooltipTitle, setCopyTooltipTile] = useState("Copy canvas ID")

    useEffect(() => {
        if (canvasTitle) {
            setCurCanvasTitle(canvasTitle)
        }
    }, [canvasTitle])

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
            <><Panel position="top-right" className="text-black dark:text-gray-100 text-right">
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
                        className="!pl-[20px] !pr-[20px] !pt-[20px] !pb-[20px] !shadow-xl dark:!bg-[#1f1f1f] dark:!border-[#2a2a2a]"
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
                    <Tooltip
                        title={theme === 'light' ? 'Dark mode' : 'Light mode'}
                        placement="left"
                        mouseLeaveDelay={0}
                    >
                        <ControlButton onClick={toggleTheme}>
                            {theme === 'light' ? (
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                                </svg>
                            ) : (
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <circle cx="12" cy="12" r="5" />
                                    <line x1="12" y1="1" x2="12" y2="3" />
                                    <line x1="12" y1="21" x2="12" y2="23" />
                                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                                    <line x1="1" y1="12" x2="3" y2="12" />
                                    <line x1="21" y1="12" x2="23" y2="12" />
                                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                                </svg>
                            )}
                        </ControlButton>
                    </Tooltip>
            </Controls></>
        )
    }

    const renderBottomCenterPanel = () => {
        if (isMobile) return
        return (
            <Panel position="bottom-center" className="!z-3 text-black dark:text-gray-100 text-center !ml-0 text-sm">
                Scroll or pinch to zoom in & out
                <br />
                Double click on canvas to create new nodes
                <br />
                Drag and drop images to add them to the canvas
            </Panel>
        )
    }

    return (
        <>
            {renderTopCenterPanel()}
            {renderTopRightPanel()}
            {renderBottomCenterPanel()}
        </>
    )
}