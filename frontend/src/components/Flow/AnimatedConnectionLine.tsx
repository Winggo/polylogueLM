import { getBezierPath, Position, type ConnectionLineComponentProps } from '@xyflow/react'

export default function AnimatedConnectionLine({
    fromX,
    fromY,
    fromPosition = Position.Right,
    toX,
    toY,
    toPosition = Position.Left,
}: ConnectionLineComponentProps) {
    const [edgePath] = getBezierPath({ sourceX: fromX, sourceY: fromY, sourcePosition: fromPosition, targetX: toX, targetY: toY, targetPosition: toPosition })

    return (
        <g>
            <path
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
                className="react-flow__connection-path"
                d={edgePath}
            />
        </g>
    )
}
