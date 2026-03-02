import json
import os
from langchain_together import ChatTogether
from langchain.prompts import PromptTemplate
from langchain_core.messages import HumanMessage
from src.db.firestore import get_document_by_collection_and_id


llamba4_17b = ChatTogether(
    model="meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
    together_api_key=os.getenv("TOGETHER_API_KEY"),
    temperature=0.7,
)
gemma3n_4b = ChatTogether(
    model="google/gemma-3n-E4B-it",
    together_api_key=os.getenv("TOGETHER_API_KEY"),
    temperature=0.7,
)
qwen3_8b = ChatTogether(
    model="Qwen/Qwen3-VL-8B-Instruct",
    together_api_key=os.getenv("TOGETHER_API_KEY"),
    temperature=0.7,
)

IMAGE_MODELS = ["gemini_flash_image", "openai_gpt_image"]


def get_model(model_name):
    if model_name == "llamba4_17b":
        llm = llamba4_17b
    elif model_name == "gemma3n_4b":
        llm = gemma3n_4b
    elif model_name == "qwen3_8b":
        llm = qwen3_8b
    elif model_name == "gemini_flash_image":
        llm = gemini_flash_image
    elif model_name == "openai_gpt_image":
        llm = openai_gpt_image
    else:
        raise ValueError(f"Unsupported model type: {model_name}")

    return llm


context_prompt_question_template = PromptTemplate(
    input_variables=["context"],
    template="""Given the following context, generate an interesting follow up question intended to induce curisoity.
If no context is provided, generate a question users will be curious to know the answer to.
Always end with a question mark. DO NOT surround the question in quotes. RETURN ENGLISH ONLY.
*IMPORTANT: GENERATED QUESTION MUST USE LESS THAN 8 WORDS*.
*Context:*
{context}"""
)

prompt_question_preamble = """Given the following context text and image data in base 64 format, generate an interesting follow up question intended to induce curisoity.
If no context or image data is provided, generate a question users will be curious to know the answer to.
Always end with a question mark. DO NOT surround the question in quotes. RETURN ENGLISH ONLY.
*IMPORTANT: GENERATED QUESTION MUST USE LESS THAN 8 WORDS*."""



context_prompt_template = PromptTemplate(
    input_variables=["context", "prompt"],
    template="""Given the following context and prompt, reply thoughtfully in *LESS THAN 150 WORDS*.
There may be no context provided. Do not mention the response or context name.
Seperate ideas into paragraphs, use bullet points, numbered lists, bolded & italicized words or phrases for better readability.
Add newlines between each bullet point.
*Context:*
{context}

----------------------------------------------------------------------------
*Prompt:*
{prompt}"""
)

context_prompt_preamble = """Given the following context text, image data in base64 format, and user prompt, reply thoughtfully in *LESS THAN 150 WORDS*.
If no context is provided, simply address the prompt by itself. Do not mention the response or context name. Seperate ideas into paragraphs, use bulletpoints, numbered lists, bolded & italicized words or phrases for better readability.
Add newlines between each bullet point."""


def extract_parent_data(parent_nodes=None):
    """Returns (text_responses, image_data_urls) from parent nodes."""
    text_responses = []
    image_data_urls = []

    for index, node in enumerate(parent_nodes or []):
        if node.get("type") == "imageNode":
            data_url = node["data"].get("imageDataUrl", "")
            if data_url:
                image_data_urls.append(data_url)
        else:
            prompt_response = node["data"].get("prompt_response", "")
            if prompt_response:
                text_responses.append(f"Response {index+1}: {prompt_response}")

    return text_responses, image_data_urls


def generate_prompt_question(parent_nodes, model=None):
    """Generate a prompt suggestion"""
    text_responses, image_data_urls = extract_parent_data(parent_nodes=parent_nodes)
    context = "\n\n".join(text_responses)

    try:
        if image_data_urls:
            content_parts = []

            content_parts.append({"type": "text", "text": prompt_question_preamble})

            if text_responses:
                context_text = "\n\n".join(text_responses)
                text_context = f"*Context:*\n{context_text}\n\n"
                content_parts.append({"type": "text", "text": text_context})

            for data_url in image_data_urls:
                content_parts.append({"type": "image_url", "image_url": {"url": data_url}})

            message = HumanMessage(content=content_parts)
            prompt_question = gemma3n_4b.invoke([message])
        else:
            chain = context_prompt_question_template | gemma3n_4b
            prompt_question = chain.invoke({ "context": context })
        
        return prompt_question.content if hasattr(prompt_question, 'content') else str(prompt_question)
    except Exception as e:
        print(f"Error generating response: {e}")
        return "Sorry, I encountered an error processing your request."


def generate_response_with_context(
        model: str,
        prompt: str,
        parent_nodes: list,
):
    text_responses, image_data_urls = extract_parent_data(parent_nodes=parent_nodes)
    llm = get_model(model)

    try:
        if image_data_urls:
            content_parts = []

            content_parts.append({"type": "text", "text": context_prompt_preamble})

            if text_responses:
                context_text = "\n\n".join(text_responses)
                text_context = f"*Context:*\n{context_text}\n\n"
                content_parts.append({"type": "text", "text": text_context})

            for data_url in image_data_urls:
                content_parts.append({"type": "image_url", "image_url": {"url": data_url}})

            content_parts.append({"type": "text", "text": prompt})

            message = HumanMessage(content=content_parts)
            response = llm.invoke([message])
        else:
            context = "\n\n".join(text_responses)
            chain = context_prompt_template | llm
            response = chain.invoke({"context": context, "prompt": prompt})

        return response.content if hasattr(response, 'content') else str(response)
    except Exception as e:
        print(f"Error generating response: {e}")
        return "Sorry, I encountered an error processing your request."


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
