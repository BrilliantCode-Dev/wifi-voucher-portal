from django.core.management.base import BaseCommand

from vouchers.services import expire_stale_vouchers


class Command(BaseCommand):
    help = "Cut off finished vouchers. Run this every minute (cron / Task Scheduler)."

    def handle(self, *args, **options):
        n = expire_stale_vouchers()
        self.stdout.write(f"Expired {n} voucher(s).")
