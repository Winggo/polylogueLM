# CLAUDE.md (AGENTS.md)

This file provides guidance to AI coding agents, including Claude Code (claude.ai/code) and other AI-assisted tools, for working with code in this repository.

## Project Overview

Polylogue is a Figma-like canvas editor for visualizing and engaging in branching conversations across multiple LLMs. Each prompt and completion is represented as a node on an infinite canvas, with support for creating conversation trees where different models can respond to the same prompts.

**Why Polylogue?** Traditional chat interfaces force linear conversations — one message follows the next, one model at a time. Polylogue breaks free of this by letting you:
- **Compare models side-by-side** — branch a conversation to see how different LLMs respond to the same prompt
- **Build conversation trees** — explore multiple lines of thinking from a single starting point, like a mind map for AI conversations
- **Mix text and images** — drop images onto the canvas or generate them with image models, and use them as context for follow-up prompts
- **Collaborate and share** — save canvases with shareable links so others can continue or branch off your conversations

**Tech Stack:**
- Frontend: Next.js 16 with React 19, TypeScript, Tailwind CSS 4, @xyflow/react for canvas, Ant Design 5
- Backend: Flask with LangChain, Flask-SocketIO for WebSockets
- Storage: Google Firestore for persistence, Google Cloud Storage for images, Redis for real-time features (optional)
- AI Providers: Together.ai (Llama 4, Gemma 3n, Qwen 3, image gen), OpenAI (GPT Image)
- Deployment: Google App Engine

## Development Commands

### Frontend (Next.js)
```bash
cd frontend
yarn dev              # Start development server (uses Turbopack)
yarn build           # Production build
yarn start           # Start production server
yarn lint            # Run ESLint
```

The frontend dev server runs on http://localhost:3000

### Backend (Flask)
```bash
cd backend
pip install -r requirements.txt   # Install dependencies

# Set up environment
# Create .env.local with required variables (see Deployment section)

# Run development server
python -m src.app    # Runs Flask with SocketIO support
```

Environment files:
- `.env.local` for local development
- `.env.production` for production
- Set `FLASK_ENV=local` or `FLASK_ENV=production`

## Architecture

### Frontend Architecture

**Component Structure:**
- `src/app/canvas/` - New canvas route (creates unique canvasId via nanoid)
- `src/app/canvas/[canvas_id]/` - Load existing canvas route
- `src/components/Flow/Flow.tsx` - Core canvas component using ReactFlow
- `src/components/Flow/CanvasInfo.tsx` - Canvas UI controls (title, save, theme toggle, help text)
- `src/components/Flow/AnimatedConnectionLine.tsx` - Custom bezier connection line during drag
- `src/components/LLMNode/LlmNode.tsx` - Conversation node for text and image generation
- `src/components/LLMNode/LLMNodeCard.tsx` - Onboarding hint card shown in empty nodes
- `src/components/ImageNode/ImageNode.tsx` - Dropped/uploaded image display node
- `src/context/ThemeContext.tsx` - Dark/light theme context with localStorage persistence
- `src/app/AntdThemeProvider.tsx` - Bridges custom theme with Ant Design theming
- `src/utils/constants.ts` - Node sizes, backend URL, model lists, progress messages
- `src/utils/helpers.ts` - `usePrevious()` hook
- `src/icons/` - Custom SVG icon components (CopyIcon, RightArrowCircle, DottedSquare, DownArrowCircle)

**State Management:**
- ReactFlow manages node and edge state via `useNodesState` and `useEdgesState`
- ThemeContext provides dark/light mode with `useTheme()` hook (default: dark, persisted in localStorage)
- Node data includes: model, prompt, prompt_response, parent_ids, canvasId, imageDataUrl
- Each node is assigned a unique ID via nanoid(10)

**Node Types:**
- `llmText` - Text/image generation node with prompt input, model selector, and response display
- `imageNode` - Image display node for drag-and-dropped images

**Node Lifecycle:**
1. Nodes are created via `createNewLlmTextNode()` or `createNewImageNode()` with position and data
2. On creation, text nodes fetch a prompt suggestion from `/api/v1/prompt` (image models get image-specific suggestions)
3. User enters prompt and selects model from dropdown (5 models: 3 text, 2 image)
4. Submission sends to `/api/v1/completion` with model, prompt, nodeId, parentNodes
5. Text responses render as Markdown; image responses display inline
6. New child node is auto-created to the right; edges connect automatically
7. Animated edges pulse when connected to nodes that are still loading

**Canvas Features:**
- Dark/light theme toggle (persisted in localStorage)
- Editable canvas title (top-center panel)
- Save canvas button with shareable link modal
- Copy canvas ID button
- Instructions panel (bottom-center, desktop only)
- ReactFlow zoom controls
- Fade-in animation on load (react-awesome-reveal)
- Mobile-responsive (panels hidden on small screens)

**Image Features:**
- Drag-and-drop PNG/JPEG images onto canvas creates an ImageNode + connected LLMNode
- Image models (Google Flash Image 2.5, OpenAI GPT Image 1.5) generate images from prompts
- Progress bar with rotating creative messages during image generation (~25s)
- Generated images display inline in LLMNode response area
- Images saved to Google Cloud Storage on canvas save

**Canvas Persistence:**
- Save operation posts to `/ds/v1/canvases` with canvasId, title, and nodes array
- Base64 images are uploaded to GCS and replaced with public URLs before Firestore storage
- Load operation fetches from `/ds/v1/canvases/<canvas_id>`
- Nodes are transformed between array format (frontend) and map format (Firestore)
- Deleted image nodes have their GCS blobs cleaned up on update

**Keyboard Shortcuts:**
- `Cmd/Ctrl + '` - Create new node at cursor position
- `Cmd/Ctrl + \` - Fit view to show all nodes
- `Enter` - Submit prompt in selected node
- `Tab` - Accept suggested prompt placeholder
- Double-click canvas - Create new node at click position
- Drag from right handle - Create connected node at drop position

### Backend Architecture

**Flask App Structure (`src/app.py`):**
- Environment-based config loading (.env.local, .env.production)
- CORS configuration for frontend origin
- SocketIO with WebSocket transport
- Google Cloud Storage client initialization (stored in app config)
- Optional Redis client and pub/sub (controlled by env vars)
- Three blueprint routes: `/api`, `/ds`, `/sockets` (sockets conditionally loaded)

**Route Blueprints:**

1. **API Routes (`src/routes/api.py`):**
   - `POST /api/v1/prompt` - Generate prompt suggestion (text or image-specific, using Gemma 3n)
   - `POST /api/v1/completion` - Generate LLM completion or image, routes to text or image handler based on model

2. **Datastore Routes (`src/routes/datastore.py`):**
   - `POST /ds/v1/canvases` - Save canvas with nodes (uploads images to GCS)
   - `GET /ds/v1/canvases/<canvas_id>` - Fetch canvas by ID
   - `PUT /ds/v1/canvases/<canvas_id>` - Update canvas (uploads new images, deletes removed image blobs)
   - Request validation via `@validate_json` decorator
   - Transforms nodes between array (API) and map (Firestore) formats

3. **Socket Routes (`src/routes/sockets.py`):**
   - Only loaded when `ENABLE_REDIS_PUBSUB=true`
   - `connect` / `disconnect` - Handle client connections
   - `subscribe` / `unsubscribe` - Redis channel pub/sub
   - Tracks client subscriptions in memory

**Request Validation (`src/routes/validation/validate.py`):**
- `@validate_json` decorator enforces schema on POST/PUT requests
- Supports types, tuples, nested objects, arrays, `OptionalField`
- Returns validation errors as JSON with path to invalid field

**AI Model Integration (`src/ai_models.py`):**

Available models via `get_model(model_name)`:
- `llamba4_17b` - Meta Llama 4 Maverick 17B via Together.ai (default)
- `gemma3n_4b` - Google Gemma 3n 4B via Together.ai (also used for prompt suggestions and image descriptions)
- `qwen3_8b` - Qwen 3 VL 8B via Together.ai (multimodal, accepts image input)

Image generation models (via `IMAGE_MODELS`):
- `google/flash-image-2.5` - Google Flash Image 2.5 via Together.ai
- `openai/gpt-image-1.5` - OpenAI GPT Image 1.5

**Context Handling:**
- `extract_parent_data()` - Separates parent nodes into `(text_responses, image_data_urls)` based on node type
- `generate_response_with_context()` - Builds multimodal HumanMessage with text context and image URLs, invokes LangChain model
- `generate_image_with_context()` - Enriches prompt with parent text + `describe_images()` output, generates via Together Images API
- `generate_prompt_question()` - Context-aware prompt suggestions with different preambles for text vs image models
- `describe_images()` - Uses Gemma 3n to describe images in 2-3 sentences (for image generation context)
- Responses limited to <150 words via prompt preamble

**Google Cloud Storage Integration (`src/db/storage.py`):**
- `start_storage_client()` - Initialize GCS client
- `upload_base64_image()` - Upload base64 data URL to GCS, return public HTTPS URL
- `is_base64_data_url()` - Detect base64 vs already-uploaded URLs
- `delete_blobs()` - Batch delete blobs from GCS

**Image Upload Pipeline (`src/routes/datastore.py`):**
- `upload_node_images()` - Process all nodes on save: upload base64 images to GCS, replace with public URLs (mutates in place)
  - `imageNode` type: base64 in `data.imageDataUrl`
  - `llmText` type: generated images in `data.prompt_response`
  - Stored at: `canvases/{canvas_id}/{node_id}.{ext}`
- `delete_removed_node_images()` - On update, compare incoming vs existing nodes and delete GCS blobs for removed image nodes

**Firestore Integration (`src/db/firestore.py`):**
- `start_firestore_project_client()` - Initialize Firestore client
- `get_document_by_collection_and_id()` - Fetch document
- `save_document_in_collection()` - Create/update document
- `update_document_in_collection()` - Update specific fields

**Redis Integration (`src/redis_listener.py`):**
- Optional feature enabled via `ENABLE_REDIS=true`
- Pub/sub for real-time collaboration (planned feature)
- Client subscriptions tracked per WebSocket session

### Data Flow

**Creating a text completion:**
1. Frontend: User types prompt in LLMNode, selects text model
2. Frontend: On Enter, calls `POST /api/v1/completion` with model, prompt, nodeId, parentNodes (15s timeout)
3. Backend: `extract_parent_data()` separates text responses and image URLs from parents
4. Backend: Builds multimodal `HumanMessage` with context preamble, text context, image URLs, and prompt
5. Backend: Invokes LangChain model (ChatTogether)
6. Backend: Returns `{ response: "markdown text" }`
7. Frontend: Renders response as Markdown, auto-creates next node to the right

**Creating an image:**
1. Frontend: User types prompt in LLMNode, selects image model (Google Flash Image or OpenAI GPT Image)
2. Frontend: Shows progress bar with rotating creative messages (90s timeout)
3. Backend: `generate_image_with_context()` enriches prompt with parent text + `describe_images()` output
4. Backend: Calls `Together().images.generate()` with enriched prompt
5. Backend: Returns `{ response: "data:image/png;base64,..." }`
6. Frontend: Displays image inline in node

**Dropping an image:**
1. Frontend: User drags PNG/JPEG file onto canvas
2. Frontend: Creates ImageNode at drop position + connected LLMNode to the right
3. Frontend: ImageNode stores base64 data URL in `data.imageDataUrl`
4. Subsequent LLMNodes connected to the image receive it as context

**Saving a canvas:**
1. Frontend: Calls `POST /ds/v1/canvases` (new) or `PUT /ds/v1/canvases/<id>` (existing)
2. Backend: `upload_node_images()` uploads all base64 images to GCS, replaces with public URLs
3. Backend: `delete_removed_node_images()` cleans up GCS blobs for deleted nodes (on update)
4. Backend: Transforms nodes array to map, saves to Firestore with timestamps
5. Frontend: Shows save modal with shareable link (`https://polylogue.dev/canvas/{canvasId}`)
6. Frontend: Updates URL to `/canvas/{canvasId}` if new canvas

