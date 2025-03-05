import os
import json
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
from django.core import serializers
from wagtail.models import Page

from wagtail_project.sync.models import SyncLog, SyncedModel


class Command(BaseCommand):
    help = 'Export selected content for sync to production'

    def add_arguments(self, parser):
        parser.add_argument('--sync_log_id', type=int, help='ID of the sync log')
        parser.add_argument('--page_ids', nargs='+', type=int, help='IDs of pages to sync')

    def handle(self, *args, **options):
        # Get the sync log
        sync_log_id = options.get('sync_log_id')
        if not sync_log_id:
            self.stderr.write(self.style.ERROR('No sync log ID provided'))
            return
        
        try:
            sync_log = SyncLog.objects.get(id=sync_log_id)
        except SyncLog.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'Sync log with ID {sync_log_id} does not exist'))
            return
        
        # Get the page IDs to sync
        page_ids = options.get('page_ids', [])
        if not page_ids:
            self.stderr.write(self.style.ERROR('No page IDs provided'))
            sync_log.status = 'failed'
            sync_log.completed_at = timezone.now()
            sync_log.message = 'No page IDs provided'
            sync_log.save()
            return
        
        # Update sync log status
        sync_log.status = 'in_progress'
        sync_log.save()
        
        try:
            self.stdout.write(self.style.NOTICE(f'Exporting content for {len(page_ids)} pages...'))
            
            # Get the pages and their related objects
            pages = Page.objects.filter(id__in=page_ids).specific()
            page_data = []
            
            # Statistics
            total_pages = 0
            skipped_pages = 0
            
            for page in pages:
                if page:
                    # Serialize the page
                    serialized_page = serializers.serialize('json', [page])
                    page_data.append({
                        'id': page.id,
                        'model': page._meta.label,
                        'data': json.loads(serialized_page)
                    })
                    total_pages += 1
                else:
                    skipped_pages += 1
            
            # Prepare data for sync
            sync_data = {
                'sync_type': 'content',
                'sync_log_id': sync_log.id,
                'source_instance': settings.INSTANCE_TYPE,
                'timestamp': timezone.now().isoformat(),
                'page_data': page_data
            }
            
            # Send to production instance
            self.stdout.write(self.style.NOTICE('Sending data to production instance...'))
            target_url = 'http://wagtail-prod:8000/sync/receive/' if settings.INSTANCE_TYPE == 'development' else 'http://wagtail-dev:8000/sync/receive/'
            
            self.stdout.write(self.style.NOTICE(f'Target URL: {target_url}'))
            
            response = requests.post(
                target_url,
                json=sync_data,
                headers={
                    'Content-Type': 'application/json',
                    'Host': 'wagtail-prod' if settings.INSTANCE_TYPE == 'development' else 'wagtail-dev',
                    'X-Sync-Source': settings.INSTANCE_TYPE
                },
                timeout=300  # 5 minute timeout for large data transfers
            )
            
            self.stdout.write(self.style.NOTICE(f'Response status: {response.status_code}'))
            self.stdout.write(self.style.NOTICE(f'Response text: {response.text}'))
            
            if response.status_code == 200:
                # Update sync log
                sync_log.status = 'completed'
                sync_log.completed_at = timezone.now()
                sync_log.message = 'Content sync completed successfully'
                sync_log.save()
                
                # Add model statistics
                SyncedModel.objects.create(
                    sync_log=sync_log,
                    model_name='Pages',
                    synced_items=total_pages,
                    skipped_items=skipped_pages
                )
                
                self.stdout.write(self.style.SUCCESS('Content sync completed successfully'))
            else:
                raise Exception(f'Error from production instance: {response.text}')
                
        except Exception as e:
            # Update sync log with error
            sync_log.status = 'failed'
            sync_log.completed_at = timezone.now()
            sync_log.message = f'Error: {str(e)}'
            sync_log.save()
            
            self.stderr.write(self.style.ERROR(f'Error exporting content: {str(e)}'))
