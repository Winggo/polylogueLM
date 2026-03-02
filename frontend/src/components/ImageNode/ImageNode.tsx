'use client'

import { useState } from 'react'
import { Handle, Position } from '@xyflow/react'
import { Tooltip } from 'antd'
import { imageNodeSize } from '../../utils/constants'
import RightArrowCircle from '../../icons/RightArrowCircle'


type ImageNodeProps = {
    id: string
    selected: boolean
    data: {
        imageDataUrl: string
        fileName: string
        canvasId: string
    }
}

export default function ImageNode({ selected, data }: ImageNodeProps) {
    const { imageDataUrl, fileName } = data
    const [isHovered, setIsHovered] = useState(false)

    return (
        <div
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
        >
            <div
                className={`
                    bg-white dark:bg-neutral-950
                    border border-gray-800 dark:border-neutral-700
                    rounded-[20px] shadow-xl overflow-hidden
                    ${isHovered && !selected && "outline-[1px] outline-orange-500"}
                    ${selected && "outline-[1px] shadow-2xl"}
                `}
                style={{ width: imageNodeSize.width, height: imageNodeSize.height }}
            >
                <Handle
                    type="target"
                    position={Position.Left}
                    className="w-4 h-4 rounded-lg !bg-white dark:!bg-neutral-950 border-gray-800 dark:border-gray-400 border-2"
                    isConnectableStart={false}
                />
                <Tooltip
                    title={<span className="text-sm">Click or drag to start a branching conversation</span>}
                    placement="top"
                    mouseLeaveDelay={0}
                >
                    <Handle
                        type="source"
                        position={Position.Right}
                        className="w-8 h-8 rounded-lg !bg-transparent !cursor-pointer"
                        isConnectableEnd={false}
                    >
                        <RightArrowCircle />
                    </Handle>
                </Tooltip>

                <div className="cursor-move px-3 py-2 text-xs font-medium truncate border-b border-gray-200 dark:border-neutral-700 text-gray-600 dark:text-gray-400">
                    {fileName}
                </div>

                <img
                    src={imageDataUrl}
                    alt={fileName}
                    className="w-full object-contain nodrag cursor-default"
                    style={{ height: imageNodeSize.height - 36 }}
                    draggable={false}
                />
            </div>
        </div>
    )
}
