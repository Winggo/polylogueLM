import json
import os
from langchain_together import ChatTogether
from langchain.prompts import PromptTemplate
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableLambda
from functools import partial
from src.db.firestore import get_document_by_collection_and_id


qwen_7b = ChatTogether(
    model="Qwen/Qwen2.5-7B-Instruct-Turbo",
    together_api_key=os.getenv("TOGETHER_API_KEY"),
    temperature=0.7,
)
llamba4_17b = ChatTogether(
    model="meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
    together_api_key=os.getenv("TOGETHER_API_KEY"),
)
gemma3n_4b = ChatTogether(
    model="google/gemma-3n-E4B-it",
    together_api_key=os.getenv("TOGETHER_API_KEY"),
)
qwen3_8b = ChatTogether(
    model="Qwen/Qwen3-VL-8B-Instruct",
    together_api_key=os.getenv("TOGETHER_API_KEY"),
    temperature=0.7,
)


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


context_prompt_question_template = PromptTemplate(
    input_variables=["context"],
    template="""Given the following context, generate an interesting follow up question intended to induce curisoity.
If no context is provided, generate a question users will be curious to know the answer to.
Always end with a question mark. DO NOT surround the question in quotes. RETURN ENGLISH ONLY.
*IMPORTANT: GENERATED QUESTION NEEDS TO USE LESS THAN 8 WORDS*.
*Context:*
{context}"""
)


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


def get_parent_responses(parent_nodes=None) -> list:
    if not parent_nodes:
        return []

    prev_chat_responses = []
    for index, node in enumerate(parent_nodes):
        if node.get("type") == "imageNode":
            continue
        prompt_response = node["data"].get("prompt_response", "")
        if prompt_response:
            prev_chat_responses.append(f"Response {index+1}: {prompt_response}")

    return prev_chat_responses


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


def generate_prompt_question(parent_nodes):
    """Generate a prompt suggestion"""
    parent_responses = get_parent_responses(parent_nodes=parent_nodes)
    context = "\n\n".join(parent_responses)

    chain = context_prompt_question_template | qwen_7b
    prompt_question = chain.invoke({ "context": context })
    
    return prompt_question.content if hasattr(prompt_question, 'content') else str(prompt_question)


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

            preamble = """Given the following context text, image data in base64 format, and user prompt, reply thoughtfully in *LESS THAN 150 WORDS*.
If no context is provided, simply address the prompt by itself. Do not mention the response or context name. Seperate ideas into paragraphs, use bulletpoints, numbered lists, bolded & italicized words or phrases for better readability.
Add newlines between each bullet point."""
            content_parts.append({"type": "text", "text": preamble})

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
    

def generate_chained_responses(redis, cur_node):
    ancestor_nodes = get_ancestor_nodes(redis, cur_node["id"])
    ancestor_nodes.append(cur_node)

    initial_inputs = {}
    output_keys = []

    node_operations = []
    for node in ancestor_nodes:
        llm = get_model(node["model"])

        prompt_input_key = f"node-input-prompt-{node['id']}"
        output_key = f"node-output-{node['id']}"
        parent_outputs = [f"node-output-{parent_id}" for parent_id in node['parent_ids']]

        initial_inputs[prompt_input_key] = node["prompt"]
        output_keys.append(output_key)

        template = """Given the past dialog and prompt, reply thoughtfully in less than 120 words.
There may be multiple or no past conversations.
*Past Conversations:*\n"""
        for parent_output in parent_outputs:
            template += "Conversation: {" + parent_output + "}\n\n"
        template += """----------------------------------------------------------------------------
*Prompt:*\n""" + "{" + prompt_input_key + "}"

        prompt_template = PromptTemplate(
            input_variables=parent_outputs + [prompt_input_key],
            template=template,
        )

        def process_node(inputs, node_llm, node_prompt_template, node_output_key):
            # Gather all required inputs
            prompt_input = inputs[node_prompt_template.input_variables[-1]]  # Last variable is the prompt
            parent_outputs = {
                k: inputs[k] 
                for k in node_prompt_template.input_variables 
                if k != node_prompt_template.input_variables[-1]
            }
            
            # Format the prompt
            formatted_prompt = node_prompt_template.format(
                **parent_outputs,
                **{node_prompt_template.input_variables[-1]: prompt_input}
            )
            
            # Get LLM response
            result = node_llm.invoke(formatted_prompt)
            
            # Return the output with our key
            return {node_output_key: result}
        
        node_operation = RunnableLambda(
            partial(
                process_node,
                node_llm=llm,
                node_prompt_template=prompt_template,
                node_output_key=output_key
            )
        )
        node_operations.append(node_operation)
        

    print(f"Chain Prompt Input Values: {initial_inputs}")

    current_result = initial_inputs
    for operation in node_operations:
        current_result.update(operation.invoke(current_result))

    return {k: current_result[k] for k in output_keys}
