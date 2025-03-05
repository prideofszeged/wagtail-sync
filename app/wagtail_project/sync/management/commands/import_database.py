import os
import json
import tempfile
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
from django.db import connections, transaction

from wagtail_project.sync.models import SyncLog, SyncedModel


class Command(BaseCommand):
    help = 'Import entire database from development instance'

    def add_arguments(self, parser):
        parser.add_argument('--sync_data', type=dict, help='Sync data as a dictionary')

    def handle(self, *args, **options):
        sync_data = options.get('sync_data')
        if not sync_data:
            self.stderr.write(self.style.ERROR('No sync data provided'))
            return
        
        # Check if this is a full database sync
        if sync_data.get('sync_type') != 'full':
            self.stderr.write(self.style.ERROR(f'Invalid sync type: {sync_data.get("sync_type")}'))
            return
        
        # Create a local sync log
        sync_log = SyncLog.objects.create(
            sync_type='full',
            source_instance=sync_data.get('source_instance'),
            target_instance=settings.INSTANCE_TYPE,
            status='in_progress',
            message=f'Importing database from {sync_data.get("source_instance")}'
        )
        
        try:
            # Write the dump data to a temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                dump_path = temp_file.name
                json.dump(sync_data.get('dump_data'), temp_file)
            
            self.stdout.write(self.style.NOTICE('Clearing database...'))
            
            # Use a transaction for safety
            with transaction.atomic():
                # Flush the database (except for contenttypes, auth.permissions, and sessions)
                call_command('flush', interactive=False)
                
                # Load the data from the dump file
                self.stdout.write(self.style.NOTICE('Loading data from dump file...'))
                call_command('loaddata', dump_path)
            
            # Clean up the temporary file
            os.unlink(dump_path)
            
            # Update sync log
            sync_log.status = 'completed'
            sync_log.completed_at = timezone.now()
            sync_log.message = 'Database import completed successfully'
            sync_log.save()
            
            # Add model statistics
            SyncedModel.objects.create(
                sync_log=sync_log,
                model_name='Full Database',
                synced_items=len(sync_data.get('dump_data')),
                skipped_items=0
            )
            
            self.stdout.write(self.style.SUCCESS('Database import completed successfully'))
            
        except Exception as e:
            # Update sync log with error
            sync_log.status = 'failed'
            sync_log.completed_at = timezone.now()
            sync_log.message = f'Error: {str(e)}'
            sync_log.save()
            
            # Clean up temporary file if it exists
            if 'dump_path' in locals() and os.path.exists(dump_path):
                os.unlink(dump_path)
                
            self.stderr.write(self.style.ERROR(f'Error importing database: {str(e)}'))
