import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters

from .ai import gpt_text
from .config import AI_BRAND_LABEL, GPT_DAILY_LIMIT_FREE, GPT_DAILY_LIMIT_PRO
from .guard import require_membership
from .db import get_user, ensure_user, has_active_sub, get_gpt_daily_count, increment_gpt_daily

log = logging.getLogger(__name__)

CB_MAIN           = "main"
CB_LEARN          = "learn"
CB_LEARN_GLOSS    = "learn_gloss"
CB_LEARN_JOURNAL  = "learn_journal"
CB_LEARN_PATTERN  = "learn_pattern"
CB_LEARN_CHALL    = "learn_chall"

def _back_main_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("↩️ بازگشت", callback_data=CB_MAIN)]])

def _learn_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("آکادمی ترید 🎓", callback_data=CB_LEARN_GLOSS),
         InlineKeyboardButton("ژورنال هوشمند Pro 📝", callback_data=CB_LEARN_JOURNAL)],
        [InlineKeyboardButton("مربی الگوهای قیمت 🤖", callback_data=CB_LEARN_PATTERN),
         InlineKeyboardButton("چالش روزانه بازار 🔥", callback_data=CB_LEARN_CHALL)],
        [InlineKeyboardButton("↩️ بازگشت", callback_data=CB_MAIN)]
    ])

async def learn_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_membership(update, context): return
    q = update.callback_query; await q.answer()
    txt = ("<b>آموزش‌ها 🎓</b>\n"
           "بخش‌های تعاملی با <b>هوش مصنوعی کم‌مصرف</b> ارائه می‌شوند.\n"
           f"<i>{AI_BRAND_LABEL}</i>")
    await q.message.edit_text(txt, parse_mode="HTML", reply_markup=_learn_kb())

# ---- Glossary (static)
_GLOSS = {
    "پرایس‌اکشن": "حرکت قیمت بدون اندیکاتور. تمرکز بر ساختار بازار، HH/HL/LH/LL.",
    "حمایت/مقاومت": "ناحیه‌هایی که قیمت احتمالاً واکنش می‌دهد. شکست معتبر = پولبک + حجم.",
    "واگرایی RSI": "قیمت سقف/کف جدید می‌سازد اما RSI تأیید نمی‌کند ⇒ ضعف روند.",
    "ریسک به ریوارد": "نسبت سود هدف به ضرر احتمالی. حداقل 1:2 توصیه می‌شود."
}

def _gloss_kb():
    rows, pair = [], []
    for k in _GLOSS.keys():
        pair.append(InlineKeyboardButton(k, callback_data=f"{CB_LEARN_GLOSS}:{k}"))
        if len(pair) == 2: rows.append(pair); pair = []
    if pair: rows.append(pair)
    rows.append([InlineKeyboardButton("↩️ بازگشت", callback_data=CB_LEARN)])
    return InlineKeyboardMarkup(rows)

async def learn_gloss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_membership(update, context): return
    q = update.callback_query; await q.answer()
    if ":" in q.data:
        term = q.data.split(":",1)[1]
        await q.message.edit_text(f"<b>{term}</b>\n{_GLOSS.get(term,'')}", parse_mode="HTML", reply_markup=_gloss_kb())
    else:
        await q.message.edit_text("<b>آکادمی ترید 🎓</b>\nیک مورد را انتخاب کن:", parse_mode="HTML", reply_markup=_gloss_kb())

# ---- Journal (low-cost GPT + daily limit)
async def learn_journal_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_membership(update, context): return
    q = update.callback_query; await q.answer()
    context.user_data["JOURNAL_WAIT"] = True
    await q.message.edit_text(
        "<b>ژورنال هوشمند Pro 📝</b>\n"
        "خلاصه ترید/تحلیل‌ت را در ۵–۶ خط بفرست (ورود/استاپ/دلایل/احساسات).\n"
        "یک فیدبک کوتاه و عملی می‌گیری.\n"
        f"<i>{AI_BRAND_LABEL}</i>",
        parse_mode="HTML", reply_markup=_back_main_kb()
    )

