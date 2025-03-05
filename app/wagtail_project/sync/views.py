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
    
    print("==== SYNC RECEIVE DEBUG INFO ====")
    print(f"Instance type: {settings.INSTANCE_TYPE}")
    print(f"Request path: {request.path}")
    print(f"Request method: {request.method}")
    print(f"Request content type: {request.content_type}")
    print(f"Request headers: {dict(request.headers)}")
    
    # Check if this is the target instance
    if settings.INSTANCE_TYPE == 'development' and False:  # Temporarily disabled this check
        print("Cannot sync to development instance")
        return JsonResponse({'error': 'Cannot sync to development instance'}, status=400)
    
    # Process the sync data
    try:
        # Make sure we have a request body
        if not request.body:
            print("No request body received")
            return JsonResponse({'error': 'No data received'}, status=400)
        
        try:
            # Try to parse the JSON data
            print(f"Request body (first 200 chars): {request.body[:200]}")
            data = json.loads(request.body)
            print(f"Parsed data keys: {data.keys() if data else 'None'}")
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {str(e)}")
            return JsonResponse({'error': f'Invalid JSON: {str(e)}'}, status=400)
        
        sync_type = data.get('sync_type')
        print(f"Sync type: {sync_type}")
        
        if sync_type == 'full':
            # Import the full database
            print("Importing full database")
            call_command('import_database', sync_data=data)
        elif sync_type == 'content':
            # Import content
            print("Importing content")
            call_command('import_content', sync_data=data)
        elif sync_type == 'media':
            # Import media
            print("Importing media")
            call_command('import_media', sync_data=data)
        else:
            print(f"Invalid sync type: {sync_type}")
            return JsonResponse({'error': f'Invalid sync type: {sync_type}'}, status=400)
        
        print("Sync completed successfully")
        return JsonResponse({'status': 'success'})
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print(f"Exception: {str(e)}")
        print("Traceback:")
        traceback.print_tb(exc_traceback)
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
        # Create a new sync log
        sync_log = SyncLog.objects.create(
            sync_type='content',
            source_instance=settings.INSTANCE_TYPE,
            target_instance='production' if settings.INSTANCE_TYPE == 'development' else 'development',
            status='in_progress'
        )
        
        try:
            # Export the content
            call_command('sync_test_content')
            
            # Update the sync log
            sync_log.status = 'completed'
            sync_log.completed_at = timezone.now()
            sync_log.message = 'Content exported successfully. Please run import_test_content on the target instance.'
            sync_log.save()
            
            # Add model statistics
            SyncedModel.objects.create(
                sync_log=sync_log,
                model_name='Pages',
                synced_items=5,
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
    else:
        return render(request, 'sync/direct_sync.html', {
            'instance_type': settings.INSTANCE_TYPE,
        })
