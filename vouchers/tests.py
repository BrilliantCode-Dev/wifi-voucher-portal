from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Package, Sale, Voucher
from .router import MockRouter
from .services import VoucherError, redeem_voucher, sell_voucher

User = get_user_model()
MAC1, MAC2 = "AA:BB:CC:00:00:01", "AA:BB:CC:00:00:02"


class Base(TestCase):
    def setUp(self):
        cache.clear()
        MockRouter.users.clear()
        self.owner = User.objects.create_user("owner", password="pw12345!", is_staff=True)
        self.cashier = User.objects.create_user("cashier", password="pw12345!")
        self.pkg = Package.objects.create(name="Test Hour", duration_minutes=60, price="1.50")

    def sold(self, **kw):
        return sell_voucher(user=self.cashier, method="cash", package=self.pkg, **kw).voucher


class ServiceTests(Base):
    def test_sale_records_price_and_voucher(self):
        sale = sell_voucher(user=self.cashier, method="cash", package=self.pkg)
        self.assertEqual(str(sale.amount), "1.50")
        self.assertEqual(sale.voucher.status, Voucher.Status.UNUSED)

    def test_unsold_voucher_cannot_be_used(self):
        v = Voucher.objects.create(package=self.pkg)
        with self.assertRaises(VoucherError):
            redeem_voucher(v.code, MAC1)

    def test_pre_printed_card_can_be_sold_once(self):
        card = Voucher.objects.create(package=self.pkg)
        sell_voucher(user=self.cashier, method="cash", code=card.code)
        with self.assertRaises(VoucherError):
            sell_voucher(user=self.cashier, method="cash", code=card.code)

    def test_redeem_activates_and_unlocks_router(self):
        v = self.sold()
        redeem_voucher(v.code.lower(), MAC1)  # lower case is accepted
        v.refresh_from_db()
        self.assertEqual(v.status, Voucher.Status.ACTIVE)
        self.assertEqual(v.device_mac, MAC1)
        self.assertEqual(MockRouter.users[v.code]["minutes"], 60)

    def test_same_device_can_reconnect_but_other_device_cannot(self):
        v = self.sold()
        redeem_voucher(v.code, MAC1)
        redeem_voucher(v.code, MAC1)
        with self.assertRaises(VoucherError):
            redeem_voucher(v.code, MAC2)

    def test_expiry_job_cuts_off_finished_vouchers(self):
        v = self.sold()
        redeem_voucher(v.code, MAC1)
        Voucher.objects.filter(pk=v.pk).update(expires_at=timezone.now() - timedelta(minutes=1))
        call_command("expire_vouchers")
        v.refresh_from_db()
        self.assertEqual(v.status, Voucher.Status.EXPIRED)
        self.assertNotIn(v.code, MockRouter.users)
        with self.assertRaises(VoucherError):
            redeem_voucher(v.code, MAC1)

    def test_sold_voucher_not_used_in_time_expires(self):
        v = self.sold()
        Voucher.objects.filter(pk=v.pk).update(valid_until=timezone.now() - timedelta(days=1))
        with self.assertRaises(VoucherError):
            redeem_voucher(v.code, MAC1)


