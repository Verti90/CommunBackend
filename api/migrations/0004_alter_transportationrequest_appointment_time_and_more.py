# Generated by Django 5.1.7 on 2025-05-17 22:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_alter_transportationrequest_pickup_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transportationrequest',
            name='appointment_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='transportationrequest',
            name='pickup_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
