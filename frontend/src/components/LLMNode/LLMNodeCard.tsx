export default function LLMNodeCard() {
    return (
        <div className="w-full h-full flex flex-col items-center justify-around llm-node-card">
            <div className="cursor-text select-text text-center mb-[50px]">
                <span><i>Visualize and explore branching LLM conversations</i></span>
                <br /><br />
                <span>Click on ⋮⋮⋮ and drag to move node</span>
                <br />
                <span><i>Backspace</i> to delete selected node</span>
                <br /><br /><br /><br /><br /><br /><br /><br />
                <span>You can...</span>
                <br />
                <span>- create a packing list 🏕️</span>
                <br />
                <span>- generate a 📚 report</span>
                <br />
                <span>- come up with 🎁 ideas</span>
                <br />
                <span>- write a love letter 🌹</span>
            </div>
        </div>
    )
}
