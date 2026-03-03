export const llmNodeSize = {
    width: 650,
    height: 700,
}
export const llmNewNodeDeltaX = 150

export const imageNodeSize = {
    width: 600,
    height: 450,
}

export const backendServerURL = process.env.NEXT_PUBLIC_BACKEND_ROOT_URL || 'http://127.0.0.1:5000'

export const initialModel = "llamba4_17b"
export const NON_IMAGE_MODELS = ["llamba4_17b", "gemma3n_4b", "qwen3_8b"]
export const IMAGE_MODELS = ["gemini_flash_image", "openai_gpt_image"]
