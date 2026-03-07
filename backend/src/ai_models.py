import base64
import json
import os
from together import Together
from langchain_together import ChatTogether
from langchain_core.messages import HumanMessage
from google import genai
from google.genai import types
from src.db.firestore import get_document_by_collection_and_id

TOGETHER_MODEL_IDS = {
    "llamba4_17b": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
    "gemma3n_4b": "google/gemma-3n-E4B-it",
    "qwen3_8b": "Qwen/Qwen3-VL-8B-Instruct",
}

llamba4_17b = ChatTogether(
    model=TOGETHER_MODEL_IDS["llamba4_17b"],
    together_api_key=os.getenv("TOGETHER_API_KEY"),
    temperature=0.7,
)
gemma3n_4b = ChatTogether(
    model=TOGETHER_MODEL_IDS["gemma3n_4b"],
    together_api_key=os.getenv("TOGETHER_API_KEY"),
    temperature=0.7,
)
qwen3_8b = ChatTogether(
    model=TOGETHER_MODEL_IDS["qwen3_8b"],
    together_api_key=os.getenv("TOGETHER_API_KEY"),
    temperature=0.7,
)

IMAGE_MODELS = ["google/flash-image-2.5", "openai/gpt-image-1.5"]

GEMINI_VIDEO_MODEL = "gemini-2.0-flash"


def _get_gemini_client():
    return genai.Client(
        vertexai=True,
        project=os.getenv("GCP_PROJECT"),
        location=os.getenv("GEMINI_LOCATION", "us-central1"),
    )


def _make_gemini_video_part(video_url):
    """Create a Gemini Part from a video — GCS HTTPS URL or base64 data URL."""
    if video_url.startswith("data:"):
        header, b64_data = video_url.split(",", 1)
        mime_type = header.split(";")[0].split(":")[1]
        return types.Part.from_bytes(data=base64.b64decode(b64_data), mime_type=mime_type)
    if video_url.startswith("https://storage.googleapis.com/"):
        gcs_uri = "gs://" + video_url[len("https://storage.googleapis.com/"):]
        ext = video_url.rsplit(".", 1)[-1].lower()
        mime_type = {"webm": "video/webm", "mov": "video/quicktime"}.get(ext, "video/mp4")
        return types.Part.from_uri(file_uri=gcs_uri, mime_type=mime_type)
    return types.Part.from_uri(file_uri=video_url, mime_type="video/mp4")


def _make_gemini_image_part(data_url):
    """Create a Gemini Part from an image — GCS HTTPS URL or base64 data URL."""
    if data_url.startswith("data:"):
        header, b64_data = data_url.split(",", 1)
        mime_type = header.split(";")[0].split(":")[1]
        return types.Part.from_bytes(data=base64.b64decode(b64_data), mime_type=mime_type)
    if data_url.startswith("https://storage.googleapis.com/"):
        gcs_uri = "gs://" + data_url[len("https://storage.googleapis.com/"):]
        ext = data_url.rsplit(".", 1)[-1].lower().split("?")[0]
        mime_type = {"png": "image/png", "gif": "image/gif", "webp": "image/webp"}.get(ext, "image/jpeg")
        return types.Part.from_uri(file_uri=gcs_uri, mime_type=mime_type)
    return types.Part.from_uri(file_uri=data_url, mime_type="image/jpeg")


def get_model(model_name):
    if model_name == "llamba4_17b":
        llm = llamba4_17b
    elif model_name == "gemma3n_4b":
        llm = gemma3n_4b
    elif model_name == "qwen3_8b":
        llm = qwen3_8b
    else:
        raise ValueError(f"Unsupported model type: {model_name}")

    return llm


def get_together_model_name(model_name):
    if model_name not in TOGETHER_MODEL_IDS:
        raise ValueError(f"Unsupported model type: {model_name}")
    return TOGETHER_MODEL_IDS[model_name]


prompt_question_closing = """Always end with a question mark. DO NOT surround the question in quotes. RETURN ENGLISH ONLY.
*IMPORTANT: GENERATED QUESTION MUST USE LESS THAN 8 WORDS*."""

no_context_prompt_question_preamble = f"""Generate a question users will be curious to know the answer to.
{prompt_question_closing}"""

with_context_prompt_question_preamble = f"""Given the following context text, image data, and video data, generate an interesting follow up question intended to induce curisoity.
There may be no context text, image data, or video data provided, in which case generate a fitting question to the best of your ability.
{prompt_question_closing}"""

video_prompt_question_preamble = f"""Analyze the provided video content and generate an interesting follow up question intended to induce curiosity.
{prompt_question_closing}"""