class ApiTests(Base):
    def client_for(self, username):
        c = APIClient()
        r = c.post("/api/auth/login/", {"username": username, "password": "pw12345!"})
        self.assertEqual(r.status_code, 200)
        c.credentials(HTTP_AUTHORIZATION="Token " + r.data["token"])
        return c, r.data

    def test_login_reports_role(self):
        _, data = self.client_for("owner")
        self.assertTrue(data["is_owner"])
        _, data = self.client_for("cashier")
        self.assertFalse(data["is_owner"])

    def test_api_requires_login(self):
        self.assertEqual(APIClient().get("/api/packages/").status_code, 401)

    def test_cashier_can_sell_but_not_see_reports_or_edit_packages(self):
        c, _ = self.client_for("cashier")
        r = c.post("/api/sell/", {"package": self.pkg.id, "method": "ecocash"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["method"], "ecocash")
        self.assertEqual(c.get("/api/reports/daily/").status_code, 403)
        self.assertEqual(c.post("/api/batches/", {"package": self.pkg.id, "quantity": 5}).status_code, 403)
        self.assertEqual(c.patch(f"/api/packages/{self.pkg.id}/", {"price": "9"}, format="json").status_code, 403)

    def test_sell_validates_input(self):
        c, _ = self.client_for("cashier")
        self.assertEqual(c.post("/api/sell/", {"method": "cash"}, format="json").status_code, 400)
        self.assertEqual(c.post("/api/sell/", {"package": self.pkg.id, "method": "bitcoin"}, format="json").status_code, 400)

    def test_owner_reports_add_up(self):
        c, _ = self.client_for("cashier")
        c.post("/api/sell/", {"package": self.pkg.id, "method": "cash"}, format="json")
        c.post("/api/sell/", {"package": self.pkg.id, "method": "ecocash"}, format="json")
        o, _ = self.client_for("owner")
        r = o.get("/api/reports/daily/").data
        self.assertEqual(r["count"], 2)
        self.assertEqual(r["total"], 3.0)
        self.assertEqual(len(r["hourly"]), 24)
        self.assertEqual(sum(h["count"] for h in r["hourly"]), 2)
        self.assertEqual(r["by_staff"][0]["label"], "cashier")
        self.assertEqual({m["label"] for m in r["by_method"]}, {"Cash", "EcoCash"})
        trend = o.get("/api/reports/trend/?days=7").data
        self.assertEqual(len(trend), 7)
        self.assertEqual(trend[-1]["total"], 3.0)

    def test_cashier_only_sees_own_sales(self):
        sell_voucher(user=self.owner, method="cash", package=self.pkg)
        c, _ = self.client_for("cashier")
        c.post("/api/sell/", {"package": self.pkg.id, "method": "cash"}, format="json")
        self.assertEqual(c.get("/api/sales/").data["count"], 1)
        o, _ = self.client_for("owner")
        self.assertEqual(o.get("/api/sales/").data["count"], 2)

    def test_batch_create_and_void(self):
        o, _ = self.client_for("owner")
        r = o.post("/api/batches/", {"package": self.pkg.id, "quantity": 10}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.data["codes"]), 10)
        self.assertEqual(len(o.get(f"/api/batches/{r.data['id']}/").data["codes"]), 10)
        v = self.sold()
        redeem_voucher(v.code, MAC1)
        self.assertEqual(o.post(f"/api/vouchers/{v.id}/void/").status_code, 200)
        self.assertNotIn(v.code, MockRouter.users)
        with self.assertRaises(VoucherError):
            redeem_voucher(v.code, MAC1)

    def test_no_bulk_over_limit(self):
        o, _ = self.client_for("owner")
        self.assertEqual(o.post("/api/batches/", {"package": self.pkg.id, "quantity": 500}, format="json").status_code, 400)


class PortalTests(Base):
    def post(self, code, mac=MAC1, login="http://192.168.88.1/login"):
        return self.client.post(reverse("wifi-login"), {"code": code, "mac": mac, "login": login, "dst": "http://example.com"})

    def test_good_code_redirects_browser_to_router(self):
        v = self.sold()
        r = self.post(v.code)
        self.assertContains(r, 'action="http://192.168.88.1/login"')
        self.assertContains(r, f'value="{v.code}"')

    def test_foreign_login_url_is_ignored(self):
        v = self.sold()
        r = self.post(v.code, login="http://evil.example/steal")
        self.assertNotContains(r, "evil.example")
        self.assertContains(r, "Voucher accepted")

    def test_bad_code_shows_message(self):
        r = self.post("NOPE-NOPE")
        self.assertContains(r, "not right")

    def test_device_is_locked_out_after_repeated_wrong_codes(self):
        for _ in range(8):
            self.post("WRONG-CODE")
        v = self.sold()
        self.assertContains(self.post(v.code), "Too many wrong tries")
        # a different phone in the same cafe is not affected
        self.assertContains(self.post(v.code, mac=MAC2), "Connecting you")

    @override_settings(ROUTER_MODE="mikrotik")
    def test_real_router_mode_needs_a_device_address(self):
        v = self.sold()
        self.assertContains(self.post(v.code, mac=""), "could not identify your device")

    def test_form_page_loads(self):
        self.assertContains(self.client.get(reverse("wifi-login")), "Voucher code")


class SiteTests(TestCase):
    def test_public_site_shows_services_and_packages(self):
        r = self.client.get("/")
        self.assertContains(r, "Internet Access")
        self.assertContains(r, "CV &amp; Job Application Services")
        self.assertContains(r, "1 Hour")

    def test_dashboard_page_loads(self):
        self.assertEqual(self.client.get("/dashboard/").status_code, 200)
