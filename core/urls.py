from django.urls import path
from . import views

urlpatterns = [
    # 1. Trang chủ: Vào thẳng Bản đồ (Guest)
    path('', views.guest_home, name='trang_chu'),

    # 2. Hệ thống tài khoản
    path('login/', views.dang_nhap, name='login'),
    path('logout/', views.dang_xuat, name='logout'),
    
    # 3. Khu vực Admin
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('import/', views.admin_import, name='admin_import'),
    
    # --- SỬA LỖI TẠI ĐÂY: Đặt tên name='tao_du_lieu_mau' cho khớp với nút bấm HTML ---
    path('tao-data/', views.tao_du_lieu_mau, name='tao_du_lieu_mau'),

    # 4. Khu vực Nhân viên (POS)
    path('pos/', views.staff_pos, name='staff_pos'),
    path('pos/process/', views.xu_ly_ban_hang, name='xu_ly_ban_hang'),
    path('chot-ca/', views.staff_chot_ca, name='staff_chot_ca'),
    # Trang chủ
    path('gioi-thieu/', views.trang_gioi_thieu, name='gioi_thieu'),
    path('linh-vuc/<str:slug>/', views.trang_linh_vuc, name='linh_vuc'), # 1 trang dùng chung cho 5 lĩnh vực
    path('tin-tuc/', views.trang_tin_tuc, name='tin_tuc'),
    path('san-pham/', views.trang_san_pham, name='san_pham'),
]