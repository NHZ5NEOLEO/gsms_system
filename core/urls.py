from django.urls import path
from . import views

urlpatterns = [
    # === 1. TRANG CHỦ & KHÁCH (GUEST) ===
    path('', views.guest_home, name='trang_chu'),
    path('gioi-thieu/', views.trang_gioi_thieu, name='gioi_thieu'),
    path('linh-vuc/<slug:slug>/', views.chi_tiet_linh_vuc, name='chi_tiet_linh_vuc'),
    path('tin-tuc/', views.trang_tin_tuc, name='tin_tuc'),
    path('tin-tuc/<int:id>/', views.chi_tiet_tin_tuc, name='chi_tiet_tin_tuc'),
    path('san-pham/', views.trang_san_pham, name='san_pham'),
    path('lien-he/', views.trang_lien_he, name='lien_he'),
    path('doi-tac/', views.trang_doi_tac, name='doi_tac'),
    path('tuyen-dung/', views.trang_tuyen_dung, name='tuyen_dung'),
    path('gui-yeu-cau-b2b/', views.gui_yeu_cau_b2b, name='gui_yeu_cau_b2b'),
    path('nop-ho-so/', views.nop_ho_so, name='nop_ho_so'),
    path('san-pham/danh-gia/<int:sp_id>/', views.gui_danh_gia, name='gui_danh_gia'),

    # === 2. HỆ THỐNG TÀI KHOẢN ===
    path('login/', views.dang_nhap, name='login'),
    path('logout/', views.dang_xuat, name='logout'),

    # === 3. KHU VỰC NHÂN VIÊN (POS) ===
    # Hai màn hình POS mới tách biệt:
    path('pos-xang/', views.pos_xang, name='pos_xang'),
    path('pos-mart/', views.pos_mart, name='pos_mart'),
    
    # Hai luồng xử lý thanh toán tách biệt:
    path('pos-xang/process/', views.xu_ly_ban_hang, name='xu_ly_ban_hang'),
    path('pos-mart/process/', views.xu_ly_ban_mart, name='xu_ly_ban_mart'), 
    
    # Các chức năng khác giữ nguyên:
    path('chot-ca/', views.staff_chot_ca, name='staff_chot_ca'),
    path('pos/bao-cao-tram/', views.bao_cao_tram, name='bao_cao_tram'),
    path('nhan-vien/xin-cap-xang/', views.tao_yeu_cau_nhap_hang, name='tao_yeu_cau_nhap_hang'),

    # === 4. KHU VỰC ADMIN - TỔNG QUAN ===
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('import/', views.admin_import, name='admin_import'),
    path('tao-data/', views.tao_du_lieu_mau, name='tao_du_lieu_mau'), # Tool nạp 50 trạm
    path('export-excel/', views.xuat_excel_doanh_thu, name='xuat_excel_doanh_thu'),
    path('quan-ly/gia-ban/', views.quan_ly_gia, name='quan_ly_gia'),
    
    # Duyệt yêu cầu (Gộp 2 link cũ trùng nhau thành 1)
    path('quan-ly/duyet-yeu-cau/<int:yc_id>/', views.duyet_yeu_cau, name='duyet_yeu_cau'),

    # === 5. KHU VỰC ADMIN - CRUD TRẠM XĂNG ===
    path('admin-portal/tram/', views.admin_danh_sach_tram, name='admin_trams'),
    path('admin-portal/tram/them/', views.admin_them_tram, name='admin_them_tram'),
    path('admin-portal/tram/sua/<int:id>/', views.admin_sua_tram, name='admin_sua_tram'),
    path('admin-portal/tram/xoa/<int:id>/', views.admin_xoa_tram, name='admin_xoa_tram'),
    # Đã đóng băng link cũ: path('admin-portal/them-tram/', views.admin_them_tram, name='admin_them_tram'),

    # === 6. KHU VỰC ADMIN - CRUD KHO / BỒN CHỨA ===
    path('admin-portal/kho/', views.admin_danh_sach_kho, name='admin_khos'),
    path('admin-portal/kho/them/', views.admin_them_kho, name='admin_them_kho'),
    path('admin-portal/kho/sua/<int:id>/', views.admin_sua_kho, name='admin_sua_kho'),
    path('admin-portal/kho/xoa/<int:id>/', views.admin_xoa_kho, name='admin_xoa_kho'),
    # Đã đóng băng link cũ: path('quan-ly/them-kho/', views.admin_them_kho, name='admin_them_kho'),

    # === 7. KHU VỰC ADMIN - CRUD NHÂN SỰ ===
    path('admin-portal/nhan-su/', views.admin_danh_sach_nhan_su, name='admin_nhan_sus'),
    path('admin-portal/nhan-su/them/', views.admin_them_nhan_su, name='admin_them_nhan_su'),
    path('admin-portal/nhan-su/sua/<int:id>/', views.admin_sua_nhan_su, name='admin_sua_nhan_su'),
    path('admin-portal/nhan-su/xoa/<int:id>/', views.admin_xoa_nhan_su, name='admin_xoa_nhan_su'),
    # Đã đóng băng link cũ: path('quan-ly/nhan-su/', views.admin_nhan_sus, name='admin_nhan_sus'),
    # Đã đóng băng link cũ: path('quan-ly/nhan-su/thao-tac/', views.thao_tac_nhan_su, name='thao_tac_nhan_su'),

    # === 8. KHU VỰC ADMIN - CRUD TIN TỨC (Giữ nguyên của bạn) ===
    path('quan-ly/tin-tuc/', views.admin_tin_tuc, name='admin_tin_tuc'),
    path('quan-ly/tin-tuc/them/', views.admin_tin_tuc_form, name='admin_them_tin_tuc'),
    path('quan-ly/tin-tuc/sua/<int:tin_id>/', views.admin_tin_tuc_form, name='admin_sua_tin_tuc'),
    path('quan-ly/tin-tuc/xoa/<int:tin_id>/', views.admin_xoa_tin_tuc, name='admin_xoa_tin_tuc'),

    # === 9. KHU VỰC ADMIN - CRUD BANNER (Giữ nguyên của bạn) ===
    path('quan-ly/banners/', views.admin_banners, name='admin_banners'),
    path('quan-ly/banners/them/', views.admin_banner_form, name='admin_them_banner'),
    path('quan-ly/banners/sua/<int:banner_id>/', views.admin_banner_form, name='admin_sua_banner'),
    path('quan-ly/banners/xoa/<int:banner_id>/', views.admin_xoa_banner, name='admin_xoa_banner'),

    path('admin-dashboard/inbox/', views.admin_inbox, name='admin_inbox'),
]