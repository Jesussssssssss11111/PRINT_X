from django.core.management.base import BaseCommand
from api.models import Order


class Command(BaseCommand):
    help = 'Regenerate tracking IDs for orders with invalid or missing tracking IDs'

    def handle(self, *args, **options):
        orders = Order.objects.all()
        fixed_count = 0
        
        for order in orders:
            old_tracking_id = order.tracking_id
            # Check if tracking_id is empty or contains invalid characters
            if not old_tracking_id or len(old_tracking_id) != 16 or not old_tracking_id.replace('-', '').replace('_', '').isalnum():
                order.tracking_id = Order.generate_tracking_id()
                order.save()
                fixed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Fixed Order #{order.id}: {old_tracking_id} -> {order.tracking_id}')
                )
        
        if fixed_count == 0:
            self.stdout.write(self.style.SUCCESS('All tracking IDs are valid!'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Fixed {fixed_count} tracking IDs'))
