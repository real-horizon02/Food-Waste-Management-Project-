"""
Simple file-backed nutrition cache with TTL.
Provides get/set for cached per-ingredient nutrition results.
"""
import json
import os
import time
import threading

_lock = threading.Lock()
_cache = None
_cache_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tmp', 'nutrition_cache.json')
_default_ttl = 60 * 60 * 24 * 30  # 30 days


def _ensure_loaded():
    global _cache
    if _cache is not None:
        return
    with _lock:
        if _cache is not None:
            return
        try:
            os.makedirs(os.path.dirname(_cache_path), exist_ok=True)
            if os.path.exists(_cache_path):
                with open(_cache_path, 'r', encoding='utf-8') as fh:
                    _cache = json.load(fh)
            else:
                _cache = {}
        except Exception:
            _cache = {}


def _persist():
    try:
        with _lock:
            tmp = _cache or {}
            with open(_cache_path, 'w', encoding='utf-8') as fh:
                json.dump(tmp, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


def make_key(name, quantity, unit):
    return f"{(name or '').strip().lower()}|{(str(quantity) or '').strip()}|{(unit or '').strip().lower()}"


def get(key):
    try:
        _ensure_loaded()
        entry = _cache.get(key)
        if not entry:
            return None
        # check ttl
        ts = entry.get('_ts', 0)
        ttl = entry.get('_ttl', _default_ttl)
        if time.time() - ts > ttl:
            # expired
            with _lock:
                _cache.pop(key, None)
                _persist()
            return None
        return entry.get('value')
    except Exception:
        return None


def set(key, value, ttl=_default_ttl):
    try:
        # Don't cache zero-value nutrition entries - they should be re-fetched for better data
        if isinstance(value, dict) and all(v == 0 for v in value.values()):
            return  # Skip caching if all nutrition values are zero
        
        _ensure_loaded()
        with _lock:
            _cache[key] = {
                '_ts': time.time(),
                '_ttl': ttl,
                'value': value
            }
            _persist()
    except Exception:
        pass


def clear():
    try:
        _ensure_loaded()
        with _lock:
            _cache.clear()
            _persist()
    except Exception:
        pass
