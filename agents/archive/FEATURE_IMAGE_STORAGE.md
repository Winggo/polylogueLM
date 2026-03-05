# Store Canvas Images in Google Cloud Storage

## Context
Dropping multiple images onto a canvas stores them as base64 strings in Firestore, which exceeds the 1MB document size limit. Solution: upload images to GCS on canvas save, store GCS URLs in Firestore instead of base64.

## Approach
- **On save**: detect base64 `imageDataUrl` on image nodes → upload to GCS → replace with public URL before Firestore write
- **On load**: `imageDataUrl` is already a GCS URL → `<img src>` renders it directly
- **On drop** (no change): images stay as base64 in frontend memory until save
- **Public bucket**: images accessible via URL without auth (MVP)
- **No frontend changes needed**: `<img src>` works with both base64 and HTTP URLs
- **No ai_models.py changes needed**: LangChain `image_url` accepts both formats

## Implementation Steps

### 1. Add dependency
**File:** `backend/requirements.txt`
- Add `google-cloud-storage` (shares auth/core deps with existing `google-cloud-firestore`)

### 2. Create GCS helper module
**New file:** `backend/src/db/storage.py` (follows `backend/src/db/firestore.py` pattern)
- `start_storage_client(project)` — init GCS client
- `upload_base64_image(client, bucket, blob_path, data_url)` — parse data URL, upload binary, return public URL
- `is_base64_data_url(value)` — check if string starts with `data:`

### 3. Initialize GCS client in app
**File:** `backend/src/app.py`
- Import and init `start_storage_client` with `GCP_PROJECT`
- Store in `app.config['GCS']` and `app.config['GCS_BUCKET']`
- Bucket name from env var `GCS_BUCKET`, default `polylogue-canvas-images`

### 4. Modify save route to upload images
**File:** `backend/src/routes/datastore.py`
- Add `upload_node_images(nodes, canvas_id, gcs_client, bucket_name)` helper
  - Iterate nodes, find `type == "imageNode"` with base64 `imageDataUrl`
  - Upload to `canvases/{canvas_id}/{node_id}.{ext}`
  - Replace `imageDataUrl` with public GCS URL
  - On upload failure: log error, keep base64 as fallback
- Call before `transform_nodes_arr_to_map` in both `save_canvas()` and `update_canvas()`
- Idempotent: re-saving a canvas with GCS URLs is a no-op (not base64, skipped)

### 5. Add env var to app.yaml
**File:** `backend/app.yaml`
- Add `GCS_BUCKET: "polylogue-canvas-images"` under `env_variables`

### 6. Create GCS bucket (one-time CLI)
```bash
gcloud storage buckets create gs://polylogue-canvas-images \
  --project=polylogue-456810 --location=us-central1 --uniform-bucket-level-access

gcloud storage buckets add-iam-policy-binding gs://polylogue-canvas-images \
  --member=allUsers --role=roles/storage.objectViewer
```

## Files Changed
| File | Change |
|------|--------|
| `backend/requirements.txt` | Add `google-cloud-storage` |
| `backend/src/db/storage.py` | **New** — GCS upload helpers |
| `backend/src/app.py` | Init GCS client |
| `backend/src/routes/datastore.py` | Upload images on save |
| `backend/app.yaml` | Add `GCS_BUCKET` env var |

## Verification
1. Start backend locally (`python -m src.app`)
2. Drop 2-3 images onto canvas in frontend
3. Click save → verify backend logs show GCS uploads
4. Check GCS bucket for uploaded images at `canvases/{canvasId}/{nodeId}.png`
5. Reload the canvas → images should load from GCS URLs
6. Re-save the same canvas → no re-uploads (idempotent)
7. Test LLM completion with image parent node → verify vision model receives GCS URL correctly
