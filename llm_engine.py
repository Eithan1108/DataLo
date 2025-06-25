import os
from anthropic import Anthropic
import ollama
import requests

LLM_MODE = os.getenv("LLM_MODE", "ollama")

if LLM_MODE == "anthropic":
    anthropic_client = Anthropic()
elif LLM_MODE == "huggingface":
    HF_API_KEY = os.getenv("HF_API_KEY")
    HF_MODEL = os.getenv("HF_MODEL", "mistralai/Mixtral-8x7B-Instruct-v0.1")


def send_message(messages, tools=None):
    if LLM_MODE == "anthropic":
        response = anthropic_client.messages.create(
            max_tokens=2048,
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
            tools=tools or [],
            messages=messages
        )
        return response

    elif LLM_MODE == "ollama":
        response = ollama.chat(
            model=os.getenv("OLLAMA_MODEL", "mistral"),
            messages=messages
        )
        # התאמה למבנה אחיד
        return {
            "content": [{"type": "text", "text": response['message']['content']}]
        }

    elif LLM_MODE == "huggingface":
        url = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        prompt = "\n".join([msg['content'] for msg in messages if msg['role'] == 'user'])

        data = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 2000,
                "return_full_text": False
            }
        }

        response = requests.post(url, headers=headers, json=data)
        result = response.json()

        if isinstance(result, list) and 'generated_text' in result[0]:
            return {
                "content": [{"type": "text", "text": result[0]['generated_text']}]
            }
        else:
            return {
                "content": [{"type": "text", "text": str(result)}]
            }

    else:
        raise ValueError(f"Unsupported LLM_MODE: {LLM_MODE}")
