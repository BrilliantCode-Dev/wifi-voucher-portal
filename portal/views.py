import logging
import re
from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from vouchers.services import VoucherError, redeem_voucher

log = logging.getLogger(__name__)
MAC_RE = re.compile(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$")


def clean_mac(raw):
    mac = (raw or "").strip().upper().replace("-", ":")
    return mac if MAC_RE.match(mac) else ""


def safe_login_url(url):
    """Only allow sending the customer back to our own router."""
    try:
        parsed = urlparse(url or "")
    except ValueError:
        return ""
    if parsed.scheme in ("http", "https") and parsed.hostname in settings.HOTSPOT_LOGIN_HOSTS:
        return url
    return ""


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")) or None


def _count(key):
    return cache.get(key, 0)


def _bump(key):
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, settings.PORTAL_FAIL_WINDOW_SECONDS)


@never_cache
def login(request):
    data = request.POST if request.method == "POST" else request.GET
    ctx = {
        "mac": data.get("mac", ""),
        "ip": data.get("ip", ""),
        "login": data.get("login", ""),
        "dst": data.get("dst", ""),
        "error": "",
    }
    if request.method != "POST":
        return render(request, "portal/login.html", ctx)

    mac = clean_mac(ctx["mac"])
    if not mac and settings.ROUTER_MODE == "mock":
        mac = "00:00:00:00:00:00"  # demo mode has no router to tell us the MAC
    ip = client_ip(request)
    dev_key, ip_key = f"portal:fail:mac:{mac}", f"portal:fail:ip:{ip}"

    if not mac:
        ctx["error"] = "We could not identify your device. Disconnect from the Wi-Fi, reconnect, and try again."
    elif _count(dev_key) >= settings.PORTAL_MAX_FAILS_PER_DEVICE or _count(ip_key) >= settings.PORTAL_MAX_FAILS_PER_IP:
        ctx["error"] = "Too many wrong tries. Please wait 10 minutes or ask at the counter."
    else:
        try:
            voucher = redeem_voucher(request.POST.get("code", ""), mac, ip)
        except VoucherError as exc:
            _bump(dev_key)
            _bump(ip_key)
            ctx["error"] = str(exc)
        else:
            login_url = safe_login_url(ctx["login"])
            return render(request, "portal/connecting.html", {
                "voucher": voucher,
                "login_url": login_url,
                "dst": ctx["dst"],
                "minutes_left": max(int((voucher.expires_at - timezone.now()).total_seconds() // 60), 0),
            })
    return render(request, "portal/login.html", ctx)
