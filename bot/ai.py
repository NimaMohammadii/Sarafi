import json, requests
from .config import API_GPT, AI_TEXT_MODEL, AI_TEMPERATURE, AI_MAX_TOKENS_TEXT

HEADERS = {"Authorization": f"Bearer {API_GPT}", "Content-Type": "application/json"}

def gpt_text(system_prompt: str, user_text: str, max_tokens: int = None, temperature: float = None) -> str:
    payload = {
        "model": AI_TEXT_MODEL,
        "temperature": AI_TEMPERATURE if temperature is None else temperature,
        "max_tokens": AI_MAX_TOKENS_TEXT if max_tokens is None else max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt or
             "You are a concise assistant. Reply in Persian, bullet points, max 6 short lines."},
            {"role": "user", "content": user_text}
        ]
    }
    r = requests.post("https://api.openai.com/v1/chat/completions", headers=HEADERS, data=json.dumps(payload), timeout=30)
    r.raise_for_status()
    data = r.json()
    return (data["choices"][0]["message"]["content"] or "").strip()