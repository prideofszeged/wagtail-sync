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

def test_receive():
    print("Testing receive process...")
    
    # Create a simple test data
    test_data = {
        'sync_type': 'content',
        'source_instance': 'development',
        'pages': [
            {
                'id': 3,
                'title': 'Test Page',
                'slug': 'test-page',
                'content_type': 'HomePage',
                'path': '000100010001',
                'depth': 3,
                'numchild': 0,
                'url_path': '/home/test-page/',
                'body': '<p>Test content</p>'
            }
        ]
    }
    
    print("Test data:", json.dumps(test_data))
    
    try:
        print("Calling import_content command...")
        call_command('import_content', sync_data=test_data)
        print("Command completed successfully")
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_receive() 