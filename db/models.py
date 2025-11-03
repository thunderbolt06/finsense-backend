"""
Simplified database models for FinSense.
No user authentication - assume single user.
"""
import uuid
from django.db import models
from django.utils import timezone


class TimestampedUUIDModel(models.Model):
    """Base model with UUID primary key and timestamps."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, null=False, unique=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ChatWithContextManager(models.Manager):
    """Custom Manager for ChatWithContext."""

    def get_queryset(self):
        return super().get_queryset()


class ChatWithContext(TimestampedUUIDModel):
    """Simplified chat model - no user FK, assumes single user."""
    chat_history = models.TextField(default="[]")  # JSON string
    title = models.TextField(default="New Chat")
    finished = models.BooleanField(default=True)
    
    objects = ChatWithContextManager()

    class Meta:
        verbose_name = "chat with context"
        verbose_name_plural = "chats with context"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Chat {self.id} - {self.title}"

