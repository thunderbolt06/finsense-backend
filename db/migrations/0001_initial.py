# Generated migration for FinSense ChatWithContext model

from django.db import migrations, models
import uuid
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ChatWithContext',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('chat_history', models.TextField(default='[]')),
                ('title', models.TextField(default='New Chat')),
                ('finished', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'chat with context',
                'verbose_name_plural': 'chats with context',
                'ordering': ['-updated_at'],
            },
        ),
    ]

