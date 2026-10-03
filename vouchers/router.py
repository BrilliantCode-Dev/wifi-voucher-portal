"""
Router adapters. The rest of the app only calls add_user() / remove_user().

ROUTER_MODE=mock      -> nothing is sent anywhere (development and demos)
ROUTER_MODE=mikrotik  -> talks to a MikroTik hotspot through its API
"""
import logging

from django.conf import settings

log = logging.getLogger(__name__)


class RouterError(Exception):
    pass


def _hhmmss(minutes):
    hours, mins = divmod(int(minutes), 60)
    return f"{hours:02d}:{mins:02d}:00"


class MockRouter:
    users = {}  # shared in memory so tests can inspect it

    def add_user(self, code, minutes, mac, rate_limit=""):
        self.users[code] = {"minutes": minutes, "mac": mac, "rate_limit": rate_limit}
        log.info("[mock router] allow %s for %s min on %s", code, minutes, mac)

    def remove_user(self, code):
        self.users.pop(code, None)
        log.info("[mock router] remove %s", code)


class MikrotikRouter:
    def _pool(self):
        import routeros_api

        return routeros_api.RouterOsApiPool(
            settings.ROUTER_HOST,
            username=settings.ROUTER_USER,
            password=settings.ROUTER_PASSWORD,
            port=settings.ROUTER_PORT,
            plaintext_login=True,
        )

    def add_user(self, code, minutes, mac, rate_limit=""):
        pool = self._pool()
        try:
            api = pool.get_api()
            users = api.get_resource("/ip/hotspot/user")
            for existing in users.get(name=code):  # never create duplicates
                users.remove(id=existing["id"])
            fields = {
                "name": code,
                "password": code,
                "limit-uptime": _hhmmss(minutes),
                "mac-address": mac,
            }
            if rate_limit:
                fields["rate-limit"] = rate_limit
            users.add(**fields)
        except Exception as exc:
            raise RouterError(str(exc)) from exc
        finally:
            pool.disconnect()

    def remove_user(self, code):
        pool = self._pool()
        try:
            api = pool.get_api()
            active = api.get_resource("/ip/hotspot/active")
            for session in active.get(user=code):  # kick the live connection
                active.remove(id=session["id"])
            users = api.get_resource("/ip/hotspot/user")
            for existing in users.get(name=code):
                users.remove(id=existing["id"])
        except Exception as exc:
            raise RouterError(str(exc)) from exc
        finally:
            pool.disconnect()


def get_router():
    return MikrotikRouter() if settings.ROUTER_MODE == "mikrotik" else MockRouter()