image_prompt_question_closing = """Start the suggestion with "Generate an image of...".
*IMPORTANT: GENERATED SUGGESTION MUST USE LESS THAN 8 WORDS*."""

no_context_image_prompt_question_preamble = f"""Return an interesting and creative image generation suggestion.
{image_prompt_question_closing}"""

with_context_image_prompt_question_preamble = f"""Given the following context text and image data, return an image generation suggestion.
If no context, image data, or video data is provided, return an interesting and creative image generation suggestion.
{image_prompt_question_closing}"""


context_prompt_preamble = """Given the following context text, image data, video data, and user prompt, reply thoughtfully in *LESS THAN 150 WORDS*.
If no context is provided, simply address the prompt by itself. Do not mention the response or context name. Seperate ideas into paragraphs, use bulletpoints, numbered lists, bolded & italicized words or phrases for better readability.
Add newlines between each bullet point."""


def extract_parent_data(parent_nodes=None):
    """Returns (text_responses, image_data_urls, video_data_urls) from parent nodes."""
    text_responses = []
    image_data_urls = []
    video_data_urls = []

    for index, node in enumerate(parent_nodes or []):
        node_data = node.get("data", {})
        if node.get("type") == "imageNode":
            data_url = node_data.get("imageDataUrl", "")
            if data_url:
                image_data_urls.append(data_url)
        elif node.get("type") == "videoNode":
            data_url = node_data.get("videoDataUrl", "")
            if data_url:
                video_data_urls.append(data_url)
        else:
            prompt_response = node_data.get("prompt_response", "")
            if prompt_response:
                text_responses.append(f"Response {index+1}: {prompt_response}")

    return text_responses, image_data_urls, video_data_urls


def generate_prompt_question(parent_nodes, model=None):
    """Generate a prompt suggestion"""
    text_responses, image_data_urls, video_data_urls = extract_parent_data(parent_nodes=parent_nodes)

    try:
        content_parts = []

        if video_data_urls:
            try:
                gemini = _get_gemini_client()
                parts = [video_prompt_question_preamble]
                for video_url in video_data_urls:
                    parts.append(_make_gemini_video_part(video_url))
                response = gemini.models.generate_content(
                    model=GEMINI_VIDEO_MODEL,
                    contents=parts,
                )
                return response.text
            except Exception as e:
                print(f"Error generating video prompt question with Gemini: {e}")
                return "Sorry, I encountered an error processing your request."

        preamble = no_context_prompt_question_preamble
        if text_responses or image_data_urls or video_data_urls:
            preamble = with_context_prompt_question_preamble

        if model in IMAGE_MODELS:
            preamble = no_context_image_prompt_question_preamble
            if text_responses or image_data_urls or video_data_urls:
                preamble = with_context_image_prompt_question_preamble

        content_parts.append({"type": "text", "text": preamble})

        if text_responses:
            context_text = "\n\n".join(text_responses)
            text_context = f"*Context:*\n{context_text}\n\n"
            content_parts.append({"type": "text", "text": text_context})

        if image_data_urls:
            for data_url in image_data_urls:
                content_parts.append({"type": "image_url", "image_url": {"url": data_url}})

        message = HumanMessage(content=content_parts)
        prompt_question = gemma3n_4b.invoke([message])
        
        return prompt_question.content if hasattr(prompt_question, 'content') else str(prompt_question)
    except Exception as e:
        print(f"Error generating response: {e}")
        return "Sorry, I encountered an error processing your request."


def generate_response_with_context(
        model: str,
        prompt: str,
        parent_nodes: list,
):
    text_responses, image_data_urls, video_data_urls = extract_parent_data(parent_nodes=parent_nodes)
    content_parts = [{"type": "text", "text": context_prompt_preamble}]

    if text_responses:
        context_text = "\n\n".join(text_responses)
        text_context = f"*Context:*\n{context_text}\n\n"
        content_parts.append({"type": "text", "text": text_context})

    if image_data_urls:
        for data_url in image_data_urls:
            content_parts.append({"type": "image_url", "image_url": {"url": data_url}})

    if video_data_urls:
        try:
            gemini = _get_gemini_client()
            parts = [context_prompt_preamble]
            if text_responses:
                context_text = "\n\n".join(text_responses)
                parts.append(f"*Context:*\n{context_text}\n\n")
            for data_url in image_data_urls:
                parts.append(_make_gemini_image_part(data_url))
            for video_url in video_data_urls:
                parts.append(_make_gemini_video_part(video_url))
            parts.append(prompt)
            response = gemini.models.generate_content(
                model=GEMINI_VIDEO_MODEL,
                contents=parts,
            )
            return response.text
        except Exception as e:
            print(f"Error generating response with video context: {e}")
            return "Sorry, I encountered an error processing your request."

    llm = get_model(model)
    try:
        content_parts.append({"type": "text", "text": prompt})
        message = HumanMessage(content=content_parts)
        response = llm.invoke([message])
        return response.content if hasattr(response, 'content') else str(response)
    except Exception as e:
        print(f"Error generating response: {e}")
        return "Sorry, I encountered an error processing your request."


def describe_images(image_data_urls):
    """Use gemma3n_4b to describe parent images as text for image gen context."""
    descriptions = []
    for data_url in image_data_urls:
        try:
            message = HumanMessage(content=[
                {"type": "text", "text": "Describe this image concisely in 2-3 sentences. Specify colors, subjects, style, composition, and overall mood."},
                {"type": "image_url", "image_url": {"url": data_url}},
            ])
            response = gemma3n_4b.invoke([message])
            desc = response.content if hasattr(response, 'content') else str(response)
            descriptions.append(desc)
        except Exception as e:
            print(f"Error describing image: {e}")
    return descriptions


def generate_image_with_context(
    model: str,
    prompt: str,
    parent_nodes: list,
):
    text_responses, image_data_urls, _ = extract_parent_data(parent_nodes=parent_nodes)

    # Build enriched prompt with parent text context
    full_prompt = prompt
    context_parts = []
    if text_responses:
        context_parts.extend(text_responses)

    if image_data_urls:
        image_descriptions = describe_images(image_data_urls)
        context_parts.extend([f"Image description: {d}" for d in image_descriptions])

    if context_parts:
        context = "\n".join(context_parts)
        full_prompt = f"Context: {context}\n\nPrompt: {prompt}"

    try:
        client = Together(api_key=os.getenv("TOGETHER_API_KEY"))
        response = client.images.generate(
            model=model,
            prompt=full_prompt,
            response_format="base64",
        )
        b64_json = response.data[0].b64_json
        return f"data:image/png;base64,{b64_json}"
    except Exception as e:
        print(f"Error generating image: {e}")
        return "Sorry, I encountered an error generating the image."



def get_ancestor_nodes(redis, node_id) -> list:
    """Get all ancestor nodes for a given node_id, including the node itself"""
    def get_parent_nodes(node_id)->None:
        if node_id in visited_node_ids or not redis.exists(f"node:{node_id}"):
            return
        visited_node_ids.add(node_id)
        cur_node = redis.hgetall(f"node:{node_id}")
        decoded_cur_node = {
            k.decode('utf-8') : v.decode('utf-8')
            for k, v in cur_node.items()
            if k.decode('utf-8') in {"model", "prompt", "parent_ids"}
        }
        decoded_cur_node["id"] = node_id
        decoded_cur_node["parent_ids"] = json.loads(decoded_cur_node["parent_ids"])
        for parent_id in decoded_cur_node["parent_ids"]:
            get_parent_nodes(parent_id)
        # append node after so that root node is always first
        ancestor_nodes.append(decoded_cur_node)

    visited_node_ids = set()
    ancestor_nodes = []
    get_parent_nodes(node_id)
    ancestor_nodes.pop()
    return ancestor_nodes


def get_parent_responses_from_redis(redis, parent_nodes=None) -> list:
    if not parent_nodes:
        return []

    prev_chat_responses = []
    for index, node in enumerate(parent_nodes):
            node_id = node["id"]
            if redis.exists(f"node:{node_id}"):
                prompt_response = redis.hget(f"node:{node_id}", "prompt_response").decode('utf-8')
                prev_chat_responses.append(f"Response {index+1}: {prompt_response}")
    return prev_chat_responses


def get_parent_responses_from_firestore(db, parent_nodes=None) -> list:
    if not parent_nodes:
        return []
    
    prev_chat_responses = []
    canvas_doc_id = parent_nodes[0]["data"].get("canvasId")
    if not canvas_doc_id:
        return []
    try:
        canvas_doc = get_document_by_collection_and_id(db, "canvases", canvas_doc_id)
    except ValueError:
        return []
    canvas_nodes = canvas_doc["nodes"]
    for index, node in enumerate(parent_nodes):
        node_id = node["id"]
        if node_id in canvas_nodes:
            prompt_response = canvas_nodes[node_id]["data"].get("prompt_response")
            if prompt_response:
                prev_chat_responses.append(f"Response {index+1}: {prompt_response}")
    return prev_chat_responses
