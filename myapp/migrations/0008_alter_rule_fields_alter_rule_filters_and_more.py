# Generated by Django 4.1.3 on 2023-02-16 13:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0007_alter_wbs_specs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rule',
            name='fields',
            field=models.TextField(blank=True, max_length=999),
        ),
        migrations.AlterField(
            model_name='rule',
            name='filters',
            field=models.TextField(blank=True, max_length=999),
        ),
        migrations.AlterField(
            model_name='rule',
            name='group_by',
            field=models.TextField(blank=True, max_length=999),
        ),
        migrations.AlterField(
            model_name='rule',
            name='name',
            field=models.TextField(blank=True, max_length=99),
        ),
        migrations.AlterField(
            model_name='rule',
            name='names',
            field=models.TextField(blank=True, max_length=999),
        ),
        migrations.AlterField(
            model_name='rule',
            name='operations',
            field=models.TextField(blank=True, max_length=9999),
        ),
        migrations.AlterField(
            model_name='rule',
            name='sum_by',
            field=models.TextField(blank=True, max_length=999),
        ),
        migrations.AlterField(
            model_name='rule',
            name='unique_name',
            field=models.TextField(blank=True, max_length=100),
        ),
    ]