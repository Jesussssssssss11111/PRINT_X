from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_order_payment_customrequest_stl'),
    ]

    operations = [
        # Add printing / ready / completed statuses to CustomRequest
        migrations.AlterField(
            model_name='customrequest',
            name='status',
            field=models.CharField(
                max_length=20,
                default='pending',
                choices=[
                    ('pending',   'Pending'),
                    ('reviewing', 'Reviewing'),
                    ('approved',  'Approved'),
                    ('printing',  'Printing'),
                    ('ready',     'Ready'),
                    ('completed', 'Completed'),
                    ('cancelled', 'Cancelled'),
                ],
            ),
        ),
        # Add notes field to Order
        migrations.AddField(
            model_name='order',
            name='notes',
            field=models.TextField(blank=True, default=''),
        ),
    ]
