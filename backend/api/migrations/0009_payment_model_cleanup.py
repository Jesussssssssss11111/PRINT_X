from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_create_superuser'),
    ]

    operations = [
        # Step 1: Rename Order.date -> Order.created_at (was auto_now_add=True named 'date')
        migrations.RenameField(
            model_name='order',
            old_name='date',
            new_name='created_at',
        ),

        # Step 2: Create the Payment table
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('method', models.CharField(
                    max_length=20,
                    choices=[
                        ('gcash', 'GCash'),
                        ('maya', 'Maya'),
                        ('bank_transfer', 'Bank Transfer'),
                    ],
                )),
                ('amount', models.DecimalField(max_digits=10, decimal_places=2)),
                ('status', models.CharField(
                    max_length=10,
                    choices=[
                        ('pending', 'Pending'),
                        ('paid', 'Paid'),
                        ('failed', 'Failed'),
                    ],
                    default='pending',
                )),
                ('reference_number', models.CharField(max_length=255, blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('order', models.ForeignKey(
                    to='api.Order',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='payments',
                )),
            ],
        ),

        # Step 3: Remove old payment fields from Order (added in 0003 and 0005)
        migrations.RemoveField(model_name='order', name='payment_method'),
        migrations.RemoveField(model_name='order', name='reference_number'),
    ]
