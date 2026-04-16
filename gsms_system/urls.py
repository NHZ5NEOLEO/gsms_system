from django.contrib import admin
from django.urls import path, include

# 1. THÊM 2 DÒNG NÀY ĐỂ XỬ LÝ ẢNH
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Đổi chữ 'admin/' thành một tên khác (ví dụ: 'sys-admin/' hoặc 'he-thong-admin/')
    path('sys-admin/', admin.site.urls), 
    
    # App core của bạn vẫn giữ nguyên, nhận mọi request còn lại
    path('', include('core.urls')), 
]

# 2. THÊM ĐOẠN NÀY VÀO CUỐI CÙNG ĐỂ HIỂN THỊ ẢNH
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)