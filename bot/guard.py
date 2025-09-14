# چک عضویت اجباری (تلگرام واقعی + اینستا فرضیِ تأیید دستی)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus
from .config import CHANNEL_ID, CHANNEL_URL, INSTA_ID

CB_JOIN_CHECK = "join_check"  # همین را در handlers.py برای Callback ثبت کن

def _is_member_status(status) -> bool:
    valid = {
        getattr(ChatMemberStatus, "MEMBER", "member"),
        getattr(ChatMemberStatus, "ADMINISTRATOR", "administrator"),
        getattr(ChatMemberStatus, "OWNER", getattr(ChatMemberStatus, "CREATOR", "creator")),
    }
    return str(status).lower() in {str(v).lower() for v in valid}

async def _get_invite_link(context: ContextTypes.DEFAULT_TYPE) -> str:
    if CHANNEL_URL:
        return CHANNEL_URL
    try:
        link = await context.bot.create_chat_invite_link(chat_id=CHANNEL_ID)
        return link.invite_link
    except Exception:
        return f"https://t.me/{str(CHANNEL_ID).lstrip('@')}"

def _join_kb(invite_url: str):
    rows = []
    if CHANNEL_ID:
        rows.append([InlineKeyboardButton("🚀 ورود به کانال تلگرام", url=invite_url)])
    if INSTA_ID:
        rows.append([InlineKeyboardButton("📷 رفتن به اینستاگرام", url=INSTA_ID)])
    rows.append([InlineKeyboardButton("✅ بررسی عضویت", callback_data=CB_JOIN_CHECK)])
    return InlineKeyboardMarkup(rows)

async def require_membership(update, context) -> bool:
    # اگر یکی تنظیم نشده باشد، گیت را نادیده می‌گیریم
    if not CHANNEL_ID or not INSTA_ID:
        return True

    uid = update.effective_user.id if update.effective_user else 0

    # چک تلگرام (واقعی)
    ok_tg = False
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=uid)
        ok_tg = _is_member_status(member.status)
    except Exception:
        ok_tg = False

    # چک اینستا (فرضی—بعد از کلیک «بررسی عضویت» ذخیره می‌کنیم)
    ok_insta = context.user_data.get("ok_insta", False)

    if ok_tg and ok_insta:
        return True

    invite = await _get_invite_link(context)
    txt = (
        "<b>🎯 عضویت اجباری</b>\n"
        "برای ادامه باید در هر دو عضو باشی:\n"
        "1️⃣ کانال تلگرام\n2️⃣ پیج اینستاگرام\n"
        "بعد روی «✅ بررسی عضویت» بزن."
    )
    if update.callback_query:
        await update.callback_query.message.edit_text(txt, parse_mode="HTML", reply_markup=_join_kb(invite))
    else:
        await update.effective_message.reply_text(txt, parse_mode="HTML", reply_markup=_join_kb(invite))
    return False