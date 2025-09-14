import io, logging, datetime, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, PreCheckoutQueryHandler, filters
)

from .config import (
    BOT_TOKEN, MODEL_VISION, BOT_OWNER_ID,
    CHANNEL_ID, CHANNEL_URL, DAILY_FREE_LIMIT, AI_BRAND_LABEL,
    GPT_DAILY_LIMIT_FREE, GPT_DAILY_LIMIT_PRO
)
from .prompts import HELP_TEXT
from .analyze import analyze_chart
from .formatting import format_reply
from .db import (
    ensure_user, get_user, update_user,
    increment_analysis, count_users, count_active_subs, last_payments,
    set_subscription_days, all_user_ids, add_payment_record,
    has_active_sub, get_daily_count, increment_daily_analysis,
    get_gpt_daily_count
)
from .handlers_learn import register_learn_handlers
from .guard import require_membership as _require_membership, CB_JOIN_CHECK

log = logging.getLogger(__name__)

CB_MAIN = "main"
CB_ANALYZE = "analyze"
CB_SUBS = "subs"
CB_SUBS_PAY = "subs_pay"
CB_PROFILE = "profile"
CB_SETTINGS = "settings"
CB_SETTINGS_CONF_UP = "settings_conf_up"
CB_SETTINGS_CONF_DOWN = "settings_conf_down"
CB_SETTINGS_RISK = "settings_risk"
CB_SETTINGS_LANG = "settings_lang"
CB_LEARN = "learn"

CB_ADMIN = "admin"
CB_ADMIN_STATS = "admin_stats"
CB_ADMIN_GRANT = "admin_grant"
CB_ADMIN_BCAST = "admin_bcast"

ADMIN_USERNAME = "AdminOfChannel"
STARS_PRICE = 399

def _fmt_ts(ts):
    if not ts: return "-"
    dt = datetime.datetime.fromtimestamp(ts)
    return dt.strftime("%Y-%m-%d %H:%M")

def _is_owner(update: Update) -> bool:
    uid = (update.effective_user.id if update.effective_user else 0)
    return BOT_OWNER_ID and uid == BOT_OWNER_ID

def menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("تحلیل چارت 📈", callback_data=CB_ANALYZE),
         InlineKeyboardButton("خرید اشتراک 🛒", callback_data=CB_SUBS)],
        [InlineKeyboardButton("پروفایل 👤", callback_data=CB_PROFILE),
         InlineKeyboardButton("تنظیمات ⚙️", callback_data=CB_SETTINGS)],
        [InlineKeyboardButton("آموزش‌ها 🎓", callback_data=CB_LEARN)],
    ])

def back_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("↩️ بازگشت به منو", callback_data=CB_MAIN)]])

def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 آمار", callback_data=CB_ADMIN_STATS)],
        [InlineKeyboardButton("🎁 فعالسازی اشتراک دستی", callback_data=CB_ADMIN_GRANT)],
        [InlineKeyboardButton("📣 برودکست", callback_data=CB_ADMIN_BCAST)],
        [InlineKeyboardButton("↩️ بازگشت به منو", callback_data=CB_MAIN)]
    ])

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="HTML")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_membership(update, context): return
    user = update.effective_user
    ensure_user(user.id, user.username or "", (user.full_name or ""))
    text = ("<b>به بات تحلیل چارت خوش آمدی!</b>\n\n"
            f"<b>مدل: GPT-5 🫧</b>\n\n"
            "<b>از منوی زیر انتخاب کن:</b>")
    await update.message.reply_text(text, reply_markup=menu_kb(), parse_mode="HTML")

async def join_check_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["ok_insta"] = True
    if await _require_membership(update, context):
        await q.message.edit_text("<b>✅ عضویت تایید شد</b>\nاز منوی زیر انتخاب کن:",
                                  parse_mode="HTML", reply_markup=menu_kb())

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_membership(update, context): return
    q = update.callback_query; await q.answer()
    await q.message.edit_text(
        "<b>منوی اصلی</b>\n👇 یکی را انتخاب کن:",
        reply_markup=menu_kb(), parse_mode="HTML"
    )

