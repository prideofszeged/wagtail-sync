from django.db import models
from django.utils import timezone


class SyncLog(models.Model):
    """Log of sync operations between instances."""
    
    SYNC_TYPE_CHOICES = [
        ('full', 'Full Database Sync'),
        ('content', 'Content Sync'),
        ('media', 'Media Files Sync'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    sync_type = models.CharField(max_length=20, choices=SYNC_TYPE_CHOICES)
    source_instance = models.CharField(max_length=100)
    target_instance = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    message = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.sync_type} from {self.source_instance} to {self.target_instance} ({self.status})"
    
    class Meta:
        ordering = ['-started_at']


class SyncedModel(models.Model):
    """Details of models that have been synced."""
    
    sync_log = models.ForeignKey(SyncLog, on_delete=models.CASCADE, related_name='synced_models')
    model_name = models.CharField(max_length=100)
    synced_items = models.IntegerField(default=0)
    skipped_items = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.model_name} - {self.synced_items} synced, {self.skipped_items} skipped"
