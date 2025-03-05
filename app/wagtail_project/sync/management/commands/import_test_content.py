import json
import os
from django.core.management.base import BaseCommand
from django.core.serializers import deserialize
from django.db import transaction
from wagtail.models import Page
from wagtail.images.models import Image
from wagtail.documents.models import Document
from wagtail_project.home.models import HomePage

class Command(BaseCommand):
    help = 'Import test content from export files'

    def handle(self, *args, **options):
        # Find the export directory
        export_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'export')
        
        if not os.path.exists(export_dir):
            self.stdout.write(self.style.ERROR(f'Export directory not found: {export_dir}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Importing content from {export_dir}...'))
        
        # Import pages
        pages_file = os.path.join(export_dir, 'pages.json')
        if os.path.exists(pages_file):
            with open(pages_file, 'r') as f:
                pages_data = f.read()
            
            # Import the pages
            with transaction.atomic():
                for obj in deserialize('json', pages_data):
                    if isinstance(obj.object, HomePage):
                        page_title = obj.object.title
                        page_slug = obj.object.slug
                        
                        # Check if the page already exists
                        existing_pages = HomePage.objects.filter(slug=page_slug)
                        if existing_pages.exists():
                            # Update existing page
                            existing_page = existing_pages.first()
                            # Make sure the page has content
                            if hasattr(obj.object, 'body') and obj.object.body:
                                existing_page.body = obj.object.body
                                existing_page.save()
                                self.stdout.write(self.style.SUCCESS(f'Updated page: {page_title}'))
                            else:
                                self.stdout.write(self.style.WARNING(f'Page has no body content: {page_title}'))
                        else:
                            # Create a new page if it doesn't exist
                            try:
                                # Find the root page
                                root_page = Page.objects.get(id=1)
                                
                                # Create a new home page
                                new_page = HomePage(
                                    title=page_title,
                                    slug=page_slug,
                                    body=obj.object.body if hasattr(obj.object, 'body') else "<p>Imported content</p>"
                                )
                                
                                root_page.add_child(instance=new_page)
                                new_page.save_revision().publish()
                                self.stdout.write(self.style.SUCCESS(f'Created page: {page_title}'))
                            except Exception as e:
                                self.stdout.write(self.style.ERROR(f'Error creating page {page_title}: {str(e)}'))
            
            self.stdout.write(self.style.SUCCESS(f'Pages imported from {pages_file}'))
        
        # Import images
        images_file = os.path.join(export_dir, 'images.json')
        if os.path.exists(images_file):
            with open(images_file, 'r') as f:
                images_data = f.read()
            
            # Import the images
            with transaction.atomic():
                for obj in deserialize('json', images_data):
                    if isinstance(obj.object, Image):
                        # Check if the image already exists
                        try:
                            existing_image = Image.objects.get(title=obj.object.title)
                            self.stdout.write(self.style.SUCCESS(f'Image already exists: {obj.object.title}'))
                        except Image.DoesNotExist:
                            try:
                                obj.save()
                                self.stdout.write(self.style.SUCCESS(f'Created image: {obj.object.title}'))
                            except Exception as e:
                                self.stdout.write(self.style.ERROR(f'Error importing image {obj.object.title}: {str(e)}'))
            
            self.stdout.write(self.style.SUCCESS(f'Images imported from {images_file}'))
        
        # Import documents
        documents_file = os.path.join(export_dir, 'documents.json')
        if os.path.exists(documents_file):
            with open(documents_file, 'r') as f:
                documents_data = f.read()
            
            # Import the documents
            with transaction.atomic():
                for obj in deserialize('json', documents_data):
                    if isinstance(obj.object, Document):
                        # Check if the document already exists
                        try:
                            existing_document = Document.objects.get(title=obj.object.title)
                            self.stdout.write(self.style.SUCCESS(f'Document already exists: {obj.object.title}'))
                        except Document.DoesNotExist:
                            try:
                                obj.save()
                                self.stdout.write(self.style.SUCCESS(f'Created document: {obj.object.title}'))
                            except Exception as e:
                                self.stdout.write(self.style.ERROR(f'Error importing document {obj.object.title}: {str(e)}'))
            
            self.stdout.write(self.style.SUCCESS(f'Documents imported from {documents_file}'))
        
        self.stdout.write(self.style.SUCCESS('Content import completed'))
