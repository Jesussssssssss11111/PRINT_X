from django.db import migrations
from django.contrib.auth.hashers import make_password


def create_superuser(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    if not User.objects.filter(username='admin').exists():
        User.objects.create(
            username='admin',
            email='admin@printx.com',
            password=make_password('printx2024'),
            is_superuser=True,
            is_staff=True,
            is_active=True,
        )


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0005_alter_order_payment_method'),
    ]
    operations = [
        migrations.RunPython(create_superuser),
    ]
