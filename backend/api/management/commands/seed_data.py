from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import Product

class Command(BaseCommand):
    help = 'Seed database with sample data'

    def handle(self, *args, **options):
        # Create users
        if not User.objects.filter(username='testuser').exists():
            user = User.objects.create_user('testuser', 'test@test.com', 'testpass123')
            user.first_name = 'Test'
            user.last_name = 'User'
            user.save()
            self.stdout.write(self.style.SUCCESS('Created test user'))

        # Create products
        if not Product.objects.exists():
            products = [
                {'name': 'Keychain', 'price': 50, 'description': 'Customizable keychain', 'stock': 100},
                {'name': 'Phone Stand', 'price': 150, 'description': 'Desk phone holder', 'stock': 50},
                {'name': 'Mini Figure', 'price': 200, 'description': '3D printed figurine', 'stock': 30},
            ]
            for p in products:
                Product.objects.create(**p)
            self.stdout.write(self.style.SUCCESS('Created sample products'))
        self.stdout.write(self.style.SUCCESS('Database seeded'))

