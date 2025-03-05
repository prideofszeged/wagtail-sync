import json
import os
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from wagtail.admin.auth import require_admin_access
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.core.management import call_command
from django.db.models import Q
from wagtail.models import Page

from .models import SyncLog, SyncedModel
from django.views.decorators.csrf import csrf_exempt


@require_admin_access
def sync_dashboard(request):
    """Dashboard for sync operations."""
    logs = SyncLog.objects.all()[:10]
    
    return render(request, 'sync/dashboard.html', {
        'logs': logs,
        'instance_type': settings.INSTANCE_TYPE,
    })


@require_admin_access
def sync_content_form(request):
    """Form for selecting content to sync."""
    # Get all pages except root
    pages = Page.objects.filter(~Q(depth=1)).specific()
    
    return render(request, 'sync/content_form.html', {
        'pages': pages,
        'instance_type': settings.INSTANCE_TYPE,
    })


@require_admin_access
@require_POST
def trigger_sync(request):
    """Trigger a sync operation."""
    sync_type = request.POST.get('sync_type', 'content')
    
    # Create a new sync log
    sync_log = SyncLog.objects.create(
        sync_type=sync_type,
        source_instance=settings.INSTANCE_TYPE,
        target_instance='production' if settings.INSTANCE_TYPE == 'development' else 'development',
        status='in_progress'
    )
    
    if sync_type == 'full':
        # Call the management command
        call_command('export_database', sync_log_id=sync_log.id)
    elif sync_type == 'content':
        # Get selected pages
        page_ids = request.POST.getlist('page_ids')
        # Call the management command
        call_command('export_content', sync_log_id=sync_log.id, page_ids=page_ids)
    elif sync_type == 'media':
        # Call the management command
        call_command('export_media', sync_log_id=sync_log.id)
    
    return redirect('sync:dashboard')


@csrf_exempt
@require_POST
def receive_sync(request):
    """API endpoint to receive sync data."""
    import sys
    import traceback
    import tempfile
    
    print("==== SYNC RECEIVE DEBUG INFO ====")
    print(f"Instance type: {settings.INSTANCE_TYPE}")
    print(f"Request path: {request.path}")
    print(f"Request method: {request.method}")
    print(f"Request content type: {request.content_type}")
    print(f"Request headers: {dict(request.headers)}")
    
    # Create a sync log at the beginning
    sync_log = SyncLog.objects.create(
        sync_type='content',  # Default, will be updated
        source_instance='unknown',  # Will be updated
        target_instance=settings.INSTANCE_TYPE,
        status='in_progress'
    )
    
    # Process the sync data
    try:
        # Make sure we have a request body
        if not request.body:
            print("No request body received")
            sync_log.status = 'failed'
            sync_log.completed_at = timezone.now()
            sync_log.message = 'No data received'
            sync_log.save()
            return JsonResponse({'error': 'No data received'}, status=400)
        
        try:
            # Try to parse the JSON data
            print(f"Request body (first 500 chars): {request.body[:500]}")
            data = json.loads(request.body)
            print(f"Parsed data keys: {data.keys() if data else 'None'}")
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {str(e)}")
            sync_log.status = 'failed'
            sync_log.completed_at = timezone.now()
            sync_log.message = f'Invalid JSON: {str(e)}'
            sync_log.save()
            return JsonResponse({'error': f'Invalid JSON: {str(e)}'}, status=400)
        
        # Update sync log with actual data
        sync_type = data.get('sync_type', 'content')
        source_instance = data.get('source_instance', 'unknown')
        
        sync_log.sync_type = sync_type
        sync_log.source_instance = source_instance
        sync_log.save()
        
        print(f"Processing sync type: {sync_type} from {source_instance}")
        
        try:
            if sync_type == 'full':
                # Import the full database
                print("Importing full database")
                call_command('import_database', sync_data=data)
                
                # Update the sync log
                sync_log.status = 'completed'
                sync_log.completed_at = timezone.now()
                sync_log.message = 'Successfully imported full database'
                sync_log.save()
                
            elif sync_type == 'content':
                # Import content
                print("Importing content")
                
                # Write data to a temporary file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                    json.dump(data, temp_file)
                    temp_file_path = temp_file.name
                
                print(f"Wrote data to temporary file: {temp_file_path}")
                
                # Import the content using our import_content command
                from wagtail_project.sync.management.commands.import_content import Command
                cmd = Command()
                cmd.handle(file_path=temp_file_path)
                
                # Clean up the temporary file
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    print(f"Warning: Could not delete temporary file: {str(e)}")
                
                # Update the sync log
                pages_count = len(data.get("pages", []))
                sync_log.status = 'completed'
                sync_log.completed_at = timezone.now()
                sync_log.message = f'Successfully imported {pages_count} pages'
                sync_log.save()
                
                # Add synced model statistics
                SyncedModel.objects.create(
                    sync_log=sync_log,
                    model_name='Pages',
                    synced_items=pages_count,
                    skipped_items=0
                )
                
                print("Content import completed successfully")
                
            elif sync_type == 'media':
                # Import media
                print("Importing media")
                call_command('import_media', sync_data=data)
                
                # Update the sync log
                sync_log.status = 'completed'
                sync_log.completed_at = timezone.now()
                sync_log.message = 'Successfully imported media files'
                sync_log.save()
                
            else:
                print(f"Invalid sync type: {sync_type}")
                sync_log.status = 'failed'
                sync_log.completed_at = timezone.now()
                sync_log.message = f'Invalid sync type: {sync_type}'
                sync_log.save()
                return JsonResponse({'error': f'Invalid sync type: {sync_type}'}, status=400)
            
            print("Sync completed successfully")
            return JsonResponse({'status': 'success'})
            
        except Exception as cmd_error:
            print(f"Error in import command: {str(cmd_error)}")
            traceback.print_exc()
            
            # Update sync log with error
            sync_log.status = 'failed'
            sync_log.completed_at = timezone.now()
            sync_log.message = f'Error: {str(cmd_error)}'
            sync_log.save()
            
            return JsonResponse({'error': f'Command error: {str(cmd_error)}'}, status=500)
            
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print(f"Exception: {str(e)}")
        print("Traceback:")
        traceback.print_tb(exc_traceback)
        
        # Update sync log with error
        sync_log.status = 'failed'
        sync_log.completed_at = timezone.now()
        sync_log.message = f'Error: {str(e)}'
        sync_log.save()
        
        return JsonResponse({'error': str(e)}, status=500)


@require_admin_access
def sync_log_detail(request, log_id):
    """View details of a sync operation."""
    log = get_object_or_404(SyncLog, id=log_id)
    synced_models = log.synced_models.all()
    
    return render(request, 'sync/log_detail.html', {
        'log': log,
        'synced_models': synced_models,
    })


@csrf_exempt
@require_admin_access
def direct_sync(request):
    """Direct sync method using management commands."""
    if request.method == 'POST':
        action = request.POST.get('action', 'export')
        
        # Create a new sync log
        sync_log = SyncLog.objects.create(
            sync_type='content',
            source_instance=settings.INSTANCE_TYPE,
            target_instance='production' if settings.INSTANCE_TYPE == 'development' else 'development',
            status='in_progress'
        )
        
        try:
            if action == 'export':
                # Export content
                call_command('direct_sync')
            else:
                # Import content
                call_command('direct_sync', import_mode=True)
            
            # The direct_sync command will update the sync log, so we don't need to do it here
            return redirect('sync:dashboard')
        except Exception as e:
            # Update sync log with error
            sync_log.status = 'failed'
            sync_log.completed_at = timezone.now()
            sync_log.message = f'Error: {str(e)}'
            sync_log.save()
            
            return redirect('sync:dashboard')
    else:
        return render(request, 'sync/direct_sync.html', {
            'instance_type': settings.INSTANCE_TYPE,
        })


@require_admin_access
@require_POST
def file_sync_content(request):
    """Export selected content to a file for file-based sync."""
    # Get selected pages
    page_ids = request.POST.getlist('page_ids')
    
    if not page_ids:
        # Redirect back with an error message
        # In a real app, you'd use Django messages framework
        return redirect('sync:content_form')
    
    # Create a new sync log
    sync_log = SyncLog.objects.create(
        sync_type='content',
        source_instance=settings.INSTANCE_TYPE,
        target_instance='file',
        status='in_progress'
    )
    
    try:
        # Call the direct_sync command with selected pages
        call_command('direct_sync', page_ids=page_ids)
        
        # Update sync log
        sync_log.status = 'completed'
        sync_log.completed_at = timezone.now()
        sync_log.message = f'Successfully exported {len(page_ids)} pages to file'
        sync_log.save()
        
        # Add synced model statistics
        SyncedModel.objects.create(
            sync_log=sync_log,
            model_name='Pages',
            synced_items=len(page_ids),
            skipped_items=0
        )
        
        return redirect('sync:dashboard')
    except Exception as e:
        # Update sync log with error
        sync_log.status = 'failed'
        sync_log.completed_at = timezone.now()
        sync_log.message = f'Error: {str(e)}'
        sync_log.save()
        
        return redirect('sync:dashboard')
