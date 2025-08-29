import json, os, threading, time
DB_PATH = os.getenv("DB_PATH", "db.json")
_lock = threading.Lock()

def _load():
    if not os.path.exists(DB_PATH):
        return {"users": {}}
    with open(DB_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {"users": {}}

def _save(data):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def ensure_user(user_id: int, username: str = "", name: str = ""):
    with _lock:
        db = _load()
        u = db["users"].get(str(user_id))
        if not u:
            now = int(time.time())
            u = {
                "user_id": user_id,
                "username": username or "",
                "name": name or "",
                "created_at": now,
                "subscription": {
                    "active": False,
                    "plan": None,
                    "start_ts": None,
                    "end_ts": None,
                    "via": None   # "stars" | "rial"
                },
                "settings": {
                    "lang": "fa",
                    "min_confidence": 55,     # آستانه اعتماد
                    "risk_mode": "conservative"  # conservative | balanced | aggressive
                },
                "stats": {
                    "analyses_count": 0,
                    "last_analysis_ts": None,
                    "last_confidence": None
                }
            }
            db["users"][str(user_id)] = u
            _save(db)
        return u

def get_user(user_id: int):
    with _lock:
        return _load()["users"].get(str(user_id))

def update_user(user_id: int, patch: dict):
    with _lock:
        db = _load()
        u = db["users"].get(str(user_id))
        if not u:
            return ensure_user(user_id)
        # merge سطحی
        for k, v in patch.items():
            if isinstance(v, dict) and isinstance(u.get(k), dict):
                u[k].update(v)
            else:
                u[k] = v
        db["users"][str(user_id)] = u
        _save(db)
        return u

def increment_analysis(user_id: int, conf: int = None):
    with _lock:
        db = _load()
        u = db["users"].get(str(user_id))
        if not u:
            u = ensure_user(user_id)
        u["stats"]["analyses_count"] = u["stats"].get("analyses_count", 0) + 1
        u["stats"]["last_analysis_ts"] = int(time.time())
        if conf is not None:
            u["stats"]["last_confidence"] = conf
        db["users"][str(user_id)] = u
        _save(db)
        return u

# --- افزوده‌ها: آمار و پرداخت/اشتراک دستی ---
def _ensure_shape(data):
    # تضمین وجود کلیدها در DB
    if "users" not in data:
        data["users"] = {}
    if "payments" not in data:
        data["payments"] = []
    return data

def _load():
    # جایگزین نسخه قبلی اگر قبلاً همین نام را داشتی: فقط انتهای تابع این خط را اضافه کن
    import json, os
    if not os.path.exists(DB_PATH):
        return _ensure_shape({"users": {}, "payments": []})
    with open(DB_PATH, "r", encoding="utf-8") as f:
        try:
            return _ensure_shape(json.load(f))
        except Exception:
            return _ensure_shape({"users": {}, "payments": []})

def count_users():
    return len(_load().get("users", {}))

def all_user_ids():
    return [int(uid) for uid in _load().get("users", {}).keys()]

def count_active_subs():
    db = _load()
    c = 0
    import time
    now = int(time.time())
    for u in db["users"].values():
        sub = u.get("subscription", {}) or {}
        if sub.get("active") and (not sub.get("end_ts") or sub["end_ts"] > now):
            c += 1
    return c

def set_subscription_days(user_id: int, days: int, via="manual", plan="manual"):
    import time
    now = int(time.time())
    end = now + days * 24 * 3600
    return update_user(user_id, {
        "subscription": {
            "active": True, "plan": plan,
            "start_ts": now, "end_ts": end, "via": via
        }
    })

def add_payment_record(user_id: int, amount_stars: int, payload: str):
    with _lock:
        db = _load()
        import time
        db["payments"].append({
            "user_id": user_id,
            "amount_stars": amount_stars,
            "payload": payload,
            "ts": int(time.time())
        })
        _save(db)

def last_payments(n=5):
    db = _load()
    return list(reversed(db.get("payments", [])[-n:]))