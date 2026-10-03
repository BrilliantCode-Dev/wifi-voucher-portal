from django.contrib import admin

from .models import Service, SiteInfo


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("icon", "title", "order", "is_active")
    list_editable = ("order", "is_active")


@admin.register(SiteInfo)
class SiteInfoAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteInfo.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
