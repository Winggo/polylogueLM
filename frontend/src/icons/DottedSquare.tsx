export default function DottedSquare () {
    return (
        <svg className="cursor-move absolute top-[-48px] left-[30px] w-[30px] h-[40px]" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 30 20" fill="none">
            <circle cx="5" cy="5" r="3.5" fill="currentColor" />
            <circle cx="15" cy="5" r="3.5" fill="currentColor" />
            <circle cx="25" cy="5" r="3.5" fill="currentColor" />
            
            <circle cx="5" cy="15" r="3.5" fill="currentColor" />
            <circle cx="15" cy="15" r="3.5" fill="currentColor" />
            <circle cx="25" cy="15" r="3.5" fill="currentColor" />
            
            <circle cx="5" cy="25" r="3.5" fill="currentColor" />
            <circle cx="15" cy="25" r="3.5" fill="currentColor" />
            <circle cx="25" cy="25" r="3.5" fill="currentColor" />
        </svg>
    )
}