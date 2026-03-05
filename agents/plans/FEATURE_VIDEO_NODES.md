# Video Node Support — Implementation Plan

## Context

Polylogue currently supports dropping image files onto the canvas, creating ImageNodes that pass image context to child LLMTextNodes. We're extending this to video files: users drop videos (mp4, webm, mov, avi) to create VideoNodes that display the video and pass video context to child nodes.

**Key constraint**: Direct child LLMTextNodes of VideoNodes can only select between the two video-capable models (`gemma3n_4b` and `qwen3_8b`), so we can test both. Other models are excluded from the dropdown for these nodes.

**API finding**: Together.ai's `video_url` content type requires HTTP URLs (base64 data URLs for video are not documented). This means videos must be uploaded to GCS before being sent to the model. LangChain ChatTogether may not pass `video_url` content parts correctly, so we'll use the Together SDK directly for video completions.

**Model**: We'll try `gemma3n_4b` (`google/gemma-3n-E4B-it`) first as specified. If it doesn't support video on Together.ai, we'll switch to `qwen3_8b` (`Qwen/Qwen3-VL-8B-Instruct`). The constant `initialVideoModel` makes switching trivial.

**Upload timing**: Upload video to GCS on completion (when user submits prompt), not on drop. Simplest approach — adds a few seconds latency on first completion but keeps the drop flow simple.

---

## Changes by File

### 1. `frontend/src/utils/constants.ts`
- Add `videoNodeSize = { width: 600, height: 450 }`
- Add `VIDEO_MIME_TYPES` array: `['video/mp4', 'video/webm', 'video/quicktime', 'video/x-msvideo']`
- Add `VIDEO_MODELS = ["gemma3n_4b", "qwen3_8b"]` — models that accept video input
- Add `initialVideoModel = "gemma3n_4b"` — default model for video node children

### 2. `frontend/src/components/VideoNode/VideoNode.tsx` (NEW)
- Clone ImageNode structure, replace `<img>` with `<video controls>`
- Data type: `{ videoDataUrl: string, fileName: string, canvasId: string }`
- Same handle structure (target left, source right)
- Uses `videoNodeSize` from constants

### 3. `frontend/src/components/Flow/Flow.tsx`
- Import `VideoNode`, register in `nodeTypes`: `videoNode: VideoNode`
- Import `videoNodeSize`, `VIDEO_MIME_TYPES`, `initialVideoModel`
- Add `createNewVideoNode()` function (parallel to `createNewImageNode`)
- Add `videoDataUrl?: string` to `ExtendedNodeData` type
- Update `handleDrop`: detect video files first (via `VIDEO_MIME_TYPES`), create VideoNode + connected LLMTextNode with forced model
- Update `onConnectEnd`: add `videoNode` to source node size calculation, force `initialVideoModel` when source is videoNode

### 4. `frontend/src/components/LLMNode/LlmNode.tsx`
- Import `VIDEO_MODELS`, `initialVideoModel` from constants
- Detect if any parent is `videoNode`: `const hasVideoParent = parentNodes.some(nd => nd.type === 'videoNode')`
- When `hasVideoParent` is true: set initial model to `initialVideoModel`, restrict dropdown to only show `VIDEO_MODELS` entries (gemma3n_4b and qwen3_8b)
- When `hasVideoParent` is false: show full model list as before

### 5. `backend/src/db/storage.py`
- Add `upload_base64_video()` function — same as `upload_base64_image()` but regex matches `data:(video/[\w+-]+);base64,(.+)`

### 6. `backend/src/routes/datastore.py`
- Import `upload_base64_video` from storage
- `upload_node_images()`: add `elif node.get("type") == "videoNode"` branch — upload `data.videoDataUrl` base64 to GCS, replace with public URL. Map MIME types to extensions (mp4, webm, mov, avi).
- `delete_removed_node_images()`: add `elif node.get("type") == "videoNode"` branch — extract `videoDataUrl` for blob cleanup

### 7. `backend/src/ai_models.py`
- Update `extract_parent_data()` to return 3-tuple: `(text_responses, image_data_urls, video_data_urls)`. Add `videoNode` handling to extract `videoDataUrl`.
- Update all callers to unpack 3 values: `generate_prompt_question`, `generate_response_with_context`, `generate_image_with_context`
- Add `generate_response_with_video_context()` — uses Together SDK directly (not LangChain) to pass `video_url` content parts. Includes text context + image context + video context.
- Modify `generate_response_with_context()` to delegate to `generate_response_with_video_context()` when `video_data_urls` is non-empty.

### 8. `backend/src/routes/api.py`
- In `/api/v1/completion` handler: before calling model, find any `videoNode` parents with base64 `videoDataUrl`, upload to GCS, replace with public URL (so the model receives an HTTP URL, not base64)
- Import `upload_base64_video`, `is_base64_data_url` from storage

---

## Implementation Order

1. `constants.ts` — no dependencies
2. `VideoNode.tsx` — depends on constants
3. `storage.py` — no dependencies
4. `ai_models.py` — depends on storage concept
5. `datastore.py` — depends on storage.py
6. `api.py` — depends on ai_models.py + storage.py
7. `Flow.tsx` — depends on VideoNode + constants
8. `LlmNode.tsx` — depends on constants

## Verification

1. **Frontend**: Drop an mp4 file onto canvas → VideoNode created with `<video>` element, connected LLMTextNode auto-created with forced model
2. **Model lock**: Child node of VideoNode shows model dropdown restricted to gemma3n_4b and qwen3_8b only
3. **Completion**: Enter prompt in child node → backend receives video context, calls Together API with `video_url`, returns text response
4. **Save/Load**: Save canvas → video uploaded to GCS → reload canvas → video plays from GCS URL
5. **Delete**: Remove video node, save → GCS blob cleaned up
