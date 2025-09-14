import os

# --- required secrets ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_GPT   = os.getenv("API_GPT")
if not BOT_TOKEN: raise RuntimeError("BOT_TOKEN در Secrets تنظیم نشده است.")
if not API_GPT:   raise RuntimeError("API_GPT در Secrets تنظیم نشده است.")

# --- model settings ---
MODEL_VISION = os.getenv("MODEL_VISION", "gpt-4o-mini")
TEMPERATURE  = float(os.getenv("TEMPERATURE", "0.2"))
MAX_TOKENS   = int(os.getenv("MAX_TOKENS", "500"))

# --- AI (low-cost) ---
AI_TEXT_MODEL       = os.getenv("AI_TEXT_MODEL", "gpt-4o-mini")
AI_VISION_MODEL     = os.getenv("AI_VISION_MODEL", MODEL_VISION)
AI_TEMPERATURE      = float(os.getenv("AI_TEMPERATURE", "0.2"))
AI_MAX_TOKENS_TEXT  = int(os.getenv("AI_MAX_TOKENS_TEXT", "160"))
AI_BRAND_LABEL      = os.getenv("AI_BRAND_LABEL", "🤖 Powered by GPT (بهینه)")

# --- forced membership (Telegram channel username only) ---
CHANNEL_ID  = os.getenv("CHANNEL_ID", "")  # مانند: @yourchannel
CHANNEL_URL = os.getenv("CHANNEL_URL", f"https://t.me/{CHANNEL_ID.lstrip('@')}") if CHANNEL_ID else ""

# --- Instagram page link (forced combo) ---
INSTA_ID = os.getenv("INSTA_ID", "")       # مانند: https://instagram.com/yourpage

# --- daily limits ---
DAILY_FREE_LIMIT       = int(os.getenv("DAILY_FREE_LIMIT", "8"))  # تحلیل تصویر برای کاربر عادی
GPT_DAILY_LIMIT_FREE   = int(os.getenv("GPT_DAILY_LIMIT_FREE", "5"))
GPT_DAILY_LIMIT_PRO    = int(os.getenv("GPT_DAILY_LIMIT_PRO", "15"))

# --- admin ---
BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID", "0") or 0)