import asyncio
import aiohttp
from openai import AsyncOpenAI
from streamlit import session_state as ss
import streamlit as st
from os import getenv
st.set_page_config(layout='wide')

MODEL_OPTIONS = ['gpt-3.5-turbo-0125', 'gpt-3.5-turbo-16k-0613', 'gpt-4-turbo', 'gpt-4-0613']

if 'msg' not in ss:
    ss.msg = {'chat1': [], 'chat2': [], 'chat3': [], 'chat4': []}
if 'is_good_input' not in ss:
    ss.is_good_input = False
if 'first_messages' not in ss:
    ss.first_messages = [''] * 4
if 'oaik' not in ss:
    ss.oaik = getenv("OPEN_AI_KEY")

def submit_cb():
    ss.is_good_input = False
    if not ss.oaik:
        st.sidebar.warning('openai api key is missing')
    else:
        ss.is_good_input = True

def submit_system_prompt():
    ss.trigger_first_messages = True
    ss.msg = {'chat1': [], 'chat2': [], 'chat3': [], 'chat4': []}

async def stream_chat(client, model, messages, max_tokens, temperature):
    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True
    )
    response = ""
    async for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            response += chunk.choices[0].delta.content
            yield response

async def process_stream(stream, placeholder):
    async for response in stream:
        placeholder.markdown(response)
    return response

async def main():
    # Get option values.
    with st.sidebar:
        with st.form('form'):
            #st.text_input('enter openai api key', type='password', key='oaik')
            st.selectbox('select model name', MODEL_OPTIONS, index=0, key='model')
            st.slider('max tokens', value=200, min_value=16, max_value=2000, step=16, key='maxtoken')
            st.slider('temperature', value=0.5, min_value=0.0, max_value=2.0, step=0.1, key='temperature')
            st.form_submit_button('Submit', on_click=submit_cb)

    # if not ss.is_good_input:
    #     st.stop()

    model = ss.model
    max_tokens = ss.maxtoken
    temperature = ss.temperature

    st.title(f"Prompt Tester !")

    with st.form('system_prompt'):
        st.text_input('System prompt', type='default', key='system_prompt', value="Anwser with emoji only.")
        st.form_submit_button('Update', on_click=submit_system_prompt)

    col1, col2, col3, col4 = st.columns(4, gap='large')
    columns = [col1, col2, col3, col4]

    for i, col in enumerate(columns):
        with col:
            st.text_area(f"First message for Chat {i+1}", key=f"first_message_{i}", value="hi!")
            ss.first_messages[i] = ss[f"first_message_{i}"]

    async with AsyncOpenAI(api_key=ss.oaik) as client:
        for i, col in enumerate(columns, 1):
            with col:
                st.write(f'Chat {i}')
                for message in ss.msg[f'chat{i}']:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])

        if 'trigger_first_messages' in ss and ss.trigger_first_messages:
            placeholders = []
            for i, (col, first_message) in enumerate(zip(columns, ss.first_messages), 1):
                if first_message:
                    ss.msg[f'chat{i}'].append({"role": "user", "content": first_message})
                    with col:
                        with st.chat_message("user"):
                            st.markdown(first_message)
                        with st.chat_message("assistant"):
                            placeholders.append(st.empty())
                else:
                    placeholders.append(None)

            tasks = []
            for i, placeholder in enumerate(placeholders, 1):
                if placeholder:
                    messages = [{"role": "system", "content": ss.system_prompt}] + [{"role": m["role"], "content": m["content"]} for m in ss.msg[f'chat{i}']]
                    stream = stream_chat(client, model, messages, max_tokens, temperature)
                    task = asyncio.create_task(process_stream(stream, placeholder))
                    tasks.append(task)
                else:
                    tasks.append(None)

            responses = await asyncio.gather(*[t for t in tasks if t])

            for i, (task, response) in enumerate(zip(tasks, responses + [None] * (4 - len(responses))), 1):
                if task:
                    ss.msg[f'chat{i}'].append({"role": "assistant", "content": response})

            ss.trigger_first_messages = False

        for i, col in enumerate(columns, 1):
            with col:
                # st.write(f'Chat {i}')
                # for message in ss.msg[f'chat{i}']:
                #     with st.chat_message(message["role"]):
                #         st.markdown(message["content"])

                prompt = st.chat_input(f"Chat {i}")

                if prompt:
                    ss.msg[f'chat{i}'].append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.markdown(prompt)

                    with st.chat_message("assistant"):
                        placeholder = st.empty()
                        messages = [{"role": "system", "content": ss.system_prompt}] + ss.msg[f'chat{i}']
                        stream = stream_chat(client, model, messages, max_tokens, temperature)
                        response = await process_stream(stream, placeholder)
                        ss.msg[f'chat{i}'].append({"role": "assistant", "content": response})

        # prompts = []
        # for i, col in enumerate(columns, 1):
        #     with col:
        #         prompt = st.text_input(f"Enter prompt for Chat {i}", key=f"prompt_{i}")
        #         prompts.append(prompt)

        # if any(prompts):
        #     placeholders = []
        #     for i, (col, prompt) in enumerate(zip(columns, prompts), 1):
        #         if prompt:
        #             ss.msg[f'chat{i}'].append({"role": "user", "content": prompt})
        #             with col:
        #                 with st.chat_message("user"):
        #                     st.markdown(prompt)
        #                 with st.chat_message("assistant"):
        #                     placeholders.append(st.empty())
        #         else:
        #             placeholders.append(None)

        #     tasks = []
        #     for i, placeholder in enumerate(placeholders, 1):
        #         if placeholder:
        #             messages = [{"role": "system", "content": ss.system_prompt}] + [{"role": m["role"], "content": m["content"]} for m in ss.msg[f'chat{i}']]
        #             stream = stream_chat(client, model, messages, max_tokens, temperature)
        #             task = asyncio.create_task(process_stream(stream, placeholder))
        #             tasks.append(task)
        #         else:
        #             tasks.append(None)

        #     responses = await asyncio.gather(*[t for t in tasks if t])

        #     for i, (task, response) in enumerate(zip(tasks, responses + [None] * (4 - len(responses))), 1):
        #         if task:
        #             ss.msg[f'chat{i}'].append({"role": "assistant", "content": response})

if __name__ == '__main__':
    asyncio.run(main())