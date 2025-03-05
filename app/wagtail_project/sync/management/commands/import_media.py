import os
import base64
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.files.base import ContentFile
from wagtail.images import get_image_model
from wagtail.documents import get_document_model

from wagtail_project.sync.models import SyncLog, SyncedModel


class Command(BaseCommand):
    help = 'Import media files from development instance'

    def add_arguments(self, parser):
        parser.add_argument('--sync_data', type=dict, help='Sync data as a dictionary')

    def handle(self, *args, **options):
        sync_data = options.get('sync_data')
        if not sync_data:
            self.stderr.write(self.style.ERROR('No sync data provided'))
            return
        
        # Check if this is a media sync
        if sync_data.get('sync_type') != 'media':
            self.stderr.write(self.style.ERROR(f'Invalid sync type: {sync_data.get("sync_type")}'))
            return
        
        # Create a local sync log
        sync_log = SyncLog.objects.create(
            sync_type='media',
            source_instance=sync_data.get('source_instance'),
            target_instance=settings.INSTANCE_TYPE,
            status='in_progress',
            message=f'Importing media from {sync_data.get("source_instance")}'
        )
        
        try:
            media_data = sync_data.get('media_data', [])
            self.stdout.write(self.style.NOTICE(f'Importing {len(media_data)} media files...'))
            
            # Get models
            Image = get_image_model()
            Document = get_document_model()
            
            # Statistics
            total_images = 0
            total_documents = 0
            skipped_items = 0
            
            # Process each media item
            for media_item in media_data:
                media_type = media_item.get('type')
                media_id = media_item.get('id')
                filename = media_item.get('filename')
                content_b64 = media_item.get('content')
                
                try:
                    # Decode base64 content
                    file_content = base64.b64decode(content_b64)
                    
                    if media_type == 'image':
                        # Check if the image exists
                        try:
                            image = Image.objects.get(id=media_id)
                            # Update existing image
                            image.file.save(filename, ContentFile(file_content), save=False)
                            image.save()
                            total_images += 1
                        except Image.DoesNotExist:
                            # Image doesn't exist in the target instance
                            self.stdout.write(self.style.WARNING(f'Image {media_id} does not exist in the target instance'))
                            skipped_items += 1
                    
                    elif media_type == 'document':
                        # Check if the document exists
                        try:
                            document = Document.objects.get(id=media_id)
                            # Update existing document
                            document.file.save(filename, ContentFile(file_content), save=False)
                            document.save()
                            total_documents += 1
                        except Document.DoesNotExist:
                            # Document doesn't exist in the target instance
                            self.stdout.write(self.style.WARNING(f'Document {media_id} does not exist in the target instance'))
                            skipped_items += 1
                    
                    else:
                        self.stdout.write(self.style.WARNING(f'Unknown media type: {media_type}'))
                        skipped_items += 1
                
                except Exception as e:
                    self.stderr.write(self.style.WARNING(f'Error importing media {media_id}: {str(e)}'))
                    skipped_items += 1
            
            # Update sync log
            sync_log.status = 'completed'
            sync_log.completed_at = timezone.now()
            sync_log.message = f'Media import completed successfully: {total_images} images, {total_documents} documents'
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
            
            self.stdout.write(self.style.SUCCESS('Media import completed successfully'))
            
        except Exception as e:
            # Update sync log with error
            sync_log.status = 'failed'
            sync_log.completed_at = timezone.now()
            sync_log.message = f'Error: {str(e)}'
            sync_log.save()
            
            self.stderr.write(self.style.ERROR(f'Error importing media: {str(e)}'))
