import logging
import requests
import json

from .config import API_GPT, MODEL_VISION, TEMPERATURE, MAX_TOKENS
from .prompts import SYSTEM_PROMPT
from .utils import image_bytes_to_data_url, strip_code_fences, safe_load_json

log = logging.getLogger(__name__)

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_GPT}",
    "Content-Type": "application/json",
}

def analyze_chart(image_bytes: bytes) -> dict:
    data_url = image_bytes_to_data_url(image_bytes)

    payload = {
        "model": MODEL_VISION,          # مثل gpt-4o-mini یا gpt-4o
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        # 👇 اجبار به JSON تا خروجی تمیز باشه
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                # فرمت صحیح برای chat/completions
                {"type": "text", "text": "Analyze this chart image and return ONLY the JSON."},
                {"type": "image_url", "image_url": {"url": data_url}}
            ]}
        ],
    }

    try:
        resp = requests.post(OPENAI_CHAT_URL, headers=HEADERS, data=json.dumps(payload), timeout=90)
        if resp.status_code != 200:
            log.error("OpenAI HTTP %s: %s", resp.status_code, resp.text)
            return {
                "bias": "NO_TRADE",
                "confidence_percent": 0,
                "rationale": f"خطا در تماس با سرویس: {resp.status_code}",
                "levels": {},
                "notes": "کمی بعد دوباره تلاش کنید."
            }

        data = resp.json()
        content = (data["choices"][0]["message"]["content"] or "").strip()

        # چون response_format=json_object دادیم، باید JSON خالص باشد؛
        # ولی برای اطمینان باز هم پاک‌سازی می‌کنیم:
        cleaned = strip_code_fences(content)

        try:
            return safe_load_json(cleaned)
        except Exception:
            log.exception("JSON parse failed. Raw content: %s", content)
            return {
                "bias": "NO_TRADE",
                "confidence_percent": 0,
                "rationale": "عدم امکان استخراج JSON معتبر از پاسخ مدل.",
                "levels": {},
                "notes": "تصویر یا پاسخ مدل نامعتبر بود. دوباره با چارت واضح‌تر امتحان کنید."
            }

    except requests.RequestException as e:
        log.exception("HTTP error calling OpenAI: %s", e)
        return {
            "bias": "NO_TRADE",
            "confidence_percent": 0,
            "rationale": "ارتباط شبکه‌ای با سرویس برقرار نشد.",
            "levels": {},
            "notes": "VPN/اینترنت را چک کنید و دوباره تلاش کنید."
        }