export const llmNodeSize = {
    width: 650,
    height: 700,
}
export const llmNewNodeDeltaX = 150

export const imageNodeSize = {
    width: 600,
    height: 450,
}
export const videoNodeSize = {
    width: 600,
    height: 450,
}
export const flowViewMinZoom = 0.3
export const flowViewMaxZoom = 0.9

export const backendServerURL = process.env.NEXT_PUBLIC_BACKEND_ROOT_URL || 'http://127.0.0.1:5000'

export const initialModel = "qwen3_8b"
export const NON_IMAGE_MODELS = ["qwen3_8b", "gemma3n_4b"]
export const IMAGE_MODELS = ["google/flash-image-2.5", "openai/gpt-image-1.5"]
export const VIDEO_MODEL = "gemini-2.0-flash"
export const VIDEO_MIME_TYPES = [
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-msvideo",
]

export const imageProgressMessages = [
    "Warming up the pixels...",
    "Mixing colors...",
    "Sketching outlines...",
    "Consulting the muse...",
    "Splattering paint...",
    "Arranging photons...",
    "Calibrating brushstrokes...",
    "Defragmenting imagination...",
    "Rendering vibes...",
    "Tickling the canvas...",
    "Conjuring shapes...",
    "Aligning chakras...",
    "Wrangling gradients...",
    "Percolating aesthetics...",
    "Seasoning with style...",
    "Untangling dimensions...",
    "Polishing reflections...",
    "Composting ideas...",
    "Fermenting visuals...",
    "Massaging textures...",
    "Befriending shadows...",
    "Negotiating with light...",
    "Herding stray pixels...",
    "Marinating in color theory...",
    "Almost there...",
]
