from datetime import datetime, time, timedelta

from django.conf import settings
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import ExtractHour, TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import serializers, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import Package, Sale, Voucher, VoucherBatch
from .services import VoucherError, create_vouchers, sell_voucher, void_voucher


# ---- permissions ----------------------------------------------------------
class IsOwner(BasePermission):
    """The owner = a staff user. Cashiers are normal (non-staff) users."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsOwnerOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or request.user.is_staff


# ---- serializers ----------------------------------------------------------
class PackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = ["id", "name", "duration_minutes", "price", "valid_days", "speed_limit", "is_active"]


class VoucherSerializer(serializers.ModelSerializer):
    package_name = serializers.CharField(source="package.name", read_only=True)
    sold_at = serializers.SerializerMethodField()

    class Meta:
        model = Voucher
        fields = ["id", "code", "package", "package_name", "status", "sold_at",
                  "activated_at", "expires_at", "device_mac"]

    def get_sold_at(self, obj):
        sale = getattr(obj, "sale", None)
        return sale.sold_at if sale else None


class SaleSerializer(serializers.ModelSerializer):
    code = serializers.CharField(source="voucher.code", read_only=True)
    package_name = serializers.CharField(source="voucher.package.name", read_only=True)
    duration_minutes = serializers.IntegerField(source="voucher.package.duration_minutes", read_only=True)
    sold_by_name = serializers.CharField(source="sold_by.username", read_only=True)

    class Meta:
        model = Sale
        fields = ["id", "code", "package_name", "duration_minutes", "amount", "method", "sold_by_name", "sold_at"]


# ---- auth -----------------------------------------------------------------
def user_payload(user):
    return {
        "username": user.username,
        "is_owner": user.is_staff,
        "cafe_name": settings.CAFE_NAME,
        "currency": settings.CURRENCY_SYMBOL,
    }


class LoginView(ObtainAuthToken):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, **user_payload(user)})


class MeView(APIView):
    def get(self, request):
        return Response(user_payload(request.user))


class LogoutView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---- packages -------------------------------------------------------------
class PackageViewSet(viewsets.ModelViewSet):
    serializer_class = PackageSerializer
    permission_classes = [IsOwnerOrReadOnly]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]  # no deleting: deactivate instead

    def get_queryset(self):
        qs = Package.objects.all()
        return qs if self.request.user.is_staff else qs.filter(is_active=True)


# ---- selling --------------------------------------------------------------
class SellView(APIView):
    def post(self, request):
        code = (request.data.get("code") or "").strip()
        package = None
        if not code:
            package = Package.objects.filter(pk=request.data.get("package")).first()
        try:
            sale = sell_voucher(user=request.user, method=request.data.get("method"), package=package, code=code)
        except VoucherError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SaleSerializer(sale).data, status=status.HTTP_201_CREATED)


def day_bounds(date_str=None):
    day = parse_date(date_str) if date_str else None
    day = day or timezone.localdate()
    start = timezone.make_aware(datetime.combine(day, time.min))
    return day, start, start + timedelta(days=1)


class SalesListView(APIView):
    def get(self, request):
        _, start, end = day_bounds(request.query_params.get("date"))
        qs = Sale.objects.filter(sold_at__gte=start, sold_at__lt=end).select_related(
            "voucher__package", "sold_by"
        )
        if not request.user.is_staff:  # cashiers only see their own sales
            qs = qs.filter(sold_by=request.user)
        qs = qs.order_by("-sold_at")
        total = qs.aggregate(t=Sum("amount"))["t"] or 0
        return Response({"total": float(total), "count": qs.count(), "sales": SaleSerializer(qs[:200], many=True).data})


# ---- vouchers -------------------------------------------------------------
class VoucherListView(APIView):
    def get(self, request):
        qs = Voucher.objects.select_related("package", "sale").order_by("-id")
        st = request.query_params.get("status")
        if st == "unsold":
            qs = qs.filter(sale__isnull=True, status=Voucher.Status.UNUSED)
        elif st in Voucher.Status.values:
            qs = qs.filter(status=st, sale__isnull=False)
        q = (request.query_params.get("q") or "").strip().upper()
        if q:
            qs = qs.filter(code__icontains=q)
        return Response(VoucherSerializer(qs[:200], many=True).data)


class VoucherVoidView(APIView):
    permission_classes = [IsOwner]

    def post(self, request, pk):
        voucher = Voucher.objects.filter(pk=pk).first()
        if not voucher:
            return Response({"detail": "Voucher not found."}, status=404)
        void_voucher(voucher)
        return Response(VoucherSerializer(voucher).data)


class BatchView(APIView):
    permission_classes = [IsOwner]

    def get(self, request, pk=None):
        if pk:
            batch = VoucherBatch.objects.select_related("package").filter(pk=pk).first()
            if not batch:
                return Response({"detail": "Batch not found."}, status=404)
            return Response(self._detail(batch))
        batches = VoucherBatch.objects.select_related("package", "created_by").order_by("-id")[:20]
        return Response([
            {"id": b.id, "package_name": b.package.name, "quantity": b.quantity,
             "created_at": b.created_at, "created_by": b.created_by.username}
            for b in batches
        ])

    def post(self, request):
        package = Package.objects.filter(pk=request.data.get("package"), is_active=True).first()
        try:
            quantity = int(request.data.get("quantity", 0))
        except (TypeError, ValueError):
            quantity = 0
        if not package or not 1 <= quantity <= 200:
            return Response({"detail": "Choose a package and a quantity from 1 to 200."}, status=400)
        batch = VoucherBatch.objects.create(package=package, quantity=quantity, created_by=request.user)
        create_vouchers(package, quantity, batch=batch)
        return Response(self._detail(batch), status=201)

    @staticmethod
    def _detail(batch):
        return {
            "id": batch.id,
            "package_name": batch.package.name,
            "duration_minutes": batch.package.duration_minutes,
            "price": float(batch.package.price),
            "created_at": batch.created_at,
            "codes": list(batch.vouchers.order_by("id").values_list("code", flat=True)),
        }


# ---- reports (owner only) -------------------------------------------------
def _rows(qs, key):
    return [{"label": r[key] or "-", "count": r["count"], "total": float(r["total"] or 0)} for r in qs]


class DailyReportView(APIView):
    permission_classes = [IsOwner]

    def get(self, request):
        day, start, end = day_bounds(request.query_params.get("date"))
        qs = Sale.objects.filter(sold_at__gte=start, sold_at__lt=end)
        agg = qs.aggregate(total=Sum("amount"), count=Count("id"))

        def group(**kw):
            return qs.values(**kw).annotate(count=Count("id"), total=Sum("amount")).order_by("-total")

        by_hour = {r["h"]: r for r in qs.annotate(h=ExtractHour("sold_at")).values("h")
                   .annotate(count=Count("id"), total=Sum("amount"))}
        hourly = [{"hour": h, "count": by_hour[h]["count"] if h in by_hour else 0,
                   "total": float(by_hour[h]["total"]) if h in by_hour else 0.0} for h in range(24)]

        methods = dict(Sale.Method.choices)
        by_method = _rows(group(label=F("method")), "label")
        for row in by_method:
            row["label"] = methods.get(row["label"], row["label"])

        return Response({
            "date": day.isoformat(),
            "total": float(agg["total"] or 0),
            "count": agg["count"],
            "by_package": _rows(group(label=F("voucher__package__name")), "label"),
            "by_method": by_method,
            "by_staff": _rows(group(label=F("sold_by__username")), "label"),
            "hourly": hourly,
            "active_now": Voucher.objects.filter(status=Voucher.Status.ACTIVE, expires_at__gt=timezone.now()).count(),
            "unused_sold": Voucher.objects.filter(status=Voucher.Status.UNUSED, sale__isnull=False).count(),
        })


class TrendReportView(APIView):
    permission_classes = [IsOwner]

    def get(self, request):
        try:
            days = min(max(int(request.query_params.get("days", 14)), 1), 90)
        except ValueError:
            days = 14
        today = timezone.localdate()
        first = today - timedelta(days=days - 1)
        _, start, _ = day_bounds(first.isoformat())
        rows = (Sale.objects.filter(sold_at__gte=start).annotate(d=TruncDate("sold_at"))
                .values("d").annotate(count=Count("id"), total=Sum("amount")))
        by_day = {r["d"]: r for r in rows}
        out = []
        for i in range(days):
            d = first + timedelta(days=i)
            r = by_day.get(d)
            out.append({"date": d.isoformat(), "count": r["count"] if r else 0,
                        "total": float(r["total"]) if r else 0.0})
        return Response(out)
