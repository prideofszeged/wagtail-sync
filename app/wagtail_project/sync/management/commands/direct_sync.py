import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from wagtail.models import Page
from wagtail_project.sync.models import SyncLog, SyncedModel

class Command(BaseCommand):
    help = 'Direct sync between instances using file-based approach'

    def add_arguments(self, parser):
        parser.add_argument('--import', dest='import_mode', action='store_true', help='Import mode')
        parser.add_argument('--page-ids', nargs='+', type=int, help='IDs of pages to sync')
        parser.add_argument('--export-file', type=str, default='sync_data.json', help='Export file name')

    def handle(self, *args, **options):
        import_mode = options.get('import_mode', False)
        
        if import_mode:
            self._handle_import()
        else:
            self._handle_export(options)
    
    def _handle_export(self, options):
        # Determine target instance
        target = 'production' if settings.INSTANCE_TYPE == 'development' else 'development'
        
        self.stdout.write(self.style.SUCCESS(f'Exporting content from {settings.INSTANCE_TYPE}...'))
        
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
                self.stdout.write(self.style.SUCCESS(f'Exporting {len(pages)} selected pages...'))
            else:
                # Get all pages except root
                pages = Page.objects.filter(depth__gt=1).specific()
                self.stdout.write(self.style.SUCCESS(f'Exporting all pages ({len(pages)} pages)...'))
            
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
            
            # Ensure export directory exists
            export_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'export')
            os.makedirs(export_dir, exist_ok=True)
            
            # Write data to file
            export_file = options.get('export_file', 'sync_data.json')
            export_path = os.path.join(export_dir, export_file)
            
            with open(export_path, 'w') as f:
                json.dump(sync_data, f, indent=2)
            
            # Update sync log
            sync_log.status = 'completed'
            sync_log.completed_at = timezone.now()
            sync_log.message = f'Successfully exported {len(pages)} pages to {export_path}'
            sync_log.save()
            
            # Add synced model statistics
            SyncedModel.objects.create(
                sync_log=sync_log,
                model_name='Pages',
                synced_items=len(pages),
                skipped_items=0
            )
            
            self.stdout.write(self.style.SUCCESS(f'Successfully exported {len(pages)} pages to {export_path}'))
        
        except Exception as e:
            # Update sync log with error
            sync_log.status = 'failed'
            sync_log.completed_at = timezone.now()
            sync_log.message = f'Error: {str(e)}'
            sync_log.save()
            
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
    
    def _handle_import(self):
        self.stdout.write(self.style.SUCCESS(f'Importing content to {settings.INSTANCE_TYPE}...'))
        
        # Create a sync log
        sync_log = SyncLog.objects.create(
            sync_type='content',
            source_instance='file',
            target_instance=settings.INSTANCE_TYPE,
            status='in_progress'
        )
        
        try:
            # Find the export file
            export_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'export')
            export_path = os.path.join(export_dir, 'sync_data.json')
            
            if not os.path.exists(export_path):
                raise FileNotFoundError(f'Export file not found: {export_path}')
            
            # Read data from file
            with open(export_path, 'r') as f:
                sync_data = json.load(f)
            
            # Import content
            from wagtail_project.sync.management.commands.import_content import Command
            cmd = Command()
            cmd.handle(sync_data=sync_data)
            
            # Update sync log
            sync_log.status = 'completed'
            sync_log.completed_at = timezone.now()
            sync_log.message = f'Successfully imported {len(sync_data.get("pages", []))} pages from {export_path}'
            sync_log.save()
            
            # Add synced model statistics
            SyncedModel.objects.create(
                sync_log=sync_log,
                model_name='Pages',
                synced_items=len(sync_data.get('pages', [])),
                skipped_items=0
            )
            
            self.stdout.write(self.style.SUCCESS(f'Successfully imported {len(sync_data.get("pages", []))} pages from {export_path}'))
        
        except Exception as e:
            # Update sync log with error
            sync_log.status = 'failed'
            sync_log.completed_at = timezone.now()
            sync_log.message = f'Error: {str(e)}'
            sync_log.save()
            
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}')) 