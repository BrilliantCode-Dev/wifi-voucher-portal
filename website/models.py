from django.db import models


class SiteInfo(models.Model):
    """One row of contact details and wording shown on the public website."""

    tagline = models.CharField(max_length=140, default="Internet, printing and paperwork, all in one place.")
    intro = models.CharField(max_length=240, default="Walk in with a phone or a document. Walk out online, printed or applied.")
    phone = models.CharField(max_length=40, blank=True)
    whatsapp = models.CharField(max_length=40, blank=True, help_text="Digits only with country code, e.g. 263771234567")
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=200, blank=True)
    opening_hours = models.TextField(blank=True, help_text="One line per row, e.g. Mon-Fri: 08:00 - 18:00")

    class Meta:
        verbose_name = "website details"
        verbose_name_plural = "website details"

    def __str__(self):
        return "Website details"


class Service(models.Model):
    icon = models.CharField(max_length=8, help_text="One emoji")
    title = models.CharField(max_length=80)
    description = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first.")
    is_active = models.BooleanField(default=True, help_text="Untick to hide this service from the website.")

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title
