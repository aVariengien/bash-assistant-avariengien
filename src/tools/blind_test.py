# %%
from openai import OpenAI
from os import getenv
import streamlit as st
import os
from pprint import pprint
import random as rd
import time
import requests
import asyncio
import time
# gets API Key from environment variable OPENAI_API_KEY


# %% All model def
ALL_MODELS = {
    "meta": [
        "meta-llama/llama-3.1-8b-instruct:free",
        "meta-llama/llama-3.1-70b-instruct",
        "meta-llama/llama-3.1-405b-instruct",
        # "meta-llama/llama-3-70b",
        # "meta-llama/llama-3-8b"
    ],
    "openai": [
        "openai/gpt-4o-mini-2024-07-18",
        "openai/gpt-4o-mini"
    ],
    "cognitivecomputations": [
        "cognitivecomputations/dolphin-llama-3-70b",
        "cognitivecomputations/dolphin-mixtral-8x22b"
    ],
    "mistralai": [
        "mistralai/codestral-mamba",
        "mistralai/mistral-nemo",
        "mistralai/mistral-7b-instruct-v0.3",
        "mistralai/mistral-7b-instruct",
        "mistralai/mistral-medium",
        "mistralai/mistral-small",
        "mistralai/mistral-tiny"
    ],
    "qwen": [
        # "qwen/qwen-2-7b-instruct:free",
        # "qwen/qwen-2-72b-instruct",
        "qwen/qwen-4b-chat",
        "qwen/qwen-7b-chat",
        "qwen/qwen-14b-chat",
        "qwen/qwen-32b-chat",
        "qwen/qwen-72b-chat",
        "qwen/qwen-110b-chat"
    ],
    "google": [
        "google/gemma-2-27b-it",
        "google/gemma-2-9b-it:free",
        "google/gemini-pro-1.5",
        "google/gemini-pro"
    ],
    "alpindale": [
        "alpindale/magnum-72b"
    ],
    "nousresearch": [
        "nousresearch/hermes-2-theta-llama-3-8b",
        "nousresearch/hermes-2-pro-llama-3-8b"
    ],
    "ai21": [
        "ai21/jamba-instruct"
    ],
    "01-ai": [
        "01-ai/yi-large"
    ],
    "anthropic": [
        "anthropic/claude-3.5-sonnet:beta",
        "anthropic/claude-3.5-sonnet",
        "anthropic/claude-3-haiku:beta",
        "anthropic/claude-3-sonnet:beta",
        "anthropic/claude-3-opus:beta",
        "anthropic/claude-3-sonnet",
        "anthropic/claude-3-opus"
    ],
    "sao10k": [
        "sao10k/l3-stheno-8b",
        "sao10k/l3-euryale-70b"
    ],
    "microsoft": [
        "microsoft/phi-3-medium-4k-instruct",
        "microsoft/phi-3-mini-128k-instruct",
        "microsoft/phi-3-medium-128k-instruct",
    ],
    "openchat": [
        "openchat/openchat-8b"
    ],
    "perplexity": [
        "perplexity/llama-3-sonar-large-32k-online"
    ],
    "rwkv": [
        "rwkv/rwkv-5-world-3b"
    ],
    "togethercomputer": [
        "togethercomputer/stripedhyena-nous-7b"
    ],
    "gryphe": [
        "gryphe/mythomist-7b",
        "gryphe/mythomax-l2-13b:extended",
        "gryphe/mythomax-l2-13b"
    ],
    "open-orca": [
        "open-orca/mistral-7b-openorca"
    ],
    "custom-selection": [
        "meta-llama/llama-3.1-8b-instruct:free",
        "meta-llama/llama-3.1-70b-instruct",
        "meta-llama/llama-3.1-405b-instruct",
        "qwen/qwen-4b-chat",
    ]
}


# custum_models = [
#         "meta-llama/llama-3.1-8b-instruct:free",
#         "meta-llama/llama-3.1-70b-instruct",
#         "meta-llama/llama-3.1-405b-instruct",
#         "openai/gpt-4o-mini",
#         "openai/gpt-4",
#         "openai/gpt-4o",
#         "microsoft/phi-3-mini-128k-instruct",
#         "anthropic/claude-3.5-sonnet",
#        "anthropic/claude-3-sonnet",
#         "anthropic/claude-3-opus",
#         "anthropic/claude-3-haiku:beta",
#         "qwen/qwen-4b-chat",
#         "google/gemini-pro",
#         "google/gemini-flash-1.5"
# ]

# %%

def get_model_list(providers=[]):
    if len(providers) == 0:
        providers = ALL_MODELS.keys()
    all_model_names = [model for k in providers for model in ALL_MODELS[k]]
    return all_model_names
def get_random_model(providers=[]):
    all_model_names = get_model_list(providers)
    return rd.choice(all_model_names)


def delayed_write(stream, delay = 0.05):
    message = ""
    placeholder = st.empty()
    last_write_time = time.time()
    buffer = []
    buffer_idx = 0

    start_time = time.time()
    nb_token = 0

    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            buffer.append(chunk.choices[0].delta.content)
            current_time = time.time()
            nb_token +=1
            
            if current_time - last_write_time >= delay:  # 100 ms
                message += buffer[buffer_idx]
                buffer_idx +=1
                placeholder.write(message)
                last_write_time = current_time
            
            #time.sleep(0.01)  # Small sleep to allow for other operations

    # print((time.time() - start_time) / nb_token) # to have an estimate of seconds/token

    # Write any remaining buffer
    while buffer_idx < len(buffer):
        message += buffer[buffer_idx]
        buffer_idx +=1
        placeholder.write(message)
        time.sleep(delay)

    return message

metadata_url = "https://openrouter.ai/api/v1/models"
PROVIDERS = ["custom-selection"]

if "messages" not in st.session_state:
    st.session_state["messages"] = []
    st.session_state["model"] = get_random_model(PROVIDERS)
    #print(st.session_state["model"])
    response = requests.get(metadata_url)
    response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
    
    data = response.json()  # Parse the JSON response
    st.session_state["all_metadata"] = data["data"]

st.title("👁️ LLM Blind Test")
st.caption("Guess who's you're speaking to.")

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])


if prompt := st.chat_input():
    if "!guess" in prompt:
        for data in st.session_state["all_metadata"]:
            if data["id"] == st.session_state["model"]:
                model_description = data["description"]
        final_message = 'You are speaking to {model}. Here is a description of the model. This interaction will be ignored in the following chat. \n\n {description}'.format(model=st.session_state["model"], description=model_description)
        st.chat_message("assistant").write(final_message)
    elif "!models" in prompt:
        st.chat_message("assistant").write(f"The pool of models is {get_model_list(PROVIDERS)}")
    elif "!new" in prompt:
        st.chat_message("assistant").write(f"You're now interacting with a new model! 🤖✨\n Previous model: {st.session_state["model"]}")
        st.session_state["messages"] = []
        st.session_state["model"] = get_random_model(PROVIDERS)
    elif "!reset" in prompt:
        st.chat_message("assistant").write(f"The conversation has been reset. 🧹")
        st.session_state["messages"] = []
    else:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=getenv("OPENROUTER_API_KEY"),
            timeout=5.0,
        )
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        with st.chat_message("assistant"):
            with client.chat.completions.create(
            model=st.session_state["model"],
            messages=st.session_state.messages,
            temperature=0,
            stream=True,  # again, we set stream=True
            ) as stream:
                response = delayed_write(stream)
                #response = asyncio.run(delayed_write(stream))
        st.session_state.messages.append({"role": "assistant", "content": response})


