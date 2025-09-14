import base64
import json
import imghdr

def _guess_mime(image_bytes: bytes) -> str:
    kind = imghdr.what(None, h=image_bytes)
    if kind == "png":
        return "image/png"
    if kind in ("jpg", "jpeg"):
        return "image/jpeg"
    if kind == "webp":
        return "image/webp"
    return "application/octet-stream"

def image_bytes_to_data_url(image_bytes: bytes, mime=None) -> str:
    if not mime:
        mime = _guess_mime(image_bytes)
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.lstrip("`")
        if "\n" in t:
            t = t.split("\n", 1)[1]
        t = t.rstrip("`")
    return t.strip()

def safe_load_json(text: str):
    try:
        return json.loads(text)
    except Exception:
        text = text.replace("\ufeff", "").strip()
        return json.loads(text)