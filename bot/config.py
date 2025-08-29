import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_GPT   = os.getenv("API_GPT")
BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID", "0") or 0)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN در Secrets تنظیم نشده است.")
if not API_GPT:
    raise RuntimeError("API_GPT در Secrets تنظیم نشده است.")

MODEL_VISION = os.getenv("MODEL_VISION", "gpt-4o-mini")
TEMPERATURE  = float(os.getenv("TEMPERATURE", "0.2"))
MAX_TOKENS   = int(os.getenv("MAX_TOKENS", "500"))