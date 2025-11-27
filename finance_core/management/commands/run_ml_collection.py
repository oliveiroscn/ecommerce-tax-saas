from django.core.management.base import BaseCommand
from finance_core.utils import fetch_and_process_ml_orders

class Command(BaseCommand):
    help = 'Fetches sales data from Mercado Livre for all tenants'

    def handle(self, *args, **options):
        self.stdout.write("Starting ML Sales Collection...")
        fetch_and_process_ml_orders()
        self.stdout.write(self.style.SUCCESS("ML Sales Collection Completed."))
