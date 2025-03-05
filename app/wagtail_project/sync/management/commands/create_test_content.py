import os
from django.core.management.base import BaseCommand
from django.core.files.images import ImageFile
from wagtail.models import Page, Site
from wagtail.images.models import Image
from wagtail.documents.models import Document
from wagtail.rich_text import RichText
from wagtail.blocks import StreamBlock, StructBlock, CharBlock, TextBlock, RichTextBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtail_project.home.models import HomePage


class TestPageStructBlock(StructBlock):
    heading = CharBlock()
    text = RichTextBlock()
    image = ImageChooserBlock(required=False)


class Command(BaseCommand):
    help = 'Create test content for the wagtail instance'

    def handle(self, *args, **options):
        # Get root page
        root_page = Page.objects.get(id=1)
        
        # Find home page either by slug or by getting the first child of root
        try:
            # Try to find home page by checking root's children
            home_page = Page.objects.filter(path__startswith=root_page.path, depth=root_page.depth + 1).first()
            
            if home_page:
                # Get the specific page instance
                home_page = home_page.specific
                self.stdout.write(self.style.SUCCESS(f'Found existing home page: {home_page.title}'))
                
                # Update body if it's empty
                if isinstance(home_page, HomePage) and not home_page.body:
                    home_page.body = "<p>Welcome to our example Wagtail site!</p>"
                    home_page.save()
            else:
                self.stdout.write(self.style.NOTICE('Creating new home page...'))
                home_page = HomePage(
                    title="Home",
                    slug="home",
                    body="<p>Welcome to our example Wagtail site!</p>",
                )
                root_page.add_child(instance=home_page)
                home_page.save_revision().publish()
                self.stdout.write(self.style.SUCCESS(f'Created home page: {home_page.title}'))
            
            # Make sure we have a site configured
            if not Site.objects.filter(is_default_site=True).exists():
                Site.objects.create(
                    hostname='localhost',
                    port=8001,
                    root_page=home_page,
                    is_default_site=True,
                    site_name='Wagtail Dev'
                )
                self.stdout.write(self.style.SUCCESS('Created default site configuration'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error setting up home page: {str(e)}'))
            return
        
        # Create some test pages
        self.create_content_pages(home_page)
        self.create_test_images()
        self.create_test_documents()

    def create_content_pages(self, parent_page):
        # Create some child pages
        for i in range(1, 6):
            title = f'Test Page {i}'
            slug = f'test-page-{i}'
            
            # Skip if it already exists
            if parent_page.get_children().filter(slug=slug).exists():
                self.stdout.write(self.style.NOTICE(f'Page already exists: {title}'))
                continue
            
            self.stdout.write(self.style.NOTICE(f'Creating page: {title}'))
            
            # Create the page
            page = HomePage(
                title=title,
                slug=slug,
                body=f'<p>This is test page number {i} with some <strong>rich text</strong> content.</p><p>This can be used to test the sync functionality.</p>',
            )
            parent_page.add_child(instance=page)
            page.save_revision().publish()
            
            # Add sub-pages to first page
            if i == 1:
                for j in range(1, 4):
                    sub_title = f'Sub Page {j}'
                    sub_slug = f'sub-page-{j}'
                    
                    # Skip if it already exists
                    if page.get_children().filter(slug=sub_slug).exists():
                        self.stdout.write(self.style.NOTICE(f'Page already exists: {sub_title}'))
                        continue
                    
                    self.stdout.write(self.style.NOTICE(f'Creating page: {sub_title}'))
                    
                    # Create the sub page
                    sub_page = HomePage(
                        title=sub_title,
                        slug=sub_slug,
                        body=f'<p>This is sub-page number {j} under test page 1.</p><p>More sample content here.</p>',
                    )
                    page.add_child(instance=sub_page)
                    sub_page.save_revision().publish()
                    
                    self.stdout.write(self.style.SUCCESS(f'Created sub page: {sub_title}'))
            
            self.stdout.write(self.style.SUCCESS(f'Created page: {title}'))

    def create_test_images(self):
        # Create some test images
        for i in range(1, 4):
            title = f'Test Image {i}'
            
            # Skip if it already exists
            if Image.objects.filter(title=title).exists():
                self.stdout.write(self.style.NOTICE(f'Image already exists: {title}'))
                continue
            
            # Create a simple test image file
            filename = f'test_image_{i}.png'
            file_path = os.path.join('/app', 'tmp', filename)
            
            # Ensure tmp directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Create a simple colored square image
            from PIL import Image as PILImage
            colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]  # Red, Green, Blue
            img = PILImage.new('RGB', (500, 500), colors[i % len(colors)])
            img.save(file_path)
            
            # Create the Wagtail image
            with open(file_path, 'rb') as f:
                image_file = ImageFile(f, name=filename)
                image = Image(title=title, file=image_file)
                image.save()
            
            self.stdout.write(self.style.SUCCESS(f'Created image: {title}'))
            
            # Clean up the file
            os.remove(file_path)

    def create_test_documents(self):
        # Create some test documents
        for i in range(1, 4):
            title = f'Test Document {i}'
            
            # Skip if it already exists
            if Document.objects.filter(title=title).exists():
                self.stdout.write(self.style.NOTICE(f'Document already exists: {title}'))
                continue
            
            # Create a simple test document file
            filename = f'test_document_{i}.txt'
            file_path = os.path.join('/app', 'tmp', filename)
            
            # Ensure tmp directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Create a simple text file
            with open(file_path, 'w') as f:
                f.write(f'This is test document {i} for the Wagtail sync functionality.\n')
                f.write(f'It contains some sample text that can be used for testing.\n')
                f.write(f'Document ID: {i}\n')
            
            # Create the Wagtail document
            with open(file_path, 'rb') as f:
                file_content = f.read()
                from django.core.files.base import ContentFile
                document = Document(title=title)
                document.file.save(filename, ContentFile(file_content))
            
            self.stdout.write(self.style.SUCCESS(f'Created document: {title}'))
            
            # Clean up the file
            os.remove(file_path)
