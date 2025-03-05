import json
import os
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from wagtail.models import Page
from wagtail_project.sync.models import SyncLog, SyncedModel

class Command(BaseCommand):
    help = 'Sync content between instances'

    def add_arguments(self, parser):
        parser.add_argument('--target', type=str, default='auto', help='Target instance (production or development)')
        parser.add_argument('--page-ids', nargs='+', type=int, help='IDs of pages to sync')

    def handle(self, *args, **options):
        # Determine target instance
        target = options.get('target')
        if target == 'auto':
            target = 'production' if settings.INSTANCE_TYPE == 'development' else 'development'
        
        self.stdout.write(self.style.SUCCESS(f'Syncing content from {settings.INSTANCE_TYPE} to {target}...'))
        
        # Create a sync log
        sync_log = SyncLog.objects.create(
            sync_type='content',
            source_instance=settings.INSTANCE_TYPE,
            target_instance=target,
            status='in_progress'
        )
        
        try:
            # Get pages to sync
            page_ids = options.get('page_ids')
            if page_ids:
                pages = Page.objects.filter(id__in=page_ids).specific()
            else:
                # Get all pages except root
                pages = Page.objects.filter(depth__gt=1).specific()
            
            # Prepare data for sync
            sync_data = {
                'sync_type': 'content',
                'source_instance': settings.INSTANCE_TYPE,
                'pages': []
            }
            
            # Add page data
            for page in pages:
                page_data = {
                    'id': page.id,
                    'title': page.title,
                    'slug': page.slug,
                    'content_type': page.specific_class.__name__,
                    'path': page.path,
                    'depth': page.depth,
                    'numchild': page.numchild,
                    'url_path': page.url_path,
                }
                
                # Add page-specific fields if available
                if hasattr(page, 'body'):
                    page_data['body'] = page.body
                
                sync_data['pages'].append(page_data)
            
            # Determine target URL
            if target == 'production':
                target_url = 'http://wagtail-prod:8000/sync/receive/'
            else:
                target_url = 'http://wagtail-dev:8000/sync/receive/'
            
            # Send data to target instance
            self.stdout.write(self.style.SUCCESS(f'Sending data to {target_url}...'))
            response = requests.post(
                target_url,
                json=sync_data,
                headers={'Content-Type': 'application/json'}
            )
            
            # Check response
            if response.status_code == 200:
                # Update sync log
                sync_log.status = 'completed'
                sync_log.completed_at = timezone.now()
                sync_log.message = f'Successfully synced {len(pages)} pages to {target}'
                sync_log.save()
                
                # Add synced model statistics
                SyncedModel.objects.create(
                    sync_log=sync_log,
                    model_name='Pages',
                    synced_items=len(pages),
                    skipped_items=0
                )
                
                self.stdout.write(self.style.SUCCESS(f'Successfully synced {len(pages)} pages to {target}'))
            else:
                # Update sync log with error
                sync_log.status = 'failed'
                sync_log.completed_at = timezone.now()
                sync_log.message = f'Error from target: {response.text}'
                sync_log.save()
                
                self.stdout.write(self.style.ERROR(f'Error from target: {response.text}'))
        
        except Exception as e:
            # Update sync log with error
            sync_log.status = 'failed'
            sync_log.completed_at = timezone.now()
            sync_log.message = f'Error: {str(e)}'
            sync_log.save()
            
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}')) 