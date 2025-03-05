import json
import os
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.core.management import call_command
from django.db.models import Q
from wagtail.models import Page

from .models import SyncLog, SyncedModel


@login_required
def sync_dashboard(request):
    """Dashboard for sync operations."""
    logs = SyncLog.objects.all()[:10]
    
    return render(request, 'sync/dashboard.html', {
        'logs': logs,
        'instance_type': settings.INSTANCE_TYPE,
    })


@login_required
def sync_content_form(request):
    """Form for selecting content to sync."""
    # Get all pages except root
    pages = Page.objects.filter(~Q(depth=1)).specific()
    
    return render(request, 'sync/content_form.html', {
        'pages': pages,
        'instance_type': settings.INSTANCE_TYPE,
    })


@login_required
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
    # Check if this is the target instance
    if settings.INSTANCE_TYPE == 'development':
        return JsonResponse({'error': 'Cannot sync to development instance'}, status=400)
    
    # Process the sync data
    try:
        data = json.loads(request.body)
        sync_type = data.get('sync_type')
        
        if sync_type == 'full':
            # Import the full database
            call_command('import_database', sync_data=data)
        elif sync_type == 'content':
            # Import content
            call_command('import_content', sync_data=data)
        elif sync_type == 'media':
            # Import media
            call_command('import_media', sync_data=data)
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def sync_log_detail(request, log_id):
    """View details of a sync operation."""
    log = get_object_or_404(SyncLog, id=log_id)
    synced_models = log.synced_models.all()
    
    return render(request, 'sync/log_detail.html', {
        'log': log,
        'synced_models': synced_models,
    })
