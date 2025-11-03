"""
Simplified database models for FinSense.
No user authentication - assume single user.
"""
import uuid
from django.db import models
from django.db.models import Q
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
    title = models.TextField(default="New Chat")
    finished = models.BooleanField(default=True)
    root_message = models.ForeignKey(
        'ChatMessage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_root',
        help_text="Root message of the conversation chain"
    )
    
    objects = ChatWithContextManager()

    class Meta:
        verbose_name = "chat with context"
        verbose_name_plural = "chats with context"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Chat {self.id} - {self.title}"
    
    def get_message_chain(self):
        """Get all messages in order from root to latest."""
        if not self.root_message:
            return []
        
        messages = []
        current = self.root_message
        while current:
            messages.append(current)
            current = current.child_message
        return messages
    
    def get_latest_message(self):
        """Get the latest message in the chain."""
        if not self.root_message:
            return None
        
        current = self.root_message
        while current.child_message:
            current = current.child_message
        return current


class ChatMessageManager(models.Manager):
    """Custom Manager for ChatMessage."""
    
    def get_queryset(self):
        return super().get_queryset().select_related('chat', 'parent_message', 'child_message', 'root_message')


class ChatMessage(TimestampedUUIDModel):
    """Individual chat message with parent/child relationships for message chains."""
    
    # Chat relationship
    chat = models.ForeignKey(
        ChatWithContext,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text="Chat this message belongs to"
    )
    
    # Root message reference - points to the first message in this chain
    root_message = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='chain_messages',
        help_text="Reference to the root message of this conversation chain"
    )
    
    # Parent/child relationships for message chain
    parent_message = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='child_messages',
        help_text="Previous message in the chain"
    )
    
    child_message = models.OneToOneField(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='parent',
        help_text="Next message in the chain"
    )
    
    # Message content
    role = models.CharField(
        max_length=20,
        choices=[
            ('user', 'User'),
            ('assistant', 'Assistant'),
            ('tool', 'Tool'),
        ],
        help_text="Role of the message sender"
    )
    
    content_type = models.CharField(
        max_length=50,
        choices=[
            ('text', 'Text'),
            ('thought', 'Thought'),
            ('sources', 'Sources'),
            ('tool_use', 'Tool Use'),
            ('tool_result', 'Tool Result'),
            ('id', 'ID'),
            ('file_ids', 'File IDs'),
        ],
        default='text',
        help_text="Type of content"
    )
    
    content = models.TextField(
        help_text="Message content"
    )
    
    # Additional attributes
    context_collected = models.BooleanField(
        default=False,
        help_text="Whether context was collected for this message"
    )
    
    context_data = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text="Additional context data (screen content, etc.)"
    )
    
    metadata = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text="Additional metadata (tool_id, function_name, etc.)"
    )
    
    step_number = models.IntegerField(
        null=True,
        blank=True,
        help_text="Step number in multi-step conversation (for assistant messages)"
    )
    
    modality_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Modality type if this message triggered a modality (for assistant messages)"
    )
    
    is_final = models.BooleanField(
        default=False,
        help_text="Whether this is the final message in a conversation turn"
    )
    
    questions_asked = models.IntegerField(
        default=0,
        help_text="Number of questions asked in this message (for assistant messages)"
    )
    
    file_ids = models.JSONField(
        null=True,
        blank=True,
        default=list,
        help_text="List of file IDs (UUIDs) attached to this message"
    )
    
    objects = ChatMessageManager()

    class Meta:
        verbose_name = "chat message"
        verbose_name_plural = "chat messages"
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['chat', 'created_at']),
            models.Index(fields=['root_message', 'created_at']),
        ]

    def __str__(self):
        return f"Message {self.id} - {self.role} ({self.content_type})"
    
    def save(self, *args, **kwargs):
        """Override save to set root_message if this is the first message."""
        
        # If this is a new message and has no root_message set, set it to itself
        if not self.root_message:
            self.root_message = self
        
        super().save(*args, **kwargs)
        
        # Update parent's child_message reference if parent exists
        if self.parent_message:
            parent = ChatMessage.objects.get(pk=self.parent_message.pk)
            # Only update if parent doesn't already have a child_message set
            # (avoid unique constraint violation and preserve existing chain)
            if not parent.child_message:
                parent.child_message = self
                parent.save(update_fields=['child_message'])
        
        # Update chat's root_message if this is the first message
        if not self.chat.root_message:
            self.chat.root_message = self
            self.chat.save(update_fields=['root_message'])
    
    def get_chain_to_root(self):
        """Get all messages from this message back to root."""
        messages = []
        current = self
        while current:
            messages.insert(0, current)
            current = current.parent_message
        return messages
    
    def get_chain_from_root(self):
        """Get all messages from root to this message."""
        if not self.root_message:
            return [self]
        
        messages = []
        current = self.root_message
        while current and current.id != self.id:
            messages.append(current)
            current = current.child_message
        messages.append(self)
        return messages


class FileManager(models.Manager):
    """Custom Manager for File."""
    
    def get_queryset(self):
        return super().get_queryset()


class File(TimestampedUUIDModel):
    """File model for storing uploaded files."""
    
    class FileStatus(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        PENDING = "pending", "Pending"
    
    filename = models.CharField(max_length=512, help_text="Original filename")
    content_type = models.CharField(max_length=255, help_text="MIME type of the file")
    size = models.IntegerField(help_text="File size in bytes")
    file_key = models.CharField(max_length=512, help_text="S3 key or local file path")
    entity_id = models.CharField(max_length=255, null=True, blank=True, help_text="Related entity ID (e.g., chat_id)")
    entity = models.CharField(max_length=255, null=True, blank=True, help_text="Related entity type (e.g., 'chat')")
    last_accessed_at = models.DateTimeField(null=True, blank=True, help_text="Last time file was accessed")
    width = models.IntegerField(null=True, blank=True, help_text="Image width (if image)")
    height = models.IntegerField(null=True, blank=True, help_text="Image height (if image)")
    status = models.CharField(max_length=20, choices=FileStatus.choices, default=FileStatus.PENDING)
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="Soft delete timestamp")
    
    objects = FileManager()
    
    class Meta:
        verbose_name = "file"
        verbose_name_plural = "files"
        indexes = [
            models.Index(fields=['entity', 'entity_id']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"File {self.id} - {self.filename}"

