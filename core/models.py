from django.db import models
from django.contrib.auth.models import AbstractUser

# 1. NGƯỜI DÙNG (Phân quyền Admin/Nhân viên)
class User(AbstractUser):
    ROLES = (
        ('admin', 'Quản trị viên'),
        ('staff', 'Nhân viên bán hàng'),
    )
    role = models.CharField(max_length=10, choices=ROLES, default='staff')
    full_name = models.CharField(max_length=100, verbose_name="Họ và tên")
    phone = models.CharField(max_length=15, verbose_name="Số điện thoại")
    
    # Thông tin riêng cho nhân viên
    cccd = models.CharField(max_length=20, blank=True, null=True)
    ca_lam_viec = models.CharField(max_length=50, blank=True, null=True)

# 2. TRẠM XĂNG (GIS)
class TramXang(models.Model):
    ten_tram = models.CharField(max_length=100)
    dia_chi = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    
    def __str__(self): return self.ten_tram

# 3. BỒN CHỨA (Kho)
class BonChua(models.Model):
    LOAI_XANG = (('A95', 'Xăng A95'), ('E5', 'Xăng E5'), ('DO', 'Dầu DO'))
    tram = models.ForeignKey(TramXang, on_delete=models.CASCADE)
    ten_bon = models.CharField(max_length=50) 
    loai_nhien_lieu = models.CharField(max_length=10, choices=LOAI_XANG)
    suc_chua_toi_da = models.FloatField()
    muc_hien_tai = models.FloatField()
    
    def __str__(self): return f"{self.ten_bon} - {self.loai_nhien_lieu}"

    # Thuộc tính hỗ trợ hiển thị % trên Dashboard
    @property
    def phan_tram(self):
        if self.suc_chua_toi_da == 0: return 0
        return round((self.muc_hien_tai / self.suc_chua_toi_da) * 100, 1)

# 4. HÓA ĐƠN & CHI TIẾT (Bán hàng)
class HoaDon(models.Model):
    ma_hd = models.CharField(max_length=50, unique=True)
    nhan_vien = models.ForeignKey(User, on_delete=models.CASCADE)
    thoi_gian = models.DateTimeField(auto_now_add=True)
    tong_tien = models.FloatField()
    
    def __str__(self): return self.ma_hd

class ChiTietHoaDon(models.Model):
    hoa_don = models.ForeignKey(HoaDon, on_delete=models.CASCADE)
    ten_mat_hang = models.CharField(max_length=100)
    so_luong = models.FloatField()
    don_gia = models.FloatField()
    thanh_tien = models.FloatField()

# 5. NHÀ CUNG CẤP & PHIẾU NHẬP (GIS & Kho)
class NhaCungCap(models.Model):
    ten_ncc = models.CharField(max_length=100)
    dia_chi = models.CharField(max_length=255)
    sdt = models.CharField(max_length=15)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self): return self.ten_ncc

class PhieuNhap(models.Model):
    ma_pn = models.CharField(max_length=20, unique=True)
    thoi_gian = models.DateTimeField(auto_now_add=True)
    nha_cung_cap = models.ForeignKey(NhaCungCap, on_delete=models.CASCADE)
    bon_chua = models.ForeignKey(BonChua, on_delete=models.CASCADE)
    so_lit_nhap = models.FloatField()
    thanh_tien = models.FloatField()

    def __str__(self): return self.ma_pn

# 6. TIN TỨC (Trang chủ doanh nghiệp)
class TinTuc(models.Model):
    tieu_de = models.CharField(max_length=200)
    anh_bia = models.CharField(max_length=500) 
    tom_tat = models.TextField()
    noi_dung = models.TextField()
    ngay_dang = models.DateTimeField(auto_now_add=True)

    def __str__(self): return self.tieu_de

# 7. SẢN PHẨM & DANH MỤC (Trang chủ doanh nghiệp)
class DanhMuc(models.Model):
    ten_dm = models.CharField(max_length=100)
    def __str__(self): return self.ten_dm

class SanPham(models.Model):
    danh_muc = models.ForeignKey(DanhMuc, on_delete=models.CASCADE)
    ten_sp = models.CharField(max_length=100)
    gia_tham_khao = models.FloatField()
    anh_sp = models.CharField(max_length=500)
    mo_ta = models.TextField()

    def __str__(self): return self.ten_sp