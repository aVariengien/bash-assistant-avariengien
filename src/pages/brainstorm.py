import streamlit as st
import anthropic
import json
import asyncio
from typing import List, Dict
import random
import time
import os
from openai import OpenAI, AsyncOpenAI
from birds_eye_view.core import ChunkCollection
from birds_eye_view.plotting import visualize_chunks
from streamlit.components.v1 import html
import datetime

st.set_page_config(layout="wide", page_icon="🌌")
st.title("🌌 Brainstorm")
# Initialize session state
if 'prompt_history' not in st.session_state:
    st.session_state.prompt_history = []
    st.session_state.prompt = ""

def rewrite_prompt(original_prompt: str) -> str:
    client = anthropic.Anthropic()
    system_message = """You are a prompt engineering expert. Your task is to rewrite prompts to make them clearer and more effective.
    The rewritten prompt should:
    1. Have a clear main request/question
    2. Include relevant context
    3. Have explicit evaluation criteria
    4. Be structured with clear sections
    
    Keep the original intent but make it more precise and actionable.
    
    The output should follow the format:
    'Request: [...]
    Evaluation criterion:
    1. [...]
    2. [...]
    ....'"""
    
    message = f"""Original prompt:
    {original_prompt}
    
    Please rewrite this prompt to be more effective. Include:
    - A clear context section
    - The main request/question
    - Explicit evaluation criteria (at least 3)
    
    Format the output with clear sections and bullet points where appropriate."""

    response = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=1000,
        temperature=0.7,
        system=system_message,
        messages=[
            {"role": "user", "content": message}
        ]
    )
    
    return response.content[0].text

class Agent:
    def __init__(self, personality: str, temperature: float):
        self.personality = personality
        self.client = AsyncOpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
        self.temperature = temperature

    async def generate_response(self, prompt: str, conversation_history: List[str], turn: int) -> Dict:
        personality_prompt = (
            "You are an AI agent with the following personality:\n"
            f"{self.personality}\n"
            "Based on the prompt and previous conversation, generate one **short** creative outputs "
            "that match the evaluation criteria, and **differs from the existing outputs in your context in a significant way**."
        )

        messages = [
            {"role": "system", "content": personality_prompt},
            {"role": "user", "content": f"Prompt: {prompt}\n\nConversation so far: {conversation_history}. Output a short paragraph (<100 words)."},
        ]
        
        response = await self.client.chat.completions.create(
            model="deepseek-chat",
            max_tokens=500,
            messages=messages,
            temperature=self.temperature,
        )

        try:
            output = response.choices[0].message.content
            return [
                {
                    "text": output,
                    "turn": turn,
                    "personality": self.personality
                }
            ]
        except:
            st.error("Error generating response!")
            return []

async def run_conversations(prompt: str, num_conversations: int, num_turns: int, temperature: float) -> List[Dict]:
    personalities = [
        "Agreeable Collaborator: You build upon others' ideas and try to combine the best elements.",
        "Wild Explorer: You generate completely novel and unexpected ideas that haven't been considered."
    ]
    
    all_outputs = []
    conversation_histories = [[] for _ in range(num_conversations)]

    progress_bar = st.progress(0)
    status_text = st.empty()
    visualization_placeholder = st.empty()

    for turn in range(num_turns):
        print(f"{turn} / {num_turns}")
        tasks = []
        for conv_id in range(num_conversations):
            personality = random.choice(personalities)
            agent = Agent(personality, temperature)
            task = agent.generate_response(
                prompt,
                conversation_histories[conv_id],
                turn
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        time.sleep(1)
        
        for conv_id, conv_results in enumerate(results):
            for result in conv_results:
                result["conversation_id"] = conv_id
                all_outputs.append(result)
                conversation_histories[conv_id].append(result["text"])

        progress = (turn + 1) / num_turns
        progress_bar.progress(progress)
        status_text.text(f"Processing turn {turn + 1}/{num_turns}")

    return all_outputs

def save_results(results, prompt):
    # Create folders if they don't exist
    os.makedirs("output/html", exist_ok=True)
    os.makedirs("output/json", exist_ok=True)

    # Save prompt history
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.prompt_history.append({
        "timestamp": timestamp,
        "prompt": prompt,
        "results": results
    })
    
    with open("output/json/prompt_history.json", "w") as f:
        json.dump(st.session_state.prompt_history, f, indent=2)

    # Save HTML visualization
    collection = ChunkCollection.load_from_list(results)
    collection.process_chunks()
    html_content = visualize_chunks(collection, n_connections=0, return_html=True)
    
    with open(f"output/html/visualization_{timestamp}.html", "w") as f:
        f.write(html_content)
    
    return html_content
# Modify the main() function to include the rewrite button
def main():
    # Input fields
    prompt = st.text_area("Enter your prompt:", height=200, value=st.session_state.prompt)
    

    col1, col2, col3 = st.columns(3)
    with col1:
        num_turns = st.slider("Number of turns:", 1, 15, 5)
    with col2:
        num_conversations = st.slider("Number of conversations:", 1, 300, 30)
    with col3:
        temperature = st.slider("Temperature:", 0.0, 1.0, 0.5)


    col1a, col2a = st.columns(2)
    with col1a:
        if st.button("Rewrite"):
            if prompt:
                with st.spinner("Rewriting prompt..."):
                    rewritten_prompt = rewrite_prompt(prompt)
                    st.session_state.prompt = rewritten_prompt
                    prompt = rewritten_prompt
                    print(rewritten_prompt)
                    st.rerun()
            else:
                st.warning("Please enter a prompt to rewrite.")
    
    with col2a:
        button = st.button("Generate")
    if button:
        if prompt:
            with st.spinner("Generating ..."):
                results = asyncio.run(run_conversations(
                    prompt=prompt,
                    num_conversations=num_conversations,
                    num_turns=num_turns,
                    temperature=temperature
                ))
                
                html_content = save_results(results, prompt)
                
                # Display visualization
                st.markdown("""
                    <style>
                        .block-container {
                            padding-top: 96px;
                            padding-bottom: 0rem;
                            padding-left: 40px;
                            padding-right: 20px;
                        }
                        .css-1d391kg {
                            padding-top: 0rem;
                            padding-right: 1rem;
                            padding-bottom: 0rem;
                            padding-left: 1rem;
                        }
                        iframe {
                            height: 80vh !important;
                        }
                    </style>
                    """, unsafe_allow_html=True)
                html(html_content, height=600)
        else:
            st.warning("Please enter a prompt.")



if __name__ == "__main__":
    main()