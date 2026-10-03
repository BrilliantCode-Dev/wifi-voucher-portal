import secrets

from django.conf import settings
from django.db import models

# No 0/O or 1/I/L, so printed codes are easy to read and type
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_code(length=8):
    raw = "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))
    return f"{raw[:4]}-{raw[4:]}"  # e.g. K7M2-9QXA


class Package(models.Model):
    """What the cafe sells: e.g. '1 Hour', '3 Hours', 'Full Day'."""

    name = models.CharField(max_length=50)
    duration_minutes = models.PositiveIntegerField(help_text="How long the customer can use the internet.")
    price = models.DecimalField(max_digits=8, decimal_places=2)
    valid_days = models.PositiveIntegerField(
        default=30, help_text="A sold voucher must be used within this many days."
    )
    speed_limit = models.CharField(
        max_length=20, blank=True,
        help_text="Optional speed cap per customer in MikroTik format, e.g. 3M/3M. Leave empty for no cap.",
    )
    is_active = models.BooleanField(default=True, help_text="Untick to stop selling this package.")

    class Meta:
        ordering = ["duration_minutes"]

    def __str__(self):
        return f"{self.name} ({self.price})"

    @property
    def duration_label(self):
        m = self.duration_minutes
        if m % 1440 == 0:
            days = m // 1440
            return "24 hours" if days == 1 else f"{days} days"
        if m % 60 == 0:
            hours = m // 60
            return "1 hour" if hours == 1 else f"{hours} hours"
        return f"{m} minutes"


class VoucherBatch(models.Model):
    """A print run of voucher cards."""

    package = models.ForeignKey(Package, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "voucher batches"

    def __str__(self):
        return f"Batch #{self.pk}: {self.quantity} x {self.package.name}"


class Voucher(models.Model):
    class Status(models.TextChoices):
        UNUSED = "unused", "Unused"
        ACTIVE = "active", "In use"
        EXPIRED = "expired", "Expired"
        VOID = "void", "Cancelled"

    code = models.CharField(max_length=12, unique=True, default=generate_code)
    package = models.ForeignKey(Package, on_delete=models.PROTECT)
    batch = models.ForeignKey(VoucherBatch, null=True, blank=True, on_delete=models.SET_NULL, related_name="vouchers")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.UNUSED, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField(null=True, blank=True)    # set when sold: must be used before this
    activated_at = models.DateTimeField(null=True, blank=True)   # the clock starts at first login
    expires_at = models.DateTimeField(null=True, blank=True)
    device_mac = models.CharField(max_length=17, blank=True)     # one voucher = one device

    def __str__(self):
        return f"{self.code} [{self.status}]"

    @property
    def is_sold(self):
        return hasattr(self, "sale")


class Sale(models.Model):
    """Money received for a voucher. A voucher only works after it has been sold."""

    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        ECOCASH = "ecocash", "EcoCash"

    voucher = models.OneToOneField(Voucher, on_delete=models.PROTECT)
    sold_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=8, decimal_places=2)  # price at the time of sale
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.CASH)
    sold_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.voucher.code} - {self.amount}"


class Session(models.Model):
    """A log of each time a customer connected with a voucher."""

    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, related_name="sessions")
    mac = models.CharField(max_length=17)
    ip = models.GenericIPAddressField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
