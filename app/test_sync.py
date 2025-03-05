import os
import sys
import json
import requests

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wagtail_project.settings.development')

import django
django.setup()

from django.core.management import call_command
from wagtail.models import Page

def test_sync():
    print("Testing sync process...")
    
    # Get all pages
    pages = Page.objects.filter(depth__gt=1).specific()
    print(f"Found {len(pages)} pages")
    
    # Prepare data for sync
    sync_data = {
        'sync_type': 'content',
        'source_instance': 'development',
        'pages': []
    }
    
    # Add page data
    for page in pages:
        page_data = {
            'id': page.id,
            'title': page.title,
            'slug': page.slug,
            'content_type': page.specific_class.__name__,
            'path': page.path,
            'depth': page.depth,
            'numchild': page.numchild,
            'url_path': page.url_path,
        }
        
        # Add page-specific fields if available
        if hasattr(page, 'body'):
            page_data['body'] = page.body
        
        sync_data['pages'].append(page_data)
    
    # Print the data we're sending
    print(f"Sending data: {json.dumps(sync_data)[:500]}...")
    
    # Send data to production instance
    target_url = 'http://wagtail-prod:8000/sync/receive/'
    print(f"Sending data to {target_url}...")
    
    try:
        response = requests.post(
            target_url,
            json=sync_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == '__main__':
    test_sync() 