from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from src.db.firestore import (
    get_document_by_collection_and_id,
    save_document_in_collection,
    update_document_in_collection,
)
from src.routes.validation.validate import validate_json, OptionalField
from src.db.storage import upload_base64_image, is_base64_data_url, delete_blobs


ds_routes = Blueprint("ds_routes", __name__)


@ds_routes.route("/v1/canvases", methods=["POST"])
def canvases_operations():
    """
    Routes to read/write to canvases collection
    """
    db = current_app.config['FIRESTORE']

    @validate_json({
        'canvasId': str,
        'title': OptionalField(str),
        'description': OptionalField(str),
        'nodes': [{
            'id': str,
            'type': str,
            'position': {
                'x': (int, float),
                'y': (int, float),
            },
            'data': dict,
            'selected': bool,
            'measured': {
                'width': (int, float),
                'height': (int, float),
            },
            'origin': [(int, float)],
        }],
        'createdBy': OptionalField(str),
    })
    def save_canvas():
        """
        Save a canvas document to datastore
        Expect request.json to be in format:
        {
            canvasId: str,
            title: str,
            description?: str,
            nodes: Node[],
            createdBy?: str,
        }
        """
        data = request.json
        try:
            gcs_client = current_app.config['GCS']
            bucket_name = current_app.config['GCS_BUCKET']
            upload_node_images(data["nodes"], data["canvasId"], gcs_client, bucket_name)

            doc_id = save_document_in_collection(
                db,
                "canvases",
                {
                    "canvas_id": data["canvasId"],
                    "title": data.get("title"),
                    "description": data.get("description"),
                    "nodes": transform_nodes_arr_to_map(data["nodes"]),
                    "created_by": data.get("createdBy"),
                    "created_at": datetime.now(),
                    "updated_at": datetime.now(),
                },
                doc_id=data["canvasId"]
            )
        except Exception as e:
            print("Error saving canvas: ", e)
            return jsonify({"error": "Internal Server Error"}), 500
        
        return jsonify({"document_id": doc_id}), 200


    if request.method == "POST":
        return save_canvas()
    else:
        return jsonify({"error": "Internal Server Error"}), 500


@ds_routes.route("/v1/canvases/<canvas_id>", methods=["GET", "PUT"])
def canvas_operations(canvas_id):
    """
    Routes to read/write to single canvas in collection
    """
    db = current_app.config['FIRESTORE']

    def get_canvas(id):
        """Get a canvas document from datastore"""
        try:
            canvas_doc = get_document_by_collection_and_id(db, "canvases", id)
            canvas_doc["nodes"] = transform_nodes_map_to_arr(canvas_doc["nodes"])
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": "Internal Server Error"}), 500
        
        return jsonify({"document": canvas_doc}), 200
    
    
    @validate_json({
        'title': OptionalField(str),
        'description': OptionalField(str),
        'nodes': OptionalField([{
            'id': str,
            'type': str,
            'position': {
                'x': (int, float),
                'y': (int, float),
            },
            'data': dict,
            'selected': bool,
            'measured': {
                'width': (int, float),
                'height': (int, float),
            },
            'origin': [(int, float)],
        }]),
    })
    def update_canvas(id):
        """
        Update a canvas document in datastore
        Expect request.json to be in format:
        {
            title: str,
            description?: str,
            nodes: Node[],
        }
        """
        data = request.json
        try:
            data["updated_at"] = datetime.now()
            if "nodes" in data:
                gcs_client = current_app.config['GCS']
                bucket_name = current_app.config['GCS_BUCKET']
                upload_node_images(data["nodes"], id, gcs_client, bucket_name)
                delete_removed_node_images(data["nodes"], id, db, gcs_client, bucket_name)
                data["nodes"] = transform_nodes_arr_to_map(data["nodes"])
            doc_id = update_document_in_collection(db, "canvases", data, doc_id=id)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": "Internal Server Error"}), 500
        
        return jsonify({"document_id": doc_id}), 200
    

    if request.method == "GET":
        return get_canvas(canvas_id)
    elif request.method == "PUT":
        return update_canvas(canvas_id)
    else:
        return jsonify({"error": "Internal Server Error"}), 500



def upload_node_images(nodes, canvas_id, gcs_client, bucket_name):
    """
    For each image node with a base64 imageDataUrl, upload to GCS
    and replace with the public URL. Mutates nodes in place.
    """
    for node in nodes:
        if node.get("type") == "imageNode":
            data_url = node.get("data", {}).get("imageDataUrl", "")
            if is_base64_data_url(data_url):
                ext = "png" if "png" in data_url[:30] else "jpg"
                blob_path = f"canvases/{canvas_id}/{node['id']}.{ext}"
                try:
                    public_url = upload_base64_image(
                        gcs_client, bucket_name, blob_path, data_url
                    )
                    node["data"]["imageDataUrl"] = public_url
                except Exception as e:
                    print(f"Error uploading image for node {node['id']}: {e}")


def delete_removed_node_images(incoming_nodes, canvas_id, db, gcs_client, bucket_name):
    """
    Compare incoming nodes with existing nodes in Firestore.
    Delete GCS blobs for image nodes that were removed.
    """
    try:
        existing_doc = get_document_by_collection_and_id(db, "canvases", canvas_id)
        existing_nodes = existing_doc.get("nodes", {})
    except Exception:
        return

    incoming_ids = {node["id"] for node in incoming_nodes}
    blob_paths = []
    for node_id, node in existing_nodes.items():
        if node.get("type") == "imageNode" and node_id not in incoming_ids:
            image_url = node.get("data", {}).get("imageDataUrl", "")
            prefix = f"https://storage.googleapis.com/{bucket_name}/"
            if image_url.startswith(prefix):
                blob_paths.append(image_url[len(prefix):])

    if blob_paths:
        try:
            delete_blobs(gcs_client, bucket_name, blob_paths)
        except Exception as e:
            print(f"Error deleting removed node images: {e}")


def transform_nodes_arr_to_map(nodes_arr):
    nodes_map = {}
    for node in nodes_arr:
        nodes_map[node['id']] = node
    return nodes_map


def transform_nodes_map_to_arr(nodes_map):
    nodes = []
    for node in nodes_map.values():
        nodes.append(node)
    return nodes
