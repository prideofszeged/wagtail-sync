import os
import shutil
import json
import base64
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from wagtail.images import get_image_model
from wagtail.documents import get_document_model

from wagtail_project.sync.models import SyncLog, SyncedModel


class Command(BaseCommand):
    help = 'Export media files for sync to production'

    def add_arguments(self, parser):
        parser.add_argument('--sync_log_id', type=int, help='ID of the sync log')

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
        
        # Update sync log status
        sync_log.status = 'in_progress'
        sync_log.save()
        
        try:
            self.stdout.write(self.style.NOTICE('Exporting media files...'))
            
            # Get all images and documents
            Image = get_image_model()
            Document = get_document_model()
            
            images = Image.objects.all()
            documents = Document.objects.all()
            
            # Statistics
            total_images = 0
            total_documents = 0
            skipped_items = 0
            
            # Prepare media data
            media_data = []
            
            # Process images
            for image in images:
                try:
                    if not image.file:
                        skipped_items += 1
                        continue
                    
                    file_path = image.file.path
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            file_content = f.read()
                        
                        # Encode file content as base64
                        file_content_b64 = base64.b64encode(file_content).decode('utf-8')
                        
                        media_data.append({
                            'type': 'image',
                            'id': image.id,
                            'filename': os.path.basename(file_path),
                            'content': file_content_b64
                        })
                        
                        total_images += 1
                    else:
                        skipped_items += 1
                except Exception as e:
                    self.stderr.write(self.style.WARNING(f'Error processing image {image.id}: {str(e)}'))
                    skipped_items += 1
            
            # Process documents
            for document in documents:
                try:
                    if not document.file:
                        skipped_items += 1
                        continue
                    
                    file_path = document.file.path
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            file_content = f.read()
                        
                        # Encode file content as base64
                        file_content_b64 = base64.b64encode(file_content).decode('utf-8')
                        
                        media_data.append({
                            'type': 'document',
                            'id': document.id,
                            'filename': os.path.basename(file_path),
                            'content': file_content_b64
                        })
                        
                        total_documents += 1
                    else:
                        skipped_items += 1
                except Exception as e:
                    self.stderr.write(self.style.WARNING(f'Error processing document {document.id}: {str(e)}'))
                    skipped_items += 1
            
            # Prepare data for sync
            sync_data = {
                'sync_type': 'media',
                'sync_log_id': sync_log.id,
                'source_instance': settings.INSTANCE_TYPE,
                'timestamp': timezone.now().isoformat(),
                'media_data': media_data
            }
            
            # Send to production instance
            self.stdout.write(self.style.NOTICE('Sending media data to production instance...'))
            target_url = 'http://wagtail-prod:8000/sync/receive/' if settings.INSTANCE_TYPE == 'development' else 'http://wagtail-dev:8000/sync/receive/'
            
            response = requests.post(
                target_url,
                json=sync_data,
                headers={'Content-Type': 'application/json'},
                timeout=600  # 10 minute timeout for large data transfers
            )
            
            if response.status_code == 200:
                # Update sync log
                sync_log.status = 'completed'
                sync_log.completed_at = timezone.now()
                sync_log.message = 'Media sync completed successfully'
                sync_log.save()
                
                # Add model statistics
                SyncedModel.objects.create(
                    sync_log=sync_log,
                    model_name='Images',
                    synced_items=total_images,
                    skipped_items=0
                )
                
                SyncedModel.objects.create(
                    sync_log=sync_log,
                    model_name='Documents',
                    synced_items=total_documents,
                    skipped_items=0
                )
                
                SyncedModel.objects.create(
                    sync_log=sync_log,
                    model_name='Skipped Media',
                    synced_items=0,
                    skipped_items=skipped_items
                )
                
                self.stdout.write(self.style.SUCCESS('Media sync completed successfully'))
            else:
                raise Exception(f'Error from production instance: {response.text}')
                
        except Exception as e:
            # Update sync log with error
            sync_log.status = 'failed'
            sync_log.completed_at = timezone.now()
            sync_log.message = f'Error: {str(e)}'
            sync_log.save()
            
            self.stderr.write(self.style.ERROR(f'Error exporting media: {str(e)}'))
