import json
import os
from langchain_together import ChatTogether
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from functools import partial
from src.db.firestore import get_document_by_collection_and_id


llama_8b = ChatTogether(
    model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    together_api_key=os.getenv("TOGETHER_API_KEY"),
    temperature=0.7,
)
mixtral_56b = ChatTogether(
    model="mistralai/Mixtral-8x7B-Instruct-v0.1",
    together_api_key=os.getenv("TOGETHER_API_KEY"),
)
openai_120b = ChatTogether(
    model="openai/gpt-oss-120b",
    together_api_key=os.getenv("TOGETHER_API_KEY")
)


def get_model(model_name):
    if model_name == "llama_8b":
        llm = llama_8b
    elif model_name == "mixtral_56b":
        llm = mixtral_56b
    elif model_name == "openai_120b":
        llm = openai_120b
    else:
        raise ValueError(f"Unsupported model type: {model_name}")
    
    return llm


context_prompt_question_template = PromptTemplate(
    input_variables=["context"],
    template="""Given the following context, generate an interesting follow up question intended to induce curisoity.
If no context is provided, generate a question users will be curious to know the answer to.
Always end with a question mark. DO NOT surround the question in quotes.
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
        prompt_response = node["data"]["prompt_response"]
        prev_chat_responses.append(f"Response {index+1}: {prompt_response}")

    return prev_chat_responses


def generate_prompt_question(parent_nodes):
    """Generate a prompt suggestion"""
    parent_responses = get_parent_responses(parent_nodes=parent_nodes)
    context = "\n\n".join(parent_responses)

    chain = context_prompt_question_template | llama_8b
    prompt_question = chain.invoke({ "context": context })
    
    return prompt_question.content if hasattr(prompt_question, 'content') else str(prompt_question)


def generate_response_with_context(
        model: str,
        prompt: str,
        parent_nodes: list,
):
    parent_responses = get_parent_responses(parent_nodes=parent_nodes)
    context = "\n\n".join(parent_responses)

    llm = get_model(model)

    chain = context_prompt_template | llm

    response_with_context = chain.invoke({
        "context": context,
        "prompt": prompt
    })
        
    return response_with_context.content if hasattr(response_with_context, 'content') else str(response_with_context)


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
