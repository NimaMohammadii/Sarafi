def format_reply(j: dict) -> str:
    bias_map = {"LONG": "📈 لانگ", "SHORT": "📉 شورت", "NO_TRADE": "⏸️ نوترید"}
    bias = j.get("bias", "NO_TRADE")
    conf = j.get("confidence_percent", 0)
    rationale = j.get("rationale", "")
    levels = j.get("levels", {})
    notes = j.get("notes", "")

    parts = []
    parts.append(f"<b>نتیجه:</b> {bias_map.get(bias, bias)} (<b>{conf}٪</b> اعتماد)\n")

    if rationale:
        if isinstance(rationale, str):
            rats = [r.strip("•- ") for r in rationale.split("\n") if r.strip()]
        else:
            rats = rationale
        rats = rats[:3]
        if rats:
            parts.append("<b>دلایل:</b>\n" + "\n".join([f"• {r}" for r in rats]))

    if levels and any(levels.get(k) for k in ["entry", "stop_loss", "tp1", "tp2"]):
        parts.append("\n<b>پلن احتمالی:</b>")
        if levels.get("entry"):
            parts.append(f"• <b>ورود:</b> {levels['entry']}")
        if levels.get("stop_loss"):
            parts.append(f"• <b>حدضرر:</b> {levels['stop_loss']}")
        if levels.get("tp1"):
            parts.append(f"• <b>تارگت ۱:</b> {levels['tp1']}")
        if levels.get("tp2"):
            parts.append(f"• <b>تارگت ۲:</b> {levels['tp2']}")

    if notes:
        parts.append("\n<b>نکات:</b> " + notes)

    parts.append("\n<b>⚠️ تحلیل ماشینی است و سیگنال قطعی نیست.</b>")
    return "\n".join(parts)