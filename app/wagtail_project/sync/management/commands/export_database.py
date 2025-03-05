import os
import json
import time
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
from django.db import connections, transaction

from wagtail_project.sync.models import SyncLog, SyncedModel


class Command(BaseCommand):
    help = 'Export entire database for sync to production'

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
            # Create a dump of the database
            dump_path = os.path.join(settings.BASE_DIR, 'tmp', f'db_dump_{sync_log.id}.json')
            os.makedirs(os.path.dirname(dump_path), exist_ok=True)
            
            self.stdout.write(self.style.NOTICE('Dumping database to JSON...'))
            
            # Use Django's dumpdata command to create a JSON dump of the database
            call_command('dumpdata', 
                         exclude=['contenttypes', 'auth.permission', 'sessions'], 
                         natural_foreign=True, 
                         natural_primary=True, 
                         output=dump_path)
            
            # Read the dump file
            with open(dump_path, 'r') as f:
                dump_data = json.load(f)
            
            # Prepare data for sync
            sync_data = {
                'sync_type': 'full',
                'sync_log_id': sync_log.id,
                'source_instance': settings.INSTANCE_TYPE,
                'timestamp': timezone.now().isoformat(),
                'dump_data': dump_data
            }
            
            # Send to production instance
            self.stdout.write(self.style.NOTICE('Sending data to production instance...'))
            target_url = 'http://wagtail-prod:8000/sync/receive/' if settings.INSTANCE_TYPE == 'development' else 'http://wagtail-dev:8000/sync/receive/'
            
            response = requests.post(
                target_url,
                json=sync_data,
                headers={'Content-Type': 'application/json'},
                timeout=300  # 5 minute timeout for large data transfers
            )
            
            if response.status_code == 200:
                # Clean up the dump file
                os.remove(dump_path)
                
                # Update sync log
                sync_log.status = 'completed'
                sync_log.completed_at = timezone.now()
                sync_log.message = 'Database sync completed successfully'
                sync_log.save()
                
                # Add model statistics
                SyncedModel.objects.create(
                    sync_log=sync_log,
                    model_name='Full Database',
                    synced_items=len(dump_data),
                    skipped_items=0
                )
                
                self.stdout.write(self.style.SUCCESS('Database sync completed successfully'))
            else:
                raise Exception(f'Error from production instance: {response.text}')
                
        except Exception as e:
            # Update sync log with error
            sync_log.status = 'failed'
            sync_log.completed_at = timezone.now()
            sync_log.message = f'Error: {str(e)}'
            sync_log.save()
            
            self.stderr.write(self.style.ERROR(f'Error exporting database: {str(e)}'))
