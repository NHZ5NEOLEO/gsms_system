import os

from django.core.wsgi import get_wsgi_application

# Trỏ hệ thống về đúng file settings của bạn
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gsms_system.settings')

application = get_wsgi_application()