from django.conf import settings


def cafe(request):
    return {"CAFE_NAME": settings.CAFE_NAME, "CURRENCY": settings.CURRENCY_SYMBOL}
