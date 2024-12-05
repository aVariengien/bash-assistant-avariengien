# %%
import streamlit as st
import anthropic
import os
import json
import yaml
import random as rd
from PIL import Image
import requests
from io import StringIO
from openai import OpenAI


# Function to read learning data
def read_learning_data(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_context_vocabulary(N=150):
    """
    Returns approximatively N words and their data from the contextual data, sample equaly from each category new, in progress and acquired.
    """
    all_words = read_learning_data(data_file)

    acquired = [
        {k: all_words[k]} for k in all_words.keys() if all_words[k]["status"] == "acquired"
    ]
    in_progress = [
        {k: all_words[k]} for k in all_words.keys() if all_words[k]["status"] == "in progress"
    ]
    new = [
        {k: all_words[k]} for k in all_words.keys() if all_words[k]["status"] == "new"
    ]
    words_per_type = N // 3
    words = (
        rd.sample(acquired, min(words_per_type, len(acquired)))
        + rd.sample(in_progress, min(words_per_type, len(in_progress)))
        + rd.sample(new, min(words_per_type, len(new)))
    )
    return words

# Function to get a random subset of a dictionary
def random_subdict(d, n):
    keys = rd.sample(list(d.keys()), n)
    return {k: d[k] for k in keys}


# Load data and prompts
data_file = os.path.join(os.curdir, "../data/kratt_data.json")
prompt_file = os.path.join(os.curdir, "prompts.yaml")
image_folder = os.path.join(os.curdir, "../data/kratt_images")

context_vocab = get_context_vocabulary(N=150)
highlighted_data = rd.sample(context_vocab, 3)
# # %%
# Load system prompt
with open(prompt_file, "r") as file:
    prompts = yaml.safe_load(file)
    system_prompt = prompts["KRATT"]

system_prompt = system_prompt.format(
    HIGHLIGHTED_LEARNING_DATA=json.dumps(highlighted_data),
    LEARNING_DATA=json.dumps(context_vocab),
)


# Function to update learning data
def update_learning_data(updates):
    learning_data = read_learning_data(data_file)
    for key, value in updates.items():
        if key in learning_data:
            learning_data[key]["nb_exposure"] += 1
            if value == "acquired":
                learning_data[key]["status"] = "acquired"
            elif value == "exposed":
                if learning_data[key]["nb_exposure"] >= 5:
                    learning_data[key]["status"] = "work in progress"
                else:
                    learning_data[key]["status"] = "new"
        else:
            learning_data[key] = {"nb_exposure": 1, "status": "new"}

    with open(data_file, "w", encoding="utf-8") as file:
        json.dump(learning_data, file, ensure_ascii=False, indent=4)


# Initialize Anthropic client
client = anthropic.Anthropic()


# Function to generate update dictionary
def generate_update_dict(chat_history, context_vocab):

    chat_content = "\n".join(
        [f"{msg['role']}: {msg['content']}" for msg in chat_history]
    )

    prompt = f"""
    Given the following learning data and chat history, generate a JSON update for the Estonian language learning progress.

    ### Learning Data:
    {context_vocab}

    ### Chat History:
    {chat_content}

    ### Instructions
    Create a JSON update with the following structure:
    1. For new words/sentences introduced in the chat: "word/sentence": "new"
    2. For words the user successfully used themselves: "word/sentence": "acquired"
    3. For words that were used by the user but approximatively (e.g incorect spelling): "word/sentence": "in progress"

    Only include useful new vocabulary, grammar tips, or sentence structures helpful for beginner Estonian learners. Include only Estonian sentences. Put *asterix* to emphasize the crucial part of a sentence. 
    Ensure the output is in valid JSON format like the example below. If a word has been seen in a new context and is present in the learning data, use the sentence of the learning data as a handle, else use the sentence where the word has been introduced, and highlight the word with *asterisks*.
    "Ma olen *õnnelik*.": "acquired",
    "Ärka *üles*!": "new",
    etc.

    ### Format of the answer

    Only output the correct json, nothing else.
    """

    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,
        system="You are an AI assistant that analyzes interaction with an AI Estonian tutor. Your role is to track language learning progress.",
        messages=[
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": "{"},
        ],
    )

    update_json = "{" + response.content[0].text
    st.success(update_json)
    updates = json.loads(update_json)

    return updates


# Function to display and validate updates
def display_and_validate_updates(updates):
    st.write("Here are the proposed updates to the learning data:")
    st.json(updates)

    if st.button("Confirm Updates"):
        update_learning_data(updates)
        st.success("Learning data updated successfully!")
    else:
        st.write("You can edit the updates below:")
        edited_updates = st.text_area(
            "Edit updates (JSON format)", json.dumps(updates, indent=2)
        )
        if st.button("Apply Edited Updates"):
            try:
                edited_updates_dict = json.loads(edited_updates)
                update_learning_data(edited_updates_dict)
                st.success("Edited learning data updated successfully!")
            except json.JSONDecodeError:
                st.error("Invalid JSON format. Please check your edits.")


def generate_image(prompt):
    client = OpenAI()
    response = client.images.generate(
        model="dall-e-2",
        prompt=prompt,
        n=1,
        size="1024x1024",
        response_format="url",
    )
    image_url = response.data[0].url
    image = Image.open(requests.get(image_url, stream=True).raw)
    return image


# Streamlit UI
st.set_page_config(page_title="Kratt - Estonian Language Tutor", page_icon="🤖")
st.title("🤖 Kratt - Your Estonian Language Tutor")
st.caption("Learn Estonian with the help of folklore-inspired AI!")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Chat input
if prompt := st.chat_input():
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        st.session_state.messages[-1]["content"] = prompt
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

    messages = st.session_state.messages

    # Generate response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        with client.messages.stream(
            model="claude-3-5-sonnet-20241022", # claude-3-5-haiku-20241022 
            max_tokens=1000,
            messages=messages,
            system=system_prompt,
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                if "<i" in full_response:
                    response = full_response[: full_response.index("<i")]
                    message_placeholder.markdown(response)
                else:
                    message_placeholder.markdown(full_response + "▌")

    # Check for image generation request
    if "<image_generation" in full_response:
        start = full_response.index('<image_generation prompt="') + len(
            '<image_generation prompt="'
        )
        end = full_response.index('">', start)
        image_prompt = full_response[start:end]
        image = generate_image(image_prompt)
        st.image(image)
        display_message = full_response.replace(
            f'<image_generation prompt="{image_prompt}">', ""
        )
    else:
        display_message = full_response

    message_placeholder.markdown(display_message)
    st.session_state.messages.append({"role": "assistant", "content": full_response})

if st.button("Update Learning Data"):
    updates = generate_update_dict(st.session_state.messages, context_vocab)
    display_and_validate_updates(updates)

# Add a button to clear the chat history
if st.button("Clear Chat History"):
    st.session_state.messages = []
    st.rerun()

# %%
