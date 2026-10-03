from django.shortcuts import render

from vouchers.models import Package

from .models import Service, SiteInfo


def index(request):
    return render(request, "website/index.html", {
        "info": SiteInfo.objects.first() or SiteInfo(),
        "services": Service.objects.filter(is_active=True),
        "packages": Package.objects.filter(is_active=True),
    })
