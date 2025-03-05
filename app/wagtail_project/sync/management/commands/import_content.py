import json
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.core import serializers
from wagtail.models import Page

from wagtail_project.sync.models import SyncLog, SyncedModel


class Command(BaseCommand):
    help = 'Import content from development instance'

    def add_arguments(self, parser):
        parser.add_argument('--sync_data', type=dict, help='Sync data as a dictionary')

    def handle(self, *args, **options):
        sync_data = options.get('sync_data')
        if not sync_data:
            self.stderr.write(self.style.ERROR('No sync data provided'))
            return
        
        # Check if this is a content sync
        if sync_data.get('sync_type') != 'content':
            self.stderr.write(self.style.ERROR(f'Invalid sync type: {sync_data.get("sync_type")}'))
            return
        
        # Create a local sync log
        sync_log = SyncLog.objects.create(
            sync_type='content',
            source_instance=sync_data.get('source_instance'),
            target_instance=settings.INSTANCE_TYPE,
            status='in_progress',
            message=f'Importing content from {sync_data.get("source_instance")}'
        )
        
        try:
            page_data = sync_data.get('page_data', [])
            self.stdout.write(self.style.NOTICE(f'Importing {len(page_data)} pages...'))
            
            # Statistics
            total_pages = 0
            skipped_pages = 0
            
            # Process each page
            for page_item in page_data:
                page_id = page_item.get('id')
                page_model = page_item.get('model')
                page_json = page_item.get('data')
                
                try:
                    # Check if the page exists
                    existing_page = Page.objects.filter(id=page_id).first()
                    
                    # Use a transaction for safety
                    with transaction.atomic():
                        if existing_page:
                            # Update the existing page
                            for obj in serializers.deserialize('json', json.dumps(page_json)):
                                updated_page = obj.object
                                # Copy the updated fields to the existing page
                                for field in updated_page._meta.fields:
                                    if field.name not in ['id', 'path', 'depth', 'numchild']:
                                        setattr(existing_page, field.name, getattr(updated_page, field.name))
                                existing_page.save()
                            total_pages += 1
                        else:
                            # Page doesn't exist, skip it
                            self.stdout.write(self.style.WARNING(f'Page {page_id} does not exist in the target instance'))
                            skipped_pages += 1
                
                except Exception as e:
                    self.stderr.write(self.style.WARNING(f'Error importing page {page_id}: {str(e)}'))
                    skipped_pages += 1
            
            # Update sync log
            sync_log.status = 'completed'
            sync_log.completed_at = timezone.now()
            sync_log.message = f'Content import completed successfully: {total_pages} pages imported, {skipped_pages} pages skipped'
            sync_log.save()
            
            # Add model statistics
            SyncedModel.objects.create(
                sync_log=sync_log,
                model_name='Pages',
                synced_items=total_pages,
                skipped_items=skipped_pages
            )
            
            self.stdout.write(self.style.SUCCESS('Content import completed successfully'))
            
        except Exception as e:
            # Update sync log with error
            sync_log.status = 'failed'
            sync_log.completed_at = timezone.now()
            sync_log.message = f'Error: {str(e)}'
            sync_log.save()
            
            self.stderr.write(self.style.ERROR(f'Error importing content: {str(e)}'))
