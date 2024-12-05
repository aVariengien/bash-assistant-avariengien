from openai import OpenAI
import streamlit as st
from PIL import Image
import requests  # type: ignore
import os
import yaml  # type: ignore
import json
import random as rd


def read_learning_data(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def random_subdict(d, n):
    keys = rd.sample(list(d.keys()), n)
    return {k: d[k] for k in keys}


data_file = os.path.join(os.curdir, "../data/kratt_data.json")

prompt_file = os.path.join(os.curdir, "prompts.yaml")

image_folder = os.path.join(os.curdir, "../data/kratt_images")

learning_data = read_learning_data(data_file)
highlighted_data = random_subdict(learning_data, n=3)

# Open the YAML file
with open(prompt_file, "r") as file:
    # Load the YAML content
    prompts = yaml.safe_load(file)
    system_prompt = prompts["KRATT"]

system_prompt = system_prompt.format(
    HIGHLIGHTED_LEARNING_DATA=json.dumps(highlighted_data),
    LEARNING_DATA=json.dumps(learning_data),
)


# Function to update the learning data
def update_learning_data(updates):
    global learning_data
    for key, value in updates.items():
        if key in learning_data:
            # Increment the exposure
            learning_data[key]["nb_exposure"] += 1

            # Update the status
            if value == "acquired":
                learning_data[key]["status"] = "acquired"
            elif value == "exposed":
                if learning_data[key]["nb_exposure"] >= 5:
                    learning_data[key]["status"] = "work in progress"
                else:
                    learning_data[key]["status"] = "new"
        else:
            # Add new words
            learning_data[key] = {"nb_exposure": 1, "status": "new"}

    # Save the updated data to the file
    with open(data_file, "w", encoding="utf-8") as file:
        json.dump(learning_data, file, ensure_ascii=False, indent=4)


client = OpenAI()


def generate_update_dict(chat_history, learning_data):
    # Prepare the context for GPT-4
    context = json.dumps(learning_data)
    chat_content = "\n".join(
        [f"{msg['role']}: {msg['content']}" for msg in chat_history]
    )

    prompt = f"""
    Given the following learning data and chat history, generate a JSON update for the Estonian language learning progress.
    
    ### Learning Data:
    {context}
    
    ### Chat History:
    {chat_content}
    
    ### Instructions
    Create a JSON update with the following structure:
    1. For new words/sentences introduced in the chat: "word/sentence": "new"
    2. For words the user successfully used themselves: "word": "acquired"
    3. For words that were presented but not necessarily used by the user: "word": "exposed"
    
    Only include useful new vocabulary, grammar tips, or sentence structures helpful for begginer estonian learners. Include only estonian sentences.
    Ensure the output is in valid JSON format like the example below:
    "Tere" : "acquired",
    "Sõnad" : "new" ...
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are an AI assistant that analyzes interaction with an AI Estonian tutor. Your role is to track language learning progress.",
            },
            {"role": "user", "content": prompt},
        ],
    )

    update_json = response.choices[0].message.content

    # Parse the JSON string into a Python dictionary
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


client = OpenAI()

st.title("🤖 Kratt - Your Estonian Language Tutor")
st.caption("Learn Estonian with the help of folklore-inspired AI!")

if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])


def generate_image(prompt):
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024",
        response_format="url",
    )
    image_url = response.data[0].url
    image = Image.open(requests.get(image_url, stream=True).raw)
    return image


if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
    ] + st.session_state.messages

    response = client.chat.completions.create(model="gpt-4o", messages=messages)
    msg = response.choices[0].message.content

    # Check for image generation request
    if "<image_generation" in msg:
        start = msg.index('<image_generation prompt="') + len(
            '<image_generation prompt="'
        )
        end = msg.index('">', start)
        image_prompt = msg[start:end]
        image = generate_image(image_prompt)
        st.image(image, caption=image_prompt)
        msg = msg.replace(f'<image_generation prompt="{image_prompt}">', "")

    st.session_state.messages.append({"role": "assistant", "content": msg})
    st.chat_message("assistant").write(msg)

if st.button("Update Learning Data"):
    updates = generate_update_dict(st.session_state.messages, learning_data)
    display_and_validate_updates(updates)
