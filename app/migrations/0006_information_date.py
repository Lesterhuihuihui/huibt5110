# Generated by Django 3.2.8 on 2021-11-04 07:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0005_auto_20211104_1148'),
    ]

    operations = [
        migrations.AddField(
            model_name='information',
            name='date',
            field=models.ForeignKey(default='1', on_delete=django.db.models.deletion.CASCADE, to='app.date'),
            preserve_default=False,
        ),
    ]