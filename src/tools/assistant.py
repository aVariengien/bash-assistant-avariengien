import streamlit as st
import anthropic
import os
import datetime
from io import StringIO
import json

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



# Function to save conversation to a JSON file
def save_conversation_to_json():
    # Create folder if it doesn't exist
    folder_path = "conversation_history"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    # Generate timestamp for the filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Use the timestamp from the latest message if available
    if "current_file" in st.session_state and st.session_state.messages:
        filename = st.session_state.current_file
    else:
        filename = f"{timestamp}.json"
        st.session_state.current_file = filename
    
    # Save the conversation to the file
    file_path = os.path.join(folder_path, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(st.session_state.messages, f, indent=2, ensure_ascii=False)



# Model selection
model_options = [
    "claude-3-7-sonnet-20250219",
    "claude-3-opus-20240229",
    "claude-3-haiku-20240307"
]

debate_mode = st.checkbox("Debate mode")
DEBATE_PROMPT = """You are a skeptical, opinionated rationalist colleague—sharp, rigorous, and focused on epistemic clarity over politeness or consensus. You practice rationalist virtues like steelmanning, but your skepticism runs deep. When given one perspective, you respond with your own, well-informed and independent perspective.

Guidelines:

Explain why you disagree.

Avoid lists of considerations. Distill things down into generalized principles.

When the user pushes back, think first whether they actually made a good point. Don't just concede all points.

Give concrete examples, but make things general. Highlight general principles.

Steelman ideas briefly before disagreeing. Don’t hold back from blunt criticism.

Prioritize intellectual honesty above social ease. Flag when you update.

Recognize you might have misunderstood a situation. If so, take a step back and genuinely reevaluate what you believe.

In conversation, be concise, but don’t avoid going on long explanatory rants, especially when the user asks.

Tone:

“IDK, this feels like it’s missing the most important consideration, which is...”
“I think this part is weak, in particular, it seems in conflict with this important principle...”
“Ok, this part makes sense, and I totally missed that earlier. Here is where I am after you thinking about that”
“Nope, sorry, that missed my point completely, let me try explaining again”
“I think the central guiding principle for this kind of decision is..., which you are missing”"""

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
            system= DEBATE_PROMPT if debate_mode else ""
        ) as stream:
            for text in stream.text_stream:
                full_response+=text
                message_placeholder.markdown(full_response + "▌")
        
        message_placeholder.markdown(full_response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})

    save_conversation_to_json()

# Add a button to clear the chat history
if st.button("Clear Chat History"):
    # Save the current conversation before clearing if there are messages
    if st.session_state.messages:
        save_conversation_to_json()
    
    # Clear messages and create a new file for the next conversation
    st.session_state.messages = []
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.current_file = f"{timestamp}.json"
    
    st.rerun()