async def analyze_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_membership(update, context): return
    q = update.callback_query; await q.answer()
    await q.message.edit_text(
        "<b>تحلیل چارت 📈</b>\nیک <b>عکس واضح</b> از چارت بفرست.",
        reply_markup=back_kb(), parse_mode="HTML"
    )

async def subs_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_membership(update, context): return
    q = update.callback_query; await q.answer()
    text = (f"<b>خرید اشتراک 🛒</b>\n• <b>۱ ماهه</b> = <b>{STARS_PRICE} ⭐️ Stars</b>\n\n")
    k = InlineKeyboardMarkup([
        [InlineKeyboardButton("پرداخت با ⭐️ استارز", callback_data=CB_SUBS_PAY)],
        [InlineKeyboardButton("↩️ بازگشت به منو", callback_data=CB_MAIN)]
    ])
    await q.message.edit_text(text, reply_markup=k, parse_mode="HTML")

async def subs_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_membership(update, context): return
    q = update.callback_query; await q.answer()
    chat_id = q.from_user.id
    await context.bot.send_invoice(
        chat_id=chat_id, title="اشتراک ماهانه",
        description="دسترسی به تحلیل چارت به مدت ۳۰ روز",
        payload=f"sub_month_{chat_id}",
        provider_token="", currency="XTR",
        prices=[LabeledPrice("اشتراک 1 ماهه", STARS_PRICE)],
    )

async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id; now = int(time.time())
    update_user(uid, {"subscription": {"active": True,"plan": "monthly","start_ts": now,"end_ts": now + 30*24*3600,"via": "stars"}})
    try: add_payment_record(uid, STARS_PRICE, update.message.successful_payment.invoice_payload)
    except Exception: log.exception("failed to store payment record")
    await update.message.reply_text("<b>پرداخت موفق ✅</b>\nاشتراک شما ۳۰ روز فعال شد.", parse_mode="HTML", reply_markup=menu_kb())

async def profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_membership(update, context): return
    q = update.callback_query; await q.answer()
    u = get_user(q.from_user.id)
    sub, stats = u["subscription"], u["stats"]
    gpt_limit = GPT_DAILY_LIMIT_PRO if has_active_sub(u) else GPT_DAILY_LIMIT_FREE
    gpt_used  = get_gpt_daily_count(u)
    txt = (
        "<b>پروفایل 👤</b>\n"
        f"• <b>آیدی:</b> <code>{u['user_id']}</code>\n"
        f"• <b>نام:</b> {u.get('name') or '-'} | @{u.get('username') or '-'}\n"
        f"• <b>عضویت از:</b> { _fmt_ts(u['created_at']) }\n\n"
        f"• <b>اشتراک فعال:</b> {'✅' if sub['active'] else '❌'} | <b>پلن:</b> {sub['plan'] or '-'}\n"
        f"• <b>پایان:</b> { _fmt_ts(sub['end_ts']) }\n\n"
        f"• <b>تحلیل‌های امروز (تصویر):</b> {get_daily_count(u)}\n"
        f"• <b>سؤالات GPT امروز (متن):</b> {gpt_used} / {gpt_limit}\n"
    )
    await q.message.edit_text(txt, parse_mode="HTML", reply_markup=back_kb())

def _settings_kb(u):
    s = u["settings"]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"آستانه اعتماد: {s['min_confidence']}٪ ➖", callback_data=CB_SETTINGS_CONF_DOWN),
         InlineKeyboardButton("➕", callback_data=CB_SETTINGS_CONF_UP)],
        [InlineKeyboardButton(f"حالت ریسک: {s['risk_mode']}", callback_data=CB_SETTINGS_RISK)],
        [InlineKeyboardButton(f"زبان خروجی: {s['lang']}", callback_data=CB_SETTINGS_LANG)],
        [InlineKeyboardButton("↩️ بازگشت به منو", callback_data=CB_MAIN)],
    ])

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_membership(update, context): return
    q = update.callback_query; await q.answer()
    u = get_user(q.from_user.id)
    await q.message.edit_text(
        "<b>تنظیمات ⚙️</b>\n• آستانه اعتماد\n• حالت ریسک\n• زبان خروجی",
        parse_mode="HTML", reply_markup=_settings_kb(u)
    )

async def settings_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_membership(update, context): return
    q = update.callback_query; uid = q.from_user.id
    u = get_user(uid); data = q.data
    if data == CB_SETTINGS_CONF_UP:   val = min(95, u["settings"]["min_confidence"] + 5)
    elif data == CB_SETTINGS_CONF_DOWN: val = max(0,  u["settings"]["min_confidence"] - 5)
    else: val = None
    if val is not None: update_user(uid, {"settings": {"min_confidence": val}})
    elif data == CB_SETTINGS_RISK:
        order = ["conservative","balanced","aggressive"]; cur = u["settings"]["risk_mode"]
        update_user(uid, {"settings": {"risk_mode": order[(order.index(cur)+1)%len(order)]}})
    elif data == CB_SETTINGS_LANG:
        update_user(uid, {"settings": {"lang": "en" if u["settings"]["lang"]=="fa" else "fa"}})
    await q.answer("به‌روز شد ✅")
    await q.message.edit_text("<b>تنظیمات ⚙️</b>\nبه‌روزرسانی انجام شد.", parse_mode="HTML", reply_markup=_settings_kb(get_user(uid)))

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_membership(update, context): return
    waiting = await update.message.reply_text("<b>در حال تحلیل تصویر...</b> 🧐", parse_mode="HTML")
    try:
        u = ensure_user(update.effective_user.id, update.effective_user.username or "", update.effective_user.full_name or "")
        if not has_active_sub(u) and get_daily_count(u) >= DAILY_FREE_LIMIT:
            await waiting.edit_text(f"⛔️ سقف تحلیل روزانه پر شد ({DAILY_FREE_LIMIT}).\nاشتراک بگیر یا فردا امتحان کن.",
                                    parse_mode="HTML", reply_markup=menu_kb()); return
        photo = update.message.photo[-1]; file = await photo.get_file()
        buf = io.BytesIO(); await file.download_to_memory(out=buf)
        result = analyze_chart(buf.getvalue()); conf = int(result.get("confidence_percent") or 0)
        increment_analysis(update.effective_user.id, conf=conf)
        increment_daily_analysis(update.effective_user.id, conf=conf)
        if conf < u["settings"]["min_confidence"]:
            await waiting.edit_text(f"<b>سیگنال معتبر نیست</b> (اعتماد {conf}٪ زیر آستانه).",
                                    parse_mode="HTML", reply_markup=back_kb()); return
        txt = format_reply(result) + f"\n\n<b>حالت ریسک فعلی:</b> {u['settings']['risk_mode']}\n\n<i>{AI_BRAND_LABEL}</i>"
        await waiting.edit_text(txt, parse_mode="HTML", reply_markup=back_kb())
    except Exception:
        log.exception("Photo handling failed")
        await waiting.edit_text("⚠️ خطا در تحلیل. دوباره امتحان کن.", parse_mode="HTML", reply_markup=back_kb())

# --- Admin (بدون تغییرات عمده؛ اگر قبلاً داشتی اضافه کن همین‌ها)
async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update): return
    if not await _require_membership(update, context): return
    await update.message.reply_text("<b>پنل ادمین</b>", parse_mode="HTML", reply_markup=admin_kb())

async def admin_menu_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update): await update.callback_query.answer("اجازه ندارید.", show_alert=True); return
    if not await _require_membership(update, context): return
    q = update.callback_query; await q.answer()
    await q.message.edit_text("<b>پنل ادمین</b>", parse_mode="HTML", reply_markup=admin_kb())

async def admin_stats_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update): await update.callback_query.answer("اجازه ندارید.", show_alert=True); return
    if not await _require_membership(update, context): return
    q = update.callback_query; await q.answer()
    pays = last_payments(5)
    lines = [f"• UID {p['user_id']} — {p['amount_stars']}⭐️ — <code>{p['payload']}</code>" for p in pays]
    await q.message.edit_text(
        "<b>📊 آمار</b>\n"
        f"• کاربران: <b>{count_users()}</b>\n"
        f"• اشتراک‌های فعال: <b>{count_active_subs()}</b>\n\n"
        "<b>آخرین پرداخت‌ها:</b>\n" + ("\n".join(lines) if lines else "—"),
        parse_mode="HTML", reply_markup=admin_kb()
    )

async def admin_grant_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update): await update.callback_query.answer("اجازه ندارید.", show_alert=True); return
    if not await _require_membership(update, context): return
    q = update.callback_query; await q.answer()
    context.user_data["ADM_MODE"] = "GRANT_WAIT"
    await q.message.edit_text("آیدی و روز را بفرست: <code>123456789 30</code>", parse_mode="HTML", reply_markup=admin_kb())

async def admin_bcast_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update): await update.callback_query.answer("اجازه ندارید.", show_alert=True); return
    if not await _require_membership(update, context): return
    q = update.callback_query; await q.answer()
    context.user_data["ADM_MODE"] = "BCAST_WAIT"
    await q.message.edit_text("متن برودکست را بفرست.", parse_mode="HTML", reply_markup=admin_kb())

async def admin_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("JOURNAL_WAIT"): return
    if not _is_owner(update): return
    if not await _require_membership(update, context): return
    mode = context.user_data.get("ADM_MODE")
    if not mode: return
    if mode == "GRANT_WAIT":
        try:
            parts = update.message.text.strip().split()
            uid = int(parts[0]); days = int(parts[1]) if len(parts) > 1 else 30
            set_subscription_days(uid, days, via="admin", plan=f"manual_{days}d")
            context.user_data["ADM_MODE"] = None
            await update.message.reply_text("اوکی! فعال شد ✅", parse_mode="HTML", reply_markup=admin_kb())
        except Exception:
            await update.message.reply_text("فرمت غلط. مثال: <code>123456789 30</code>", parse_mode="HTML", reply_markup=admin_kb())
    elif mode == "BCAST_WAIT":
        text = update.message.text; ids = all_user_ids(); ok = fail = 0
        for uid in ids:
            try: await context.bot.send_message(chat_id=uid, text=text, parse_mode="HTML"); ok += 1
            except Exception: fail += 1
        context.user_data["ADM_MODE"] = None
        await update.message.reply_text(f"برودکست تمام شد. موفق: {ok} | ناموفق: {fail}", parse_mode="HTML", reply_markup=admin_kb())

def build_app():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))

    app.add_handler(CallbackQueryHandler(main_menu,     pattern=f"^{CB_MAIN}$"))
    app.add_handler(CallbackQueryHandler(analyze_menu,  pattern=f"^{CB_ANALYZE}$"))
    app.add_handler(CallbackQueryHandler(subs_menu,     pattern=f"^{CB_SUBS}$"))
    app.add_handler(CallbackQueryHandler(subs_pay,      pattern=f"^{CB_SUBS_PAY}$"))
    app.add_handler(CallbackQueryHandler(profile_menu,  pattern=f"^{CB_PROFILE}$"))
    app.add_handler(CallbackQueryHandler(settings_menu, pattern=f"^{CB_SETTINGS}$"))
    app.add_handler(CallbackQueryHandler(
        settings_actions,
        pattern=f"^{CB_SETTINGS}.*|^{CB_SETTINGS_CONF_UP}$|^{CB_SETTINGS_CONF_DOWN}$|^{CB_SETTINGS_RISK}$|^{CB_SETTINGS_LANG}$"
    ))
    app.add_handler(CallbackQueryHandler(join_check_cb, pattern=f"^{CB_JOIN_CHECK}$"))

    # آموزش‌ها (شامل روتِر ژورنال)
    register_learn_handlers(app)

    app.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

    app.add_handler(CallbackQueryHandler(admin_menu_cb,  pattern=f"^{CB_ADMIN}$"))
    app.add_handler(CallbackQueryHandler(admin_stats_cb, pattern=f"^{CB_ADMIN_STATS}$"))
    app.add_handler(CallbackQueryHandler(admin_grant_cb, pattern=f"^{CB_ADMIN_GRANT}$"))
    app.add_handler(CallbackQueryHandler(admin_bcast_cb, pattern=f"^{CB_ADMIN_BCAST}$"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_router))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    return app
