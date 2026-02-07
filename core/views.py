from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.utils import timezone
from .models import TramXang, BonChua, NhaCungCap, HoaDon, ChiTietHoaDon, TinTuc, DanhMuc, SanPham
from django.shortcuts import render
from .models import TramXang, BonChua, TinTuc, SanPham
from .models import TramXang, TinTuc, SanPham # Import thêm Model mới
from .models import ChiTietHoaDon, NhaCungCap, PhieuNhap, TramXang, BonChua, HoaDon
import uuid
import json 

# ==========================================
# 1. HỆ THỐNG XÁC THỰC (AUTH)
# ==========================================

def dang_nhap(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            messages.success(request, f"Xin chào {user.username}!")
            if user.role == 'admin':
                return redirect('admin_dashboard')
            else:
                return redirect('staff_pos')
        else:
            messages.error(request, "Tên đăng nhập hoặc mật khẩu không đúng!")
    return render(request, 'login.html')

def dang_xuat(request):
    logout(request)
    messages.info(request, "Đăng xuất thành công.")
    return redirect('login')


# ==========================================
# 2. KHU VỰC QUẢN TRỊ (ADMIN)
# ==========================================

@login_required
def admin_dashboard(request):
    if request.user.role != 'admin':
        messages.warning(request, "Bạn không có quyền truy cập!")
        return redirect('staff_pos')

    today = timezone.now().date()
    ds_bon = BonChua.objects.all()

    stats = HoaDon.objects.filter(thoi_gian__date=today).aggregate(
        total_money=Sum('tong_tien'),
        total_tx=Count('id')
    )
    doanh_thu = stats['total_money'] or 0
    so_giao_dich = stats['total_tx'] or 0

    san_luong = ChiTietHoaDon.objects.filter(
        hoa_don__thoi_gian__date=today
    ).aggregate(Sum('so_luong'))['so_luong__sum'] or 0

    context = {
        'ds_bon': ds_bon,
        'doanh_thu_hom_nay': doanh_thu,
        'san_luong_hom_nay': san_luong,
        'so_giao_dich': so_giao_dich
    }
    return render(request, 'admin_dashboard.html', context)

@login_required
def admin_import(request):
    if request.user.role != 'admin':
        return redirect('trang_chu')

    if request.method == 'POST':
        try:
            ncc_id = request.POST.get('ncc_id')
            bon_id = request.POST.get('bon_chua')
            so_lit = float(request.POST.get('so_lit', 0))
            bon = BonChua.objects.get(id=bon_id)
            
            if bon.muc_hien_tai + so_lit > bon.suc_chua_toi_da:
                messages.error(request, f"Cảnh báo: Bồn {bon.ten_bon} không đủ sức chứa!")
            else:
                bon.muc_hien_tai += so_lit
                bon.save()
                PhieuNhap.objects.create(
                    ma_pn=f"PN-{timezone.now().strftime('%d%m%H%M')}",
                    nha_cung_cap_id=ncc_id,
                    bon_chua=bon,
                    so_lit_nhap=so_lit,
                    thanh_tien=so_lit * 22000
                )
                messages.success(request, f"Đã nhập {so_lit:,.0f} lít vào {bon.ten_bon}.")
                return redirect('admin_dashboard')
        except Exception as e:
            messages.error(request, f"Lỗi nhập liệu: {e}")

    # --- SỬA LỖI FieldError TẠI ĐÂY ---
    tram = TramXang.objects.first()
    ds_ncc = NhaCungCap.objects.all()
    ds_bon = BonChua.objects.all()

    # Lấy đúng tên trường trong Database (ten_ncc, latitude...)
    ncc_data = list(ds_ncc.values('id', 'ten_ncc', 'latitude', 'longitude', 'dia_chi'))
    
    # Chuyển đổi key sang format mà JavaScript (Leaflet Map) cần: name, lat, lng
    ncc_list = []
    for item in ncc_data:
        ncc_list.append({
            'id': item['id'],
            'name': item['ten_ncc'],   # Đổi ten_ncc -> name
            'lat': item['latitude'],   # Đổi latitude -> lat
            'lng': item['longitude'],  # Đổi longitude -> lng
            'address': item['dia_chi'] # Đổi dia_chi -> address
        })

    context = {
        'tram': tram,
        'ds_ncc': ds_ncc,
        'ds_bon': ds_bon,
        'ncc_json': json.dumps(ncc_list) # Truyền JSON chuẩn xuống view
    }
    return render(request, 'admin_import.html', context)


# ==========================================
# 3. KHU VỰC NHÂN VIÊN (STAFF POS)
# ==========================================

@login_required
def staff_pos(request):
    today = timezone.now().date()
    lich_su = HoaDon.objects.filter(
        nhan_vien=request.user,
        thoi_gian__date=today
    ).order_by('-thoi_gian')[:10]
    return render(request, 'staff_pos.html', {'lich_su_ban': lich_su})

@login_required
def xu_ly_ban_hang(request):
    if request.method == 'POST':
        try:
            loai_nl = request.POST.get('loai_nhien_lieu')
            so_tien_str = request.POST.get('so_tien')
            
            if not so_tien_str:
                messages.error(request, "Vui lòng nhập số tiền!")
                return redirect('staff_pos')
                
            so_tien = float(so_tien_str)
            bang_gia = {'A95': 24500, 'E5': 23500, 'DO': 21000}
            don_gia = bang_gia.get(loai_nl, 20000)
            so_lit = so_tien / don_gia
            
            bon = BonChua.objects.filter(loai_nhien_lieu=loai_nl).first()
            if bon:
                if bon.muc_hien_tai >= so_lit:
                    bon.muc_hien_tai -= so_lit
                    bon.save()
                    hd = HoaDon.objects.create(
                        ma_hd=f"HD-{str(uuid.uuid4())[:8].upper()}",
                        nhan_vien=request.user,
                        tong_tien=so_tien
                    )
                    ChiTietHoaDon.objects.create(
                        hoa_don=hd,
                        ten_mat_hang=f"Xăng {loai_nl}",
                        so_luong=so_lit,
                        don_gia=don_gia,
                        thanh_tien=so_tien
                    )
                    messages.success(request, f"Đã bơm {so_lit:.2f} lít {loai_nl}. Thu {so_tien:,.0f}đ")
                else:
                    messages.error(request, f"HẾT HÀNG! Bồn {loai_nl} chỉ còn {bon.muc_hien_tai:.1f} lít.")
            else:
                messages.error(request, f"Lỗi: Không tìm thấy bồn chứa {loai_nl}!")
        except ValueError:
            messages.error(request, "Số tiền nhập vào không hợp lệ!")
    return redirect('staff_pos')

@login_required
def staff_chot_ca(request):
    today = timezone.now().date()
    ds_hoa_don = HoaDon.objects.filter(nhan_vien=request.user, thoi_gian__date=today)
    tong_tien = ds_hoa_don.aggregate(Sum('tong_tien'))['tong_tien__sum'] or 0
    so_gd = ds_hoa_don.count()
    tong_lit = ChiTietHoaDon.objects.filter(hoa_don__in=ds_hoa_don).aggregate(Sum('so_luong'))['so_luong__sum'] or 0

    context = {
        'tong_tien': tong_tien,
        'so_gd': so_gd,
        'tong_lit': tong_lit,
        'ngay_chot': timezone.now()
    }
    return render(request, 'staff_chot_ca.html', context)


# ==========================================
# 4. KHU VỰC KHÁCH (GUEST)
# ==========================================

def guest_home(request):
    trams = TramXang.objects.all()
    # Sửa lại mapping cho guest_home luôn để tránh lỗi tương tự
    tram_list = []
    for t in trams:
        tram_list.append({
            'ten': t.ten_tram,
            'lat': t.latitude,
            'lng': t.longitude,
            'dia_chi': t.dia_chi
        })
    
    gia_hien_tai = {'A95': 24500, 'E5': 23500, 'DO': 21000}
    context = {'tram_json': json.dumps(tram_list), 'gia': gia_hien_tai}
    return render(request, 'index.html', context)


# ==========================================
# 5. TIỆN ÍCH DEV (TẠO DATA MẪU)
# ==========================================

def tao_du_lieu_mau(request):
    # 1. XÓA SẠCH DỮ LIỆU CŨ (Để tránh trùng lặp)
    PhieuNhap.objects.all().delete()
    ChiTietHoaDon.objects.all().delete()
    HoaDon.objects.all().delete()
    BonChua.objects.all().delete()
    NhaCungCap.objects.all().delete()
    TramXang.objects.all().delete()
    TinTuc.objects.all().delete()
    SanPham.objects.all().delete()
    DanhMuc.objects.all().delete()

    # 2. TẠO TRẠM XĂNG CỦA BẠN (Trung tâm TP.HCM)
    tram = TramXang.objects.create(
        ten_tram="Cửa Hàng Xăng Dầu Số 1",
        dia_chi="123 Nguyễn Huệ, Quận 1, TP.HCM",
        latitude=10.776019,  # Tọa độ Q1
        longitude=106.701124
    )

    # 3. TẠO 3 BỒN CHỨA (Có 1 bồn sắp hết để test cảnh báo)
    BonChua.objects.create(tram=tram, ten_bon="Bồn 01 (A95)", loai_nhien_lieu='A95', suc_chua_toi_da=15000, muc_hien_tai=12500)
    BonChua.objects.create(tram=tram, ten_bon="Bồn 02 (E5)", loai_nhien_lieu='E5', suc_chua_toi_da=10000, muc_hien_tai=800) # < 10% -> Báo động đỏ
    BonChua.objects.create(tram=tram, ten_bon="Bồn 03 (DO)", loai_nhien_lieu='DO', suc_chua_toi_da=20000, muc_hien_tai=18000)

    # 4. TẠO 4 NHÀ CUNG CẤP (Nằm xung quanh TP.HCM để vẽ đường GIS)
    # Kho Nhà Bè (Nam)
    NhaCungCap.objects.create(ten_ncc="Kho Xăng Dầu Nhà Bè", dia_chi="Huyện Nhà Bè", sdt="0283873888", latitude=10.668820, longitude=106.745672)
    # Kho Thủ Đức (Đông Bắc)
    NhaCungCap.objects.create(ten_ncc="Tổng Kho Thủ Đức", dia_chi="TP. Thủ Đức", sdt="0283731234", latitude=10.849506, longitude=106.772596)
    # Kho Bình Chánh (Tây)
    NhaCungCap.objects.create(ten_ncc="Kho Nhiên Liệu Bình Chánh", dia_chi="Bình Chánh", sdt="0909123456", latitude=10.730104, longitude=106.613254)
    # Kho Cát Lái (Đông)
    NhaCungCap.objects.create(ten_ncc="Kho Cảng Cát Lái", dia_chi="Cát Lái, Q2", sdt="0918777999", latitude=10.771661, longitude=106.791583)

    # 5. TẠO DỮ LIỆU TIN TỨC & SẢN PHẨM (Cho trang chủ)
    # Tin tức
    TinTuc.objects.create(tieu_de="Giá xăng giảm mạnh chiều nay", anh_bia="https://cafefcdn.com/thumb_w/650/2033/1/4/photo-1-16728189874452093774880.jpg", tom_tat="Liên Bộ Công Thương - Tài chính vừa điều chỉnh giá xăng dầu...", noi_dung="...")
    TinTuc.objects.create(tieu_de="Khai trương trạm sạc xe điện", anh_bia="https://vinfastauto.com/sites/default/files/styles/news_detail/public/2021-04/VinFast-vf-e34_0.jpg", tom_tat="GSMS hợp tác lắp đặt trạm sạc nhanh...", noi_dung="...")
    
    # Sản phẩm
    dm1 = DanhMuc.objects.create(ten_dm="Dầu Nhớt")
    dm2 = DanhMuc.objects.create(ten_dm="Phụ Gia")
    SanPham.objects.create(danh_muc=dm1, ten_sp="Castrol Power 1", gia_tham_khao=120000, anh_sp="https://cf.shopee.vn/file/49a6224168e3708304f5533139855584", mo_ta="Dầu nhớt tổng hợp toàn phần")
    SanPham.objects.create(danh_muc=dm2, ten_sp="Nước làm mát", gia_tham_khao=50000, anh_sp="https://bizweb.dktcdn.net/100/416/542/products/nuoc-lam-mat-dong-co-o-to-xe-may-mau-xanh-blue-fobe-super-coolant-500ml-lon-p523a1.jpg", mo_ta="Giải nhiệt động cơ")

    messages.success(request, "Đã khởi tạo dữ liệu mẫu thành công! Bản đồ đã sẵn sàng.")
    return redirect('admin_dashboard')


def guest_home(request):
    # 1. Dữ liệu GIS (Trạm xăng)
    trams = TramXang.objects.all()
    tram_list = []
    for t in trams:
        # Giả lập dữ liệu loại xăng có tại trạm (để demo lọc)
        # Trong thực tế bạn sẽ query từ bảng BonChua
        tram_list.append({
            'id': t.id,
            'ten': t.ten_tram,
            'lat': t.latitude,
            'lng': t.longitude,
            'dia_chi': t.dia_chi,
            'types': ['A95', 'E5'] if t.id % 2 == 0 else ['A95', 'DO'] # Demo: Trạm chẵn có E5, lẻ có DO
        })

    # 2. Dữ liệu Tin tức (Tạm thời fake list nếu chưa nhập DB)
    tin_tuc = [
        {'tieu_de': 'Giá xăng dầu hôm nay giảm mạnh', 'anh': 'https://image.thanhnien.vn/w1024/Uploaded/2026/puqg/2024_04_11/gia-xang-dau-hom-nay-1142024-anh-ngoc-thang-304.jpg', 'tom_tat': 'Liên Bộ Công Thương - Tài chính vừa công bố giá cơ sở...'},
        {'tieu_de': 'Khai trương trạm xăng mới tại Quận 7', 'anh': 'https://petrolimex.com.vn/public/userfiles/images/2021/T6/18062021_KV2_CH42_01.jpg', 'tom_tat': 'GSMS mở rộng mạng lưới với trạm xăng tiêu chuẩn 5 sao...'},
        {'tieu_de': 'Hợp tác chiến lược với VinFast', 'anh': 'https://vinfastauto.com/sites/default/files/styles/news_detail/public/2021-04/VinFast-vf-e34_0.jpg', 'tom_tat': 'Triển khai trạm sạc điện tại hệ thống cây xăng GSMS...'}
    ]

    context = {
        'tram_json': json.dumps(tram_list),
        'tin_tuc': tin_tuc,
    }
    return render(request, 'index.html', context)
def guest_home(request):
    # 1. Lấy dữ liệu hiển thị web
    tin_tuc_moi = TinTuc.objects.order_by('-ngay_dang')[:3]
    san_pham_hot = SanPham.objects.all()[:4] # Lấy 4 sản phẩm demo

    # 2. Xử lý dữ liệu GIS (Phức tạp hơn: Phải biết trạm đó còn xăng loại nào)
    trams = TramXang.objects.all()
    tram_list = []
    
    for t in trams:
        # Kiểm tra tồn kho thực tế của trạm này
        available_fuels = []
        # Nếu bồn A95 còn > 0 lít thì thêm vào danh sách
        if BonChua.objects.filter(tram=t, loai_nhien_lieu='A95', muc_hien_tai__gt=0).exists():
            available_fuels.append('A95')
        if BonChua.objects.filter(tram=t, loai_nhien_lieu='E5', muc_hien_tai__gt=0).exists():
            available_fuels.append('E5')
        if BonChua.objects.filter(tram=t, loai_nhien_lieu='DO', muc_hien_tai__gt=0).exists():
            available_fuels.append('DO')

        tram_list.append({
            'id': t.id,
            'ten': t.ten_tram,
            'lat': t.latitude,
            'lng': t.longitude,
            'dia_chi': t.dia_chi,
            'fuels': available_fuels # VD: ['A95', 'DO']
        })

    # 3. Giá xăng niêm yết (Demo chạy chữ)
    gia_hien_tai = {'A95': 24500, 'E5': 23500, 'DO': 21000}

    context = {
        'tram_json': json.dumps(tram_list),
        'tin_tuc': tin_tuc_moi,
        'san_pham': san_pham_hot,
        'gia': gia_hien_tai
    }
    return render(request, 'index.html', context)

# core/views.py

def trang_gioi_thieu(request):
    return render(request, 'pages/gioi_thieu.html')

def trang_linh_vuc(request, slug):
    # Dữ liệu mẫu (Hardcode) cho từng lĩnh vực hoạt động
    data = {
        'xang-dau': {
            'title': 'Kinh Doanh Xăng Dầu',
            'img': 'https://petrolimex.com.vn/public/userfiles/images/2021/T6/18062021_KV2_CH42_01.jpg',
            'content': 'GSMS sở hữu mạng lưới 500+ trạm xăng trải dài toàn quốc, cung cấp nhiên liệu chất lượng cao (Euro 4, Euro 5) đảm bảo hiệu suất động cơ tối ưu.'
        },
        'van-tai': {
            'title': 'Vận Tải Xăng Dầu',
            'img': 'https://image.saigondautu.com.vn/w680/Uploaded/2026/bp_cpi/2022_09_06/xang-dau-2_LDKN.jpg',
            'content': 'Đội xe bồn hiện đại 200 chiếc cùng hệ thống tàu viễn dương, đảm bảo chuỗi cung ứng không bao giờ đứt gãy.'
        },
        'gas': {
            'title': 'Khí Hóa Lỏng (LPG)',
            'img': 'https://cdn.thuvienphapluat.vn/uploads/tintuc/2022/10/28/binh-gas.jpg',
            'content': 'Cung cấp Gas dân dụng và Gas công nghiệp an toàn tuyệt đối, ngọn lửa xanh, tiết kiệm nhiên liệu.'
        },
        'hoa-dau': {
            'title': 'Hóa Dầu & Dung Môi',
            'img': 'https://vneconomy.mediacdn.vn/thumb_w/640/2023/2/14/dau-nhot-16763660334811776856525.jpg',
            'content': 'Phân phối các dòng dầu nhờn, nhựa đường và hóa chất chuyên dụng cho các ngành công nghiệp nặng.'
        },
        'tai-chinh': {
            'title': 'Dịch vụ Tài chính',
            'img': 'https://baodautu.vn/Images/chicong/2021/04/28/PG-Bank.jpg',
            'content': 'Hợp tác với các ngân hàng lớn cung cấp giải pháp thanh toán không tiền mặt, thẻ tín dụng xăng dầu và bảo hiểm.'
        }
    }
    context = data.get(slug, data['xang-dau']) # Mặc định là xăng dầu nếu không tìm thấy
    return render(request, 'pages/linh_vuc.html', context)

def trang_tin_tuc(request):
    # Lấy tin từ DB (Đã tạo ở phần trước)
    tin_tuc = TinTuc.objects.all().order_by('-ngay_dang')
    return render(request, 'pages/tin_tuc.html', {'ds_tin': tin_tuc})

def trang_san_pham(request):
    # Lấy sản phẩm từ DB
    san_pham = SanPham.objects.all()
    return render(request, 'pages/san_pham.html', {'ds_sp': san_pham})