from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_alter_order_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_method',
            field=models.CharField(default='cod', max_length=50),
        ),
        migrations.AddField(
            model_name='order',
            name='reference_number',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='customrequest',
            name='stl_file',
            field=models.FileField(blank=True, null=True, upload_to='stl_files/'),
        ),
    ]
