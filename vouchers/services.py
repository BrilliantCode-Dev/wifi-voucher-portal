import logging
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Package, Sale, Session, Voucher
from .router import RouterError, get_router

log = logging.getLogger(__name__)


class VoucherError(Exception):
    """The message is safe to show to the customer or staff member."""


def normalize_code(code):
    return (code or "").strip().upper().replace(" ", "")


def create_vouchers(package, quantity, batch=None):
    created = []
    while len(created) < quantity:
        try:
            with transaction.atomic():
                created.append(Voucher.objects.create(package=package, batch=batch))
        except IntegrityError:  # random code collided: just try another
            continue
    return created


@transaction.atomic
def sell_voucher(*, user, method, package=None, code=None):
    """
    Sell a voucher at the counter.
      - code given  -> sell that pre-printed card
      - no code     -> create a fresh voucher for `package` on the spot
    """
    if method not in Sale.Method.values:
        raise VoucherError("Choose how the customer paid.")

    if code:
        try:
            voucher = Voucher.objects.select_for_update().select_related("package").get(code=normalize_code(code))
        except Voucher.DoesNotExist:
            raise VoucherError("That card code was not found.")
        if voucher.status != Voucher.Status.UNUSED or voucher.is_sold:
            raise VoucherError("That card has already been sold.")
    else:
        if package is None or not package.is_active:
            raise VoucherError("Choose a package to sell.")
        voucher = create_vouchers(package, 1)[0]

    pkg = voucher.package
    if not pkg.is_active:
        raise VoucherError("This package is no longer on sale.")
    voucher.valid_until = timezone.now() + timedelta(days=pkg.valid_days)
    voucher.save(update_fields=["valid_until"])
    sale = Sale.objects.create(voucher=voucher, sold_by=user, amount=pkg.price, method=method)
    return sale


@transaction.atomic
def redeem_voucher(code, mac, ip=None):
    """Validate a code and unlock the customer's device. Returns the voucher."""
    code = normalize_code(code)
    try:
        # The row lock stops two people redeeming one code at the same moment
        voucher = Voucher.objects.select_for_update().select_related("package").get(code=code)
    except Voucher.DoesNotExist:
        raise VoucherError("That code is not right. Check it and try again.")

    if not voucher.is_sold or voucher.status == Voucher.Status.VOID:
        raise VoucherError("That code is not valid. Please ask at the counter.")

    now = timezone.now()

    if voucher.status == Voucher.Status.UNUSED:
        if voucher.valid_until and now > voucher.valid_until:
            voucher.status = Voucher.Status.EXPIRED
            voucher.save(update_fields=["status"])
            raise VoucherError("This voucher has expired.")
        voucher.status = Voucher.Status.ACTIVE
        voucher.activated_at = now
        voucher.expires_at = now + timedelta(minutes=voucher.package.duration_minutes)
        voucher.device_mac = mac
        voucher.save()
        try:
            get_router().add_user(voucher.code, voucher.package.duration_minutes, mac, voucher.package.speed_limit)
        except RouterError:
            log.exception("Router error while activating %s", voucher.code)
            # Raising rolls the whole transaction back, so the voucher stays unused
            raise VoucherError("We could not connect you right now. Please ask staff for help.")

    elif voucher.status == Voucher.Status.ACTIVE:
        if now >= voucher.expires_at:
            voucher.status = Voucher.Status.EXPIRED
            voucher.save(update_fields=["status"])
            raise VoucherError("Your time has finished. Please buy a new voucher.")
        if voucher.device_mac != mac:
            raise VoucherError("This voucher is already in use on another device.")

    else:  # expired
        raise VoucherError("This voucher has expired.")

    Session.objects.create(voucher=voucher, mac=mac, ip=ip)
    return voucher


def void_voucher(voucher):
    was_active = voucher.status == Voucher.Status.ACTIVE
    voucher.status = Voucher.Status.VOID
    voucher.save(update_fields=["status"])
    if was_active:
        try:
            get_router().remove_user(voucher.code)
        except RouterError:
            log.exception("Router error while removing %s", voucher.code)


def expire_stale_vouchers():
    """Mark finished vouchers as expired and cut them off at the router."""
    now = timezone.now()
    count = 0
    for v in Voucher.objects.filter(status=Voucher.Status.ACTIVE, expires_at__lte=now):
        try:
            get_router().remove_user(v.code)
        except RouterError:
            log.exception("Router error while expiring %s (will retry)", v.code)
            continue
        v.status = Voucher.Status.EXPIRED
        v.save(update_fields=["status"])
        count += 1
    # Sold but never used within their validity window
    stale = Voucher.objects.filter(status=Voucher.Status.UNUSED, valid_until__lt=now)
    count += stale.update(status=Voucher.Status.EXPIRED)
    return count
