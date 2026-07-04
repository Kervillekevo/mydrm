# videos/security.py
import time
import hmac
import hashlib
import secrets

from django.conf import settings
from django.core.cache import cache



PLAYLIST_TTL = 60
SEGMENT_TTL = 10
KEY_TTL = 120



SEGMENT_RATE_LIMIT = 30
SEGMENT_RATE_WINDOW = 2

KEY_RATE_LIMIT = 30
KEY_RATE_WINDOW = 5


MAX_CONCURRENT_SEGMENTS = 4



def _sign(message: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()


def _fingerprint(request):


    
    ip = request.META.get("REMOTE_ADDR", "")
    ip_prefix = ".".join(ip.split(".")[:3])  

    ua = request.META.get("HTTP_USER_AGENT", "")[:120]

    session = request.session.session_key
    if not session:
        session = cache.get_or_set(
            f"anon_session:{ip_prefix}:{ua}",
            secrets.token_hex(16),
            timeout=300,
        )

    return ip_prefix, ua, session


def _ttl(resource_type: str, issued_at: int) -> int:
    jitter = issued_at % 5
    base = {
        "playlist": PLAYLIST_TTL,
        "segment": SEGMENT_TTL,
        "key": KEY_TTL,
    }.get(resource_type, 0)
    return base + jitter


def check_rate_limit(ip: str, key: str, limit: int, window: int) -> bool:
    cache_key = f"rate:{ip}:{key}"

    try:
        count = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, timeout=window)
        return True

    return count <= limit


def acquire_segment_slot(ip: str, video_id: str) -> bool:
    key = f"concurrent:{ip}:{video_id}"

    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=10)
        return True

    if count > MAX_CONCURRENT_SEGMENTS:
        cache.decr(key)
        return False

    return True


def release_segment_slot(ip: str, video_id: str):
    try:
        cache.decr(f"concurrent:{ip}:{video_id}")
    except Exception:
        pass



def validate_segment_order(ip: str, video_id: str, segment_name: str) -> bool:
    """
    Allows small jumps (adaptive bitrate) but blocks bulk download.
    """
    try:
        index = int(segment_name.split("_")[-1].split(".")[0])
    except Exception:
        return False

    key = f"last_segment:{ip}:{video_id}"
    last = cache.get(key)

    if last is not None:
        if index > last + 3 or index < last - 3:
            return False

    cache.set(key, index, timeout=30)
    return True


def generate_stream_token(*, video_id, resource_type, resource_name="", request, ttl=None):
    issued_at = int(time.time())
    ip, ua, session = _fingerprint(request)

    nonce = secrets.token_hex(6)

    message = (
        f"{video_id}:{resource_type}:{resource_name}:"
        f"{issued_at}:{ip}:{ua}:{session}:{nonce}"
    )

    signature = _sign(message)

    cache.set(
        f"nonce:{signature}",
        True,
        timeout=ttl or _ttl(resource_type, issued_at),
    )

    return f"{issued_at}:{nonce}:{signature}"



def validate_stream_token(*, token, video_id, resource_type, resource_name="", request):
    try:
        issued_at, nonce, signature = token.split(":")
        issued_at = int(issued_at)

        ttl = _ttl(resource_type, issued_at)
        if ttl == 0 or time.time() - issued_at > ttl:
            return False

        if not cache.get(f"nonce:{signature}"):
            return False

        ip, ua, session = _fingerprint(request)

        message = (
            f"{video_id}:{resource_type}:{resource_name}:"
            f"{issued_at}:{ip}:{ua}:{session}:{nonce}"
        )

        if not hmac.compare_digest(signature, _sign(message)):
            return False

        if resource_type == "segment":
            if not check_rate_limit(ip, "segment", SEGMENT_RATE_LIMIT, SEGMENT_RATE_WINDOW):
                return False
            if not validate_segment_order(ip, video_id, resource_name):
                return False

        if resource_type == "key":
            if not check_rate_limit(ip, "key", KEY_RATE_LIMIT, KEY_RATE_WINDOW):
                return False

        return True

    except Exception:
        return False
