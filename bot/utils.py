import base64
import json

# 👇 تشخیص MIME با امضاهای باینری (بدون imghdr)
def _guess_mime(image_bytes: bytes) -> str:
    b = image_bytes or b""
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if len(b) >= 8 and b[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    # JPEG: FF D8 FF
    if len(b) >= 3 and b[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    # WEBP: "RIFF" .... "WEBP"
    if len(b) >= 12 and b[:4] == b"RIFF" and b[8:12] == b"WEBP":
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
