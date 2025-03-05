import json
import os
from django.core.management.base import BaseCommand
from django.core.serializers import serialize
from wagtail.models import Page
from wagtail.images.models import Image
from wagtail.documents.models import Document
from wagtail_project.home.models import HomePage

class Command(BaseCommand):
    help = 'Sync test content from dev to prod'

    def add_arguments(self, parser):
        parser.add_argument('--target', type=str, default='prod', help='Target instance (prod or dev)')

    def handle(self, *args, **options):
        target = options.get('target')
        
        self.stdout.write(self.style.SUCCESS(f'Syncing test content to {target}...'))
        
        # Create a directory to store the exported content
        export_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'export')
        os.makedirs(export_dir, exist_ok=True)
        
        # Export pages
        pages = HomePage.objects.all()
        pages_data = serialize('json', pages)
        with open(os.path.join(export_dir, 'pages.json'), 'w') as f:
            f.write(pages_data)
        
        # Export images
        images = Image.objects.all()
        images_data = serialize('json', images)
        with open(os.path.join(export_dir, 'images.json'), 'w') as f:
            f.write(images_data)
        
        # Export documents
        documents = Document.objects.all()
        documents_data = serialize('json', documents)
        with open(os.path.join(export_dir, 'documents.json'), 'w') as f:
            f.write(documents_data)
        
        self.stdout.write(self.style.SUCCESS(f'Content exported to {export_dir}'))
        self.stdout.write(self.style.SUCCESS(f'Exported {len(pages)} pages, {len(images)} images, {len(documents)} documents'))
        
        self.stdout.write(self.style.SUCCESS('To import this content, run:'))
        self.stdout.write(self.style.NOTICE(f'python manage.py import_test_content'))
