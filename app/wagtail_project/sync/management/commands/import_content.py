import json
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.core import serializers
from wagtail.models import Page
from django.utils.text import slugify
from wagtail_project.sync.models import SyncLog, SyncedModel


class Command(BaseCommand):
    help = 'Import content from another instance'

    def add_arguments(self, parser):
        parser.add_argument('--sync-data', type=dict, help='JSON data to import as a dictionary')

    def handle(self, *args, **options):
        sync_data = options.get('sync_data')
        
        if not sync_data:
            self.stdout.write(self.style.ERROR('No sync data provided'))
            return
        
        # Create a sync log
        sync_log = SyncLog.objects.create(
            sync_type='content',
            source_instance=sync_data.get('source_instance', 'unknown'),
            target_instance='current',
            status='in_progress'
        )
        
        try:
            # Get pages from sync data
            pages_data = sync_data.get('pages', [])
            
            if not pages_data:
                self.stdout.write(self.style.WARNING('No pages found in sync data'))
                sync_log.status = 'completed'
                sync_log.completed_at = timezone.now()
                sync_log.message = 'No pages found in sync data'
                sync_log.save()
                return
            
            # Import pages
            imported_count = 0
            skipped_count = 0
            
            with transaction.atomic():
                for page_data in pages_data:
                    try:
                        # Get page details
                        page_id = page_data.get('id')
                        page_title = page_data.get('title')
                        page_slug = page_data.get('slug')
                        page_content_type = page_data.get('content_type')
                        page_path = page_data.get('path')
                        page_depth = page_data.get('depth')
                        page_body = page_data.get('body')
                        
                        # Check if page already exists
                        try:
                            existing_page = Page.objects.get(slug=page_slug)
                            # Update existing page
                            specific_page = existing_page.specific
                            
                            # Update page content if body is available
                            if page_body and hasattr(specific_page, 'body'):
                                specific_page.body = page_body
                                specific_page.save()
                                
                                self.stdout.write(self.style.SUCCESS(f'Updated page: {page_title}'))
                                imported_count += 1
                            else:
                                self.stdout.write(self.style.WARNING(f'Page has no body content or body field: {page_title}'))
                                skipped_count += 1
                        except Page.DoesNotExist:
                            # Find parent page based on depth
                            if page_depth == 2:
                                # This is a top-level page, parent is root
                                parent_page = Page.objects.get(id=1)
                            else:
                                # Try to find parent based on path
                                parent_path = page_path[:-4]  # Remove last 4 chars which is the page's own id
                                try:
                                    parent_page = Page.objects.get(path=parent_path)
                                except Page.DoesNotExist:
                                    # Default to root if parent not found
                                    parent_page = Page.objects.get(id=1)
                            
                            # Create new page based on content type
                            # This is a simplified version - in a real app, you'd need to handle different page types
                            from wagtail_project.home.models import HomePage
                            
                            if page_content_type == 'HomePage':
                                new_page = HomePage(
                                    title=page_title,
                                    slug=page_slug,
                                    body=page_body if page_body else "<p>Imported content</p>"
                                )
                                
                                parent_page.add_child(instance=new_page)
                                new_page.save_revision().publish()
                                
                                self.stdout.write(self.style.SUCCESS(f'Created page: {page_title}'))
                                imported_count += 1
                            else:
                                self.stdout.write(self.style.WARNING(f'Unknown page type: {page_content_type}'))
                                skipped_count += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Error importing page {page_data.get("title")}: {str(e)}'))
                        skipped_count += 1
            
            # Update sync log
            sync_log.status = 'completed'
            sync_log.completed_at = timezone.now()
            sync_log.message = f'Imported {imported_count} pages, skipped {skipped_count} pages'
            sync_log.save()
            
            # Add synced model statistics
            SyncedModel.objects.create(
                sync_log=sync_log,
                model_name='Pages',
                synced_items=imported_count,
                skipped_items=skipped_count
            )
            
            self.stdout.write(self.style.SUCCESS(f'Imported {imported_count} pages, skipped {skipped_count} pages'))
        
        except Exception as e:
            # Update sync log with error
            sync_log.status = 'failed'
            sync_log.completed_at = timezone.now()
            sync_log.message = f'Error: {str(e)}'
            sync_log.save()
            
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
