# Generated by Django 4.2.4 on 2023-08-05 20:56

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('etl', '0002_workimport_allow_anon_comments_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ObjectMapping',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('uid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('import_type', models.CharField(choices=[('ao3', 'ao3')], max_length=100)),
                ('object_type', models.CharField(choices=[('work', 'work'), ('chapter', 'chapter')], max_length=100)),
                ('origin_field', models.CharField(max_length=100)),
                ('destination_field', models.CharField(max_length=100)),
            ],
        ),
        migrations.RemoveField(
            model_name='workimport',
            name='mode',
        ),
    ]
