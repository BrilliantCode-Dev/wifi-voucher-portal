from django.urls import path
from rest_framework.routers import DefaultRouter

from . import api

router = DefaultRouter()
router.register("packages", api.PackageViewSet, basename="package")

urlpatterns = [
    path("auth/login/", api.LoginView.as_view()),
    path("auth/logout/", api.LogoutView.as_view()),
    path("auth/me/", api.MeView.as_view()),
    path("sell/", api.SellView.as_view()),
    path("sales/", api.SalesListView.as_view()),
    path("vouchers/", api.VoucherListView.as_view()),
    path("vouchers/<int:pk>/void/", api.VoucherVoidView.as_view()),
    path("batches/", api.BatchView.as_view()),
    path("batches/<int:pk>/", api.BatchView.as_view()),
    path("reports/daily/", api.DailyReportView.as_view()),
    path("reports/trend/", api.TrendReportView.as_view()),
] + router.urls
