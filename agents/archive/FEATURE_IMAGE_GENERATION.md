# Implement `generate_image_with_context()`

## Context
The image generation function in the backend is a stub. Users can already select image models (gemini_flash_image, openai_gpt_image) in the frontend, but submitting a prompt returns `None`. We need to implement the backend function to call Together.ai's image generation API and return a base64 data URL, then update the frontend to render images.

## Changes

### 1. Backend: Implement `generate_image_with_context()` in [ai_models.py](backend/src/ai_models.py)

- Use the `together` Python SDK (`Together().images.generate()`) with `response_format="base64"`
- Map model names to Together.ai model IDs using a dict (reuse existing model ID strings from the `ChatTogether` instances: `"google/flash-image-2.5"`, `"openai/gpt-image-1.5"`)
- Build an enriched prompt using `extract_parent_data()`
- Context handling differs by model capability:
  - **Nano Banana (text input only)**: Prepend parent text as context. For parent images, use `gemma3n_4b` to describe them as text first.
  - **GPT Image 1.5 (text + image input)**: Prepend parent text as context. Pass the **first** parent image directly via `image_url` param (API supports one input image).
- Return a data URL string: `data:image/png;base64,{b64_json}`
- Add `from together import Together`
- Add `together` to requirements.txt if not already a transitive dep of `langchain-together`

### 2. Frontend: Update `renderOutput()` in [LlmNode.tsx](frontend/src/components/LLMNode/LlmNode.tsx)

- Detect if `promptResponse` starts with `data:image/` -> render as `<img>` tag
- Otherwise render with ReactMarkdown as before

### 3. Backend: Timeout

Leave frontend 15s timeout as-is for MVP. Together.ai image gen is typically fast enough.

## Files to modify
- `backend/src/ai_models.py` - implement function, add model ID mapping
- `frontend/src/components/LLMNode/LlmNode.tsx` - render image in output
- `backend/requirements.txt` - add `together` if not already installed transitively

## Verification
1. Start backend: `cd backend && python -m src.app`
2. Start frontend: `cd frontend && yarn dev`
3. Create a node, select "Google Nano Banana" or "OpenAI GPT Image 1.5"
4. Enter an image prompt like "Generate an image of a bioluminescent jellyfish city"
5. Verify image is displayed in the node
6. Test with a parent text node to verify context enrichment works
