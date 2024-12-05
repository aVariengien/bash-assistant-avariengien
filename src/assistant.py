import streamlit as st
import anthropic
import os
from io import StringIO

# Set up the Streamlit page
st.set_page_config(page_title="Assistant", page_icon="🤖")
st.title("🤖 Claude Chatbot")

# Get the Anthropic API key from environment variable
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

if not anthropic_api_key:
    st.error("Please set the ANTHROPIC_API_KEY environment variable.")
    st.stop()

# Initialize the Anthropic client
client = anthropic.Anthropic()

# Model selection
model_options = [
    "claude-3-5-sonnet-20240620",
    "claude-3-opus-20240229",
    "claude-3-haiku-20240307"
]
selected_model = st.selectbox("Choose a model:", model_options)

# Token slider
max_tokens = st.slider("Max tokens to generate:", min_value=100, max_value=8192, value=1000, step=100)

# File uploader
uploaded_file = st.file_uploader("Upload a file (optional)", type=["txt", "pdf", "docx"])

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("What would you like to ask?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare the messages for the API call
    messages = []
    
    # Add file content to messages if a file was uploaded
    if uploaded_file:
        file_content = uploaded_file.getvalue().decode("utf-8")
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Here's the content of the uploaded file:\n\n{file_content}"
                }
            ]
        })
    
    # Add chat history and current prompt to messages
    for message in st.session_state.messages:
        messages.append({
            "role": message["role"],
            "content": [
                {
                    "type": "text",
                    "text": message["content"]
                }
            ]
        })

    # Generate response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        with client.messages.stream(
            model=selected_model, #type: ignore
            max_tokens=max_tokens,
            messages=messages, #type: ignore
        ) as stream:
            for text in stream.text_stream:
                full_response+=text
                message_placeholder.markdown(full_response + "▌")
        
        message_placeholder.markdown(full_response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# Add a button to clear the chat history
if st.button("Clear Chat History"):
    st.session_state.messages = []
    st.rerun()