async def journal_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("JOURNAL_WAIT"): return
    context.user_data["JOURNAL_WAIT"] = False

    uid = update.effective_user.id
    u = get_user(uid) or ensure_user(uid, update.effective_user.username or "", update.effective_user.full_name or "")

    # daily limit for GPT text
    limit = GPT_DAILY_LIMIT_PRO if has_active_sub(u) else GPT_DAILY_LIMIT_FREE
    used  = get_gpt_daily_count(u)
    if used >= limit:
        await update.message.reply_text(
            f"⛔️ سقف استفاده روزانه از GPT رسید: <b>{used}/{limit}</b>\n"
            "برای ادامه امروز اشتراک بگیر یا فردا (بعد از ۰۰:۰۰) امتحان کن.",
            parse_mode="HTML", reply_markup=_back_main_kb()
        )
        return

    waiting = await update.message.reply_text("در حال ارزیابی... ⏳", parse_mode="HTML")
    try:
        sys = ("You are a trading coach. Reply in Persian. "
               "Be ultra-concise: max 6 short bullet points. "
               "Cover strengths, risks, 1 concrete improvement, position sizing tip, mantra.")
        out = gpt_text(sys, update.message.text, max_tokens=140)  # حتی کم‌تر از پیش‌فرض
        increment_gpt_daily(uid)
        await waiting.edit_text(out + f"\n\n<i>{AI_BRAND_LABEL}</i>", parse_mode="HTML", reply_markup=_back_main_kb())
    except Exception:
        await waiting.edit_text("⚠️ خطا در ارزیابی. دوباره تلاش کن.", parse_mode="HTML", reply_markup=_back_main_kb())

# ---- Pattern coach (prompt-only; تحلیل تصویر با هندلر اصلی عکس انجام می‌شود)
async def learn_pattern(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_membership(update, context): return
    q = update.callback_query; await q.answer()
    await q.message.edit_text(
        "<b>مربی الگوهای قیمت 🤖</b>\n"
        "یک تصویر چارت واضح بفرست تا الگوهای احتمالی و نکات کلیدی گفته شود.\n"
        f"<i>{AI_BRAND_LABEL}</i>",
        parse_mode="HTML", reply_markup=_back_main_kb()
    )

# ---- Daily challenge (static)
async def learn_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_membership(update, context): return
    q = update.callback_query; await q.answer()
    txt = ("<b>چالش روزانه بازار 🔥</b>\n"
           "سناریو: شکست مقاومت با حجم متوسط؛ RSI=62؛ پولبک ضعیف به ناحیه شکسته.\n"
           "گزینه بهتر؟\nA) لانگ با استاپ نزدیک 1R\nB) صبر برای کندل تاییدی\nC) عدم ورود (پراکندگی سیگنال)\n\n"
           "پیشنهاد آموزشی: B، چون تایید پولبک/تداوم اهمیت دارد.")
    await q.message.edit_text(txt, parse_mode="HTML", reply_markup=_back_main_kb())

def register_learn_handlers(app):
    app.add_handler(CallbackQueryHandler(learn_menu,            pattern=f"^{CB_LEARN}$"))
    app.add_handler(CallbackQueryHandler(learn_gloss,           pattern=f"^{CB_LEARN_GLOSS}.*"))
    app.add_handler(CallbackQueryHandler(learn_journal_start,   pattern=f"^{CB_LEARN_JOURNAL}$"))
    app.add_handler(CallbackQueryHandler(learn_pattern,         pattern=f"^{CB_LEARN_PATTERN}$"))
    app.add_handler(CallbackQueryHandler(learn_challenge,       pattern=f"^{CB_LEARN_CHALL}$"))
    # ژورنال باید قبل از روتِرهای متنی دیگر ثبت شود
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, journal_router))