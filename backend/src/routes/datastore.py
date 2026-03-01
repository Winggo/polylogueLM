from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from src.db.firestore import (
    get_document_by_collection_and_id,
    save_document_in_collection,
    update_document_in_collection,
)
from src.routes.validation.validate import validate_json, OptionalField


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
