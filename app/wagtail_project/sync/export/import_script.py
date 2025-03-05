
import os
import sys
import json

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wagtail_project.settings.production')

import django
django.setup()

from django.core.management import call_command
from wagtail_project.sync.models import SyncLog, SyncedModel
from django.utils import timezone

def import_data():
    print("Importing sync data...")
    
    # Load the sync data
    with open('/app/wagtail_project/sync/export/sync_data.json', 'r') as f:
        sync_data = json.load(f)
    
    # Create a sync log
    sync_log = SyncLog.objects.create(
        sync_type='content',
        source_instance=sync_data.get('source_instance', 'unknown'),
        target_instance='production',
        status='in_progress'
    )
    
    try:
        # Import the content
        from wagtail_project.sync.management.commands.import_content import Command
        cmd = Command()
        cmd.handle(sync_data=sync_data)
        
        # Update the sync log
        sync_log.status = 'completed'
        sync_log.completed_at = timezone.now()
        sync_log.message = 'Content imported successfully'
        sync_log.save()
        
        print("Import completed successfully")
    except Exception as e:
        # Update the sync log with error
        sync_log.status = 'failed'
        sync_log.completed_at = timezone.now()
        sync_log.message = f'Error: {str(e)}'
        sync_log.save()
        
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    import_data()
