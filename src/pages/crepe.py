import streamlit as st
from openai import OpenAI
from PIL import Image
import requests
import os
import random
import anthropic


# Streamlit App Configuration
st.set_page_config(page_title="Crêpe - Language Tutor", page_icon="🥞", initial_sidebar_state='collapsed')



try:
    if "OpenAI_key" not in st.secrets:
        open_ai_api_key = st.sidebar.text_input("Enter your OpenAI API key:")
    else:
        open_ai_api_key = st.secrets["OpenAI_key"]
except:
    if os.getenv("OPENAI_API_KEY") is None:
        open_ai_api_key = st.sidebar.text_input("Enter your OpenAI API key:")
    else:
        open_ai_api_key = os.getenv("OPENAI_API_KEY")

try:
    if "Anthropic_key" not in st.secrets:
        anthropic_api_key = st.sidebar.text_input("Enter your Anthropic API key:")
    else:
        anthropic_api_key = st.secrets["Anthropic_key"]
except:
    if os.getenv("ANTHROPIC_API_KEY") is None:
        anthropic_api_key = st.sidebar.text_input("Enter your Anthropic API key:")
    else:
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")




# Session State Initialization
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "language" not in st.session_state:
    st.session_state["language"] = "French"
if "current_topic" not in st.session_state:
    st.session_state["current_topic"] = None

# Sidebar for Language Selection
st.sidebar.title("🌍 Language Settings")
language_options = ["French", "Estonian", "Spanish", "German", "Italian"]
st.session_state["language"] = st.sidebar.selectbox(
    "Choose Language", 
    language_options
)
custom_language = st.sidebar.text_input("Or enter a custom language")
if custom_language:
    st.session_state["language"] = custom_language

# Image Generation Function
def generate_image(prompt):
    client = OpenAI(api_key=open_ai_api_key)
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024",
        response_format="url"
    )
    image_url = response.data[0].url
    image = Image.open(requests.get(image_url, stream=True).raw)
    return image

# Main Streamlit App
st.title(f"🥞 Crêpe - Your Language Tutor")

# System Prompt for Language Tutor
system_prompt = f"""
You are Crêpe, a friendly AI language tutor specializing in {st.session_state['language']}. 
Your goal is to make language learning engaging, interactive, and fun.

Key Principles:
1. Start by proposing a few choice for lessons, or if the user simply want a chat. Keep it brief, your first message should be a single sentence.
2. Start lessons with a brief grammar or vocabulary explanation
3. Use image-based exercises to make learning more interactive. 
4. Use as much as the language as possible, but keep the sentence short, and the word simple
5. Use images to create engaging situation to ground exercises. To generate an image, use the tag '<image_generation prompt="a detailed description of the image">' **at the end** of your message. An AI image generator will replace the tag with a synthetic image. When writting image description, you can be creative and playful.

To create a lesson:
- Choose a specific topic or grammar point
- Explain the concept briefly
- Create an image-based exercise. During the exercise only use {st.session_state['language']}, and resort to English only if asked by the user, or if the user is lost.
- Don't give away the answer during the exercise, ask a question in {st.session_state['language']} about a situation depicted in the image. Generate the image at the end of your message.
- Ask a question such that the user _has_ to use the newly learned structure / words.
- Provide encouraging feedback

If the user wants to chat, create playful scenarios using images.
"""

# Render Previous Messages
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Chat Input and Processing
anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)

if prompt := st.chat_input("Ask me anything or start a lesson!"):
    # User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)


    messages = st.session_state.messages

    messages = st.session_state.messages

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        with anthropic_client.messages.stream(
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
        with st.spinner("🏞️ Generating image ..."):
            image = generate_image(image_prompt)
        st.image(image)
        display_message = full_response.replace(
            f'<image_generation prompt="{image_prompt}">', ""
        )
    else:
        display_message = full_response

    message_placeholder.markdown(display_message)
    st.session_state.messages.append({"role": "assistant", "content": full_response})
