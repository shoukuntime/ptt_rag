# Generated by Django 4.2.7 on 2025-04-11 10:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('log_app', '0002_alter_log_traceback'),
    ]

    operations = [
        migrations.RenameField(
            model_name='log',
            old_name='step',
            new_name='type',
        ),
    ]
