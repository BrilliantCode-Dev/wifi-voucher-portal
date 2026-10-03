from django.contrib import admin

from .models import Package, Sale, Session, Voucher, VoucherBatch


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ("name", "duration_minutes", "price", "is_active")
    list_editable = ("price", "is_active")


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = ("code", "package", "status", "activated_at", "expires_at")
    list_filter = ("status", "package")
    search_fields = ("code",)


admin.site.register(Sale)
admin.site.register(VoucherBatch)
admin.site.register(Session)
