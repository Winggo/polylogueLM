from flask import Blueprint, jsonify, request, current_app

from src.ai_models import (
    generate_prompt_question,
    generate_response_with_context,
    IMAGE_MODELS,
    generate_image_with_context,
)
from src.db.storage import upload_parent_videos


api_routes = Blueprint("api_routes", __name__)


@api_routes.route("/v1/prompt", methods=["POST"])
def generate_prompt():
    """Generate a prompt, given context"""
    data = request.json

    try:
        prompt_question = generate_prompt_question(data.get("parentNodes", []), model=data.get("model"))
    except Exception as e:
        return jsonify({"error": "Internal Server Error"}), 500
    
    return jsonify({"prompt": prompt_question}), 200


@api_routes.route("/v1/completion", methods=["POST"])
def generate():
    """Generate prompt response, given a prompt"""

    data = request.json or {}
    for key in ["model", "prompt", "nodeId"]:
        if key not in data:
            return jsonify({"error": f"{key} is required"}), 400
    model, prompt = data["model"], data["prompt"]

    try:
        parent_nodes = data.get("parentNodes", [])
        canvas_id = data.get("canvasId", data.get("nodeId"))
        if parent_nodes:
            gcs_client = current_app.config.get("GCS")
            bucket_name = current_app.config.get("GCS_BUCKET")
            if gcs_client and bucket_name:
                upload_parent_videos(parent_nodes, canvas_id, gcs_client, bucket_name)

        if model in IMAGE_MODELS:
            image_completion = generate_image_with_context(
                model=model,
                prompt=prompt,
                parent_nodes=parent_nodes,
            )

            return jsonify({"response": image_completion}), 200
        else:
            prompt_completion = generate_response_with_context(
                model=model,
                prompt=prompt,
                parent_nodes=parent_nodes,
            )

            return jsonify({"response": prompt_completion}), 200

    except ValueError as e:
        return jsonify({"error": "Input Error"}), 400
    except Exception as e:
        return jsonify({"error": "Internal Server Error"}), 500
