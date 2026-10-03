from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "DM Internet Cafe - Admin"
admin.site.site_title = "DM Internet Cafe"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("vouchers.urls")),
    path("wifi/", include("portal.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("", include("website.urls")),
]
