# Feature: Image Drag-and-Drop on Canvas

## Context

Users want to drop image files (PNG/JPEG/HEIC) onto the canvas to create image nodes that serve as visual context for LLM conversations. An image node connects to LLM text nodes via edges, and the image is sent as multimodal input when generating completions with vision-capable models.

## Plan

### 1. Add constants (`frontend/src/utils/constants.ts`)
- Add `imageNodeSize = { width: 400, height: 300 }`
- Add `visionModels` set: `new Set(['openai_gpt4o', 'llama_vision'])`

### 2. Create ImageNode component (`frontend/src/components/ImageNode/ImageNode.tsx`)
- New component displaying: filename header + image thumbnail
- Left `Handle` (target, `isConnectableStart={false}`) — receives connections
- Right `Handle` (source, `isConnectableEnd={false}`) — always connectable (no response gating like LLMNode)
- `nodrag` on `<img>` to prevent browser drag interference
- Style to match existing dark theme (rounded corners, border, `bg-white dark:bg-neutral-950`)
- No prompt input, no model dropdown, no response area

### 3. Update Flow.tsx — types, node registration, drop handler
- **Types**: Add `imageDataUrl?: string` and `fileName?: string` to `ExtendedNodeData` (simpler than a union type for MVP)
- **nodeTypes**: Add `imageNode: ImageNode` to the map
- **`createNewImageNode()`**: Factory function similar to `createNewLlmTextNode()`, uses `type: 'imageNode'` and `imageNodeSize`
- **Drop handler**: Add `onDragOver` + `onDrop` props to `<ReactFlow>`:
  - `onDragOver`: `preventDefault()` + set `dropEffect = 'copy'`
  - `onDrop`: Read file via `FileReader.readAsDataURL()`, convert screen→flow coords via `screenToFlowPosition()`, call `createNewImageNode()`, add to nodes

### 4. Update LlmNode.tsx — vision model + warning
- Add vision models to the models array: `{ value: "openai_gpt4o", label: "OpenAI GPT-4o" }` and `{ value: "llama_vision", label: "Llama Vision" }`
- Add to `modelMapping`
- Detect image parents: `parentNodes.some(n => n.type === 'imageNode')`
- Show inline warning text below model dropdown when image parents exist but selected model isn't vision-capable

### 5. Backend — add vision models (`backend/src/ai_models.py`)
- Add `llama_vision` model: `ChatTogether(model="meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo", ...)`
- Add `openai_gpt4o` model: `ChatOpenAI(model="gpt-4o", ...)` (direct OpenAI, not Together — confirmed vision support)
- Add both to `get_model()` switch
- Define `VISION_MODELS = {"openai_gpt4o", "llama_vision"}`

### 6. Backend — multimodal completion (`backend/src/ai_models.py`)
- New `extract_parent_data(parent_nodes)` function that separates text responses from image data URLs by checking `node.get("type") == "imageNode"`
- Modify `generate_response_with_context()`:
  - If images present AND model in `VISION_MODELS`: build `HumanMessage(content=[...])` with `{"type": "text", ...}` and `{"type": "image_url", "image_url": {"url": data_url}}` parts, invoke `llm.invoke([message])`
  - Otherwise: use existing `PromptTemplate | llm` chain (images silently stripped for non-vision models)
- Update `get_parent_responses()` to skip image nodes (they have no `prompt_response`)

### 7. Backend — relax datastore validation (`backend/src/routes/datastore.py`)
- Change the `'data'` schema in both POST and PUT `@validate_json` decorators from the strict `{ model, prompt, prompt_response, ... }` to `dict` — allows image node data shape through save/load

## Files to modify
- `frontend/src/utils/constants.ts` — add image node size, vision models set
- `frontend/src/components/ImageNode/ImageNode.tsx` — **new file**
- `frontend/src/components/Flow/Flow.tsx` — types, nodeTypes, factory, drop handler
- `frontend/src/components/LLMNode/LlmNode.tsx` — vision models, warning UI
- `backend/src/ai_models.py` — vision models, multimodal completion logic
- `backend/src/routes/datastore.py` — relax node data validation

## Verification
1. `cd frontend && yarn dev` — start frontend
2. `cd backend && python -m src.app` — start backend
3. Drag a PNG/JPEG onto the canvas → image node appears at drop position
4. Connect image node (source handle) to an LLM text node (target handle)
5. Select a vision model (GPT-4o or Llama Vision) on the LLM node
6. Enter a prompt referencing the image → submit → verify multimodal response
7. Switch to a non-vision model → verify warning appears, completion still works (text-only, image stripped)
8. Save canvas → reload → verify image node persists and connections restore
