const hints = [
    'Click on ⋮⋮⋮ and drag to move node',
    <><i>Backspace</i> to delete selected node</>,
]

const examples = [
    'create a packing list 🏕️',
    'generate a 📚 report',
    'come up with 🎁 ideas',
    'write a love letter 🌹',
]

export default function LLMNodeCard() {
    return (
        <div className="w-full h-full flex flex-col items-center justify-around llm-node-card">
            <div className="cursor-text select-text text-center flex flex-col gap-16">
                <p><i>Visualize and explore branching LLM conversations</i></p>
                <div className="flex flex-col gap-1">
                    {hints.map((hint, i) => <span key={i}>{hint}</span>)}
                </div>
                <div className="flex flex-col gap-1">
                    <span>You can...</span>
                    {examples.map((ex, i) => <span key={i}>- {ex}</span>)}
                </div>
            </div>
        </div>
    )
}