**Loading a canvas:**
1. Frontend: Routes to `/canvas/<canvas_id>`
2. Frontend: Calls `GET /ds/v1/canvases/<canvas_id>`
3. Backend: Fetches from Firestore, transforms nodes map to array
4. Frontend: Creates edges from parent_ids, initializes ReactFlow, fits view

## Deployment

This app deploys to Google App Engine with separate frontend and backend services.

**Environment Variables Required:**

Backend (`backend/app.yaml`):
- `GCP_PROJECT` - Google Cloud project ID
- `CORS_ORIGIN` - Frontend URL for CORS
- `TOGETHER_API_KEY` - Together.ai API key (required)
- `OPENAI_API_KEY` - OpenAI API key (optional, for GPT Image)
- `GCS_BUCKET` - Google Cloud Storage bucket name (default: `polylogue-canvas-images`)
- `ENABLE_REDIS` - Set to "true" to enable Redis
- `ENABLE_REDIS_PUBSUB` - Set to "true" to enable pub/sub

Frontend (`frontend/app.yaml`):
- `NEXT_PUBLIC_BACKEND_ROOT_URL` - Backend URL (also set during build)

**Deployment Order:**
1. Deploy backend first: `cd backend && gcloud app deploy`
2. Build frontend with backend URL: `NEXT_PUBLIC_BACKEND_ROOT_URL=<backend_url> yarn build`
3. Deploy frontend: `cd frontend && gcloud app deploy`

**Debugging:**
- Backend logs: `gcloud app logs tail -s backend`
- Frontend logs: `gcloud app logs tail -s frontend`

## Code Patterns

**Adding a new LLM model:**
1. Add model instance in `backend/src/ai_models.py` (e.g., using ChatTogether)
2. Add case to `get_model()` function
3. Add to `IMAGE_MODELS` list if it's an image model
4. Add to models array and `modelMapping` in `frontend/src/components/LLMNode/LlmNode.tsx`
5. Add to `IMAGE_MODELS` or `NON_IMAGE_MODELS` in `frontend/src/utils/constants.ts`

**Modifying prompt templates:**
- Edit preamble strings in `backend/src/ai_models.py` (e.g., `context_prompt_preamble`, `*_prompt_question_preamble`)
- Separate preambles exist for: text prompts with/without context, image prompts with/without context

**Node data structure:**
```typescript
// LLM Text Node
{
  id: string (nanoid),
  type: 'llmText',
  position: { x: number, y: number },
  data: {
    model: string,
    prompt: string,
    prompt_response: string,  // markdown text or image URL/base64
    parent_ids: string[],
    canvasId: string,
    setNode: function,
    createNextNode: function,
  },
  selected: boolean,
  measured: { width: 650, height: 700 },
  origin: [number, number]
}

// Image Node (drag-and-dropped images)
{
  id: string (nanoid),
  type: 'imageNode',
  position: { x: number, y: number },
  data: {
    imageDataUrl: string,  // base64 data URL or GCS public URL
    fileName: string,
    canvasId: string,
    setNode: function,
    createNextNode: function,
  },
  selected: boolean,
  measured: { width: 600, height: 450 },
  origin: [number, number]
}
```

**API request/response formats:**

Generate prompt:
```json
POST /api/v1/prompt
{ "parentNodes": [{ "type": "llmText", "data": { "prompt_response": "..." } }], "model": "llamba4_17b" }
-> { "prompt": "suggested question?" }
```

Generate text completion:
```json
POST /api/v1/completion
{
  "model": "llamba4_17b",
  "prompt": "user prompt",
  "nodeId": "abc123",
  "parentNodes": [{ "id": "xyz", "type": "llmText", "data": { "prompt_response": "..." } }]
}
-> { "response": "AI generated markdown response" }
```

Generate image:
```json
POST /api/v1/completion
{
  "model": "google/flash-image-2.5",
  "prompt": "a painting of a sunset",
  "nodeId": "abc123",
  "parentNodes": []
}
-> { "response": "data:image/png;base64,iVBOR..." }
```
