# Generated by Django 3.2 on 2022-07-15 01:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0004_auto_20220715_0411'),
    ]

    operations = [
        migrations.RenameField(
            model_name='rule',
            old_name='wbs_code',
            new_name='name',
        ),
    ]
