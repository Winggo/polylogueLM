from flask import Blueprint, jsonify, request

from src.ai_models import (
    generate_prompt_question,
    generate_response_with_context,
    IMAGE_MODELS,
    generate_image_with_context,
)


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

    data = request.json
    model, prompt = data["model"], data["prompt"]
    for key in ["model", "prompt", "nodeId"]:
        if key not in data:
            return jsonify({"error": f"{key} is required"}), 400

    try:
        if model in IMAGE_MODELS:
            image_completion = generate_image_with_context(
                model=model,
                prompt=prompt,
                parent_nodes=data.get("parentNodes", []),
            )

            return jsonify({"response": image_completion}), 200
        else:
            prompt_completion = generate_response_with_context(
                model=model,
                prompt=prompt,
                parent_nodes=data.get("parentNodes", []),
            )

            return jsonify({"response": prompt_completion}), 200

    except ValueError as e:
        return jsonify({"error": "Input Error"}), 400
    except Exception as e:
        return jsonify({"error": "Internal Server Error"}), 500
