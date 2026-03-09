import json
import uuid
import random
from datetime import timedelta
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.utils import timezone
from .models import TramXang, BonChua, NhaCungCap, HoaDon, ChiTietHoaDon, TinTuc, DanhMuc, SanPham, PhieuNhap


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

    # Thống kê nhanh
    stats = HoaDon.objects.filter(thoi_gian__date=today).aggregate(
        total_money=Sum('tong_tien'),
        total_tx=Count('id')
    )
    doanh_thu = stats['total_money'] or 0
    so_giao_dich = stats['total_tx'] or 0

    san_luong = ChiTietHoaDon.objects.filter(
        hoa_don__thoi_gian__date=today
    ).aggregate(Sum('so_luong'))['so_luong__sum'] or 0

    # ==========================================
    # TÍNH TOÁN DỮ LIỆU THẬT CHO BIỂU ĐỒ (CHART.JS)
    # ==========================================
    now = timezone.now()
    
    # 1. DỮ LIỆU THEO NGÀY (7 ngày qua)
    day_data = {'labels': [], 'revenue': [], 'volume': []}
    for i in range(6, -1, -1):
        dt = now - timedelta(days=i)
        day_data['labels'].append(dt.strftime("%d/%m"))
        
        hds = HoaDon.objects.filter(thoi_gian__date=dt.date())
        dt_sum = hds.aggregate(Sum('tong_tien'))['tong_tien__sum'] or 0
        day_data['revenue'].append(float(dt_sum) / 1000000)
        
        sl_sum = ChiTietHoaDon.objects.filter(hoa_don__in=hds).aggregate(Sum('so_luong'))['so_luong__sum'] or 0
        day_data['volume'].append(float(sl_sum))

    # 2. DỮ LIỆU THEO THÁNG (4 tuần qua)
    month_data = {'labels': ['Tuần 1', 'Tuần 2', 'Tuần 3', 'Tuần 4'], 'revenue': [0,0,0,0], 'volume': [0,0,0,0]}
    for i in range(28):
        dt = now - timedelta(days=i)
        week_idx = 3 - (i // 7)
        
        hds = HoaDon.objects.filter(thoi_gian__date=dt.date())
        dt_sum = hds.aggregate(Sum('tong_tien'))['tong_tien__sum'] or 0
        month_data['revenue'][week_idx] += float(dt_sum) / 1000000
        
        sl_sum = ChiTietHoaDon.objects.filter(hoa_don__in=hds).aggregate(Sum('so_luong'))['so_luong__sum'] or 0
        month_data['volume'][week_idx] += float(sl_sum)

    # 3. DỮ LIỆU THEO NĂM (12 Tháng của năm hiện tại)
    year_data = {'labels': [f'T{i}' for i in range(1, 13)], 'revenue': [0]*12, 'volume': [0]*12}
    hds_year = HoaDon.objects.filter(thoi_gian__year=now.year)
    for hd in hds_year:
        m_idx = hd.thoi_gian.month - 1
        year_data['revenue'][m_idx] += float(hd.tong_tien or 0) / 1000000
        
        sl_sum = ChiTietHoaDon.objects.filter(hoa_don=hd).aggregate(Sum('so_luong'))['so_luong__sum'] or 0
        year_data['volume'][m_idx] += float(sl_sum)

    # 4. DỮ LIỆU THEO QUÝ
    quarter_data = {
        'labels': ['Quý 1', 'Quý 2', 'Quý 3', 'Quý 4'],
        'revenue': [
            sum(year_data['revenue'][0:3]), sum(year_data['revenue'][3:6]),
            sum(year_data['revenue'][6:9]), sum(year_data['revenue'][9:12])
        ],
        'volume': [
            sum(year_data['volume'][0:3]), sum(year_data['volume'][3:6]),
            sum(year_data['volume'][6:9]), sum(year_data['volume'][9:12])
        ]
    }

    chart_data = {
        'day': day_data,
        'month': month_data,
        'quarter': quarter_data,
        'year': year_data
    }
    
    chart_data_json = json.dumps(chart_data)

    context = {
        'ds_bon': ds_bon,
        'doanh_thu_hom_nay': doanh_thu,
        'san_luong_hom_nay': san_luong,
        'so_giao_dich': so_giao_dich,
        'chart_data_json': chart_data_json,
    }
    return render(request, 'admin_dashboard.html', context)


@login_required
def admin_import(request):
    if request.user.role != 'admin':
        return redirect('trang_chu')

    # XỬ LÝ KHI BẤM NÚT "PHÁT LỆNH NHẬP KHO"
    if request.method == 'POST':
        try:
            ncc_id = request.POST.get('ncc_id')
            bon_id = request.POST.get('bon_chua')
            so_lit = float(request.POST.get('so_lit', 0))
            
            if not bon_id:
                messages.error(request, "Vui lòng chọn bồn chứa!")
                return redirect('admin_import')
                
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

    # ========================================================
    # ĐÓNG GÓI DỮ LIỆU SẠCH SẼ BẰNG JSON ĐỂ TRÁNH LỖI JAVASCRIPT
    # ========================================================
    ds_ncc = NhaCungCap.objects.all()
    ds_bon = BonChua.objects.select_related('tram').all()

    # 1. Đóng gói Kho (Nhà cung cấp)
    ncc_list = [{
        'id': n.id, 
        'name': n.ten_ncc, 
        'lat': float(n.latitude or 0), 
        'lng': float(n.longitude or 0), 
        'address': n.dia_chi
    } for n in ds_ncc]

    # 2. Đóng gói Trạm Xăng và Bồn Chứa
    tank_list = []
    station_dict = {}

    for b in ds_bon:
        phan_tram = round((b.muc_hien_tai / b.suc_chua_toi_da) * 100, 1) if b.suc_chua_toi_da > 0 else 0
        
        # Danh sách bồn
        tank_list.append({
            'id': b.id,
            'ten_bon': b.ten_bon,
            'loai': b.get_loai_nhien_lieu_display(),
            'muc_hien_tai': float(b.muc_hien_tai),
            'suc_chua': float(b.suc_chua_toi_da),
            'phan_tram': phan_tram,
            'tram_id': b.tram.id
        })
        
        # Lọc ra danh sách trạm độc nhất
        if b.tram.id not in station_dict:
            station_dict[b.tram.id] = {
                'id': b.tram.id,
                'name': b.tram.ten_tram,
                'lat': float(b.tram.latitude or 0),
                'lng': float(b.tram.longitude or 0)
            }

    context = {
        'ds_ncc': ds_ncc,
        # Truyền JSON thẳng sang HTML
        'ncc_json': json.dumps(ncc_list),
        'tank_json': json.dumps(tank_list),
        'station_json': json.dumps(list(station_dict.values())),
    }
    return render(request, 'admin_import.html', context)


@login_required
def admin_add_station(request):
    if request.user.role != 'admin':
        messages.warning(request, "Bạn không có quyền truy cập!")
        return redirect('trang_chu')

    if request.method == 'POST':
        try:
            ten_tram = request.POST.get('ten_tram')
            dia_chi = request.POST.get('dia_chi')
            lat = request.POST.get('lat')
            lng = request.POST.get('lng')

            # 1. Tạo Trạm Xăng mới
            tram_moi = TramXang.objects.create(
                ten_tram=ten_tram,
                dia_chi=dia_chi,
                latitude=float(lat),
                longitude=float(lng)
            )

            # 2. Tự động khởi tạo 3 Bồn chứa rỗng (0 Lít) cho trạm mới này
            BonChua.objects.create(tram=tram_moi, ten_bon="Bồn A95", loai_nhien_lieu='A95', suc_chua_toi_da=15000, muc_hien_tai=0)
            BonChua.objects.create(tram=tram_moi, ten_bon="Bồn E5", loai_nhien_lieu='E5', suc_chua_toi_da=10000, muc_hien_tai=0)
            BonChua.objects.create(tram=tram_moi, ten_bon="Bồn DO", loai_nhien_lieu='DO', suc_chua_toi_da=20000, muc_hien_tai=0)

            messages.success(request, f"Đã thêm thành công: {ten_tram}. Các bồn chứa hiện đang trống, vui lòng lập lệnh Nhập hàng!")
            return redirect('admin_dashboard')

        except Exception as e:
            messages.error(request, f"Lỗi khi thêm trạm: {e}")

    return render(request, 'admin_add_station.html')

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
# 4. KHU VỰC KHÁCH (GUEST) & TIỆN ÍCH
# ==========================================

def guest_home(request):
    tin_tuc_moi = TinTuc.objects.order_by('-ngay_dang')[:3]
    san_pham_hot = SanPham.objects.all()[:4]

    trams = TramXang.objects.all()
    tram_list = []
    
    for t in trams:
        available_fuels = []
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
            'fuels': available_fuels
        })

    gia_hien_tai = {'A95': 24500, 'E5': 23500, 'DO': 21000}

    context = {
        'tram_json': json.dumps(tram_list),
        'tin_tuc': tin_tuc_moi,
        'san_pham': san_pham_hot,
        'gia': gia_hien_tai
    }
    return render(request, 'index.html', context)


def trang_gioi_thieu(request):
    return render(request, 'pages/gioi_thieu.html')


def trang_linh_vuc(request, slug):
    data = {
        'xang-dau': {
            'title': 'Kinh Doanh Xăng Dầu',
            'img': 'https://petrolimex.com.vn/public/userfiles/images/2021/T6/18062021_KV2_CH42_01.jpg',
            'content': 'GSMS sở hữu mạng lưới 500+ trạm xăng trải dài toàn quốc, cung cấp nhiên liệu chất lượng cao.'
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
            'content': 'Hợp tác với các ngân hàng lớn cung cấp giải pháp thanh toán không tiền mặt, thẻ tín dụng xăng dầu.'
        }
    }
    context = data.get(slug, data['xang-dau'])
    return render(request, 'pages/linh_vuc.html', context)


def trang_tin_tuc(request):
    tin_tuc = TinTuc.objects.all().order_by('-ngay_dang')
    return render(request, 'pages/tin_tuc.html', {'ds_tin': tin_tuc})


def trang_san_pham(request):
    san_pham = SanPham.objects.all()
    return render(request, 'pages/san_pham.html', {'ds_sp': san_pham})


# ==========================================
# 5. TIỆN ÍCH DEV (TẠO DATA MẪU)
# ==========================================

def tao_du_lieu_mau(request):
    PhieuNhap.objects.all().delete()
    ChiTietHoaDon.objects.all().delete()
    HoaDon.objects.all().delete()
    BonChua.objects.all().delete()
    NhaCungCap.objects.all().delete()
    TramXang.objects.all().delete()
    TinTuc.objects.all().delete()
    SanPham.objects.all().delete()
    DanhMuc.objects.all().delete()

    danh_sach_tram = [
        {"ten": "CHXD Số 1 - Trung Tâm", "dia_chi": "123 Nguyễn Huệ, Quận 1", "lat": 10.776019, "lng": 106.701124},
        {"ten": "CHXD Petrolimex Số 02", "dia_chi": "281 Lý Thường Kiệt, Quận 11", "lat": 10.775263, "lng": 106.653457},
        {"ten": "Trạm Xăng Comeco Hàng Xanh", "dia_chi": "Ngã tư Hàng Xanh, Bình Thạnh", "lat": 10.801538, "lng": 106.711124},
        {"ten": "CHXD Số 4 - Lê Văn Sỹ", "dia_chi": "380 Lê Văn Sỹ, Tân Bình", "lat": 10.792557, "lng": 106.663185},
        {"ten": "Trạm Xăng Dầu Số 5", "dia_chi": "117 Quang Trung, Gò Vấp", "lat": 10.828854, "lng": 106.678453},
        {"ten": "CHXD Comeco Lý Thái Tổ", "dia_chi": "49 Lý Thái Tổ, Quận 10", "lat": 10.765620, "lng": 106.676648},
        {"ten": "Trạm Xăng Phú Mỹ Hưng", "dia_chi": "15B Nguyễn Lương Bằng, Quận 7", "lat": 10.725801, "lng": 106.721453},
        {"ten": "CHXD An Sương", "dia_chi": "Ngã tư An Sương, Quận 12", "lat": 10.833111, "lng": 106.613322},
        {"ten": "Trạm Xăng 99 Bình Chánh", "dia_chi": "99 Nguyễn Văn Linh, Bình Chánh", "lat": 10.718843, "lng": 106.650231},
        {"ten": "CHXD Kha Vạn Cân", "dia_chi": "200 Kha Vạn Cân, TP. Thủ Đức", "lat": 10.835421, "lng": 106.748342},
        {"ten": "Trạm Xăng Hoàng Văn Thụ", "dia_chi": "200 Hoàng Văn Thụ, Phú Nhuận", "lat": 10.800010, "lng": 106.671092},
        {"ten": "CHXD Đại Lộ Đông Tây", "dia_chi": "Võ Văn Kiệt, Quận 5", "lat": 10.751245, "lng": 106.666320},
        {"ten": "Trạm Xăng Bình Tân", "dia_chi": "Quốc Lộ 1A, Bình Tân", "lat": 10.738092, "lng": 106.598211},
        {"ten": "CHXD Khu Công Nghệ Cao", "dia_chi": "88 Lê Văn Việt, TP. Thủ Đức", "lat": 10.844356, "lng": 106.782103},
        {"ten": "Trạm Xăng Nguyễn Văn Cừ", "dia_chi": "Nguyễn Văn Cừ, Quận 8", "lat": 10.758923, "lng": 106.682310},
    ]

    for index, data in enumerate(danh_sach_tram):
        tram = TramXang.objects.create(
            ten_tram=data["ten"],
            dia_chi=data["dia_chi"],
            latitude=data["lat"],
            longitude=data["lng"]
        )
        if index == 0:
            BonChua.objects.create(tram=tram, ten_bon="Bồn A95", loai_nhien_lieu='A95', suc_chua_toi_da=15000, muc_hien_tai=12000)
            BonChua.objects.create(tram=tram, ten_bon="Bồn E5", loai_nhien_lieu='E5', suc_chua_toi_da=10000, muc_hien_tai=500)
            BonChua.objects.create(tram=tram, ten_bon="Bồn DO", loai_nhien_lieu='DO', suc_chua_toi_da=20000, muc_hien_tai=18000)
        else:
            BonChua.objects.create(tram=tram, ten_bon="Bồn A95", loai_nhien_lieu='A95', suc_chua_toi_da=15000, muc_hien_tai=random.randint(1000, 15000))
            BonChua.objects.create(tram=tram, ten_bon="Bồn E5", loai_nhien_lieu='E5', suc_chua_toi_da=10000, muc_hien_tai=random.randint(0, 10000))
            BonChua.objects.create(tram=tram, ten_bon="Bồn DO", loai_nhien_lieu='DO', suc_chua_toi_da=20000, muc_hien_tai=random.randint(2000, 20000))

    NhaCungCap.objects.create(ten_ncc="Kho Xăng Dầu Nhà Bè", dia_chi="Huyện Nhà Bè", sdt="0283873888", latitude=10.668820, longitude=106.745672)
    NhaCungCap.objects.create(ten_ncc="Tổng Kho Thủ Đức", dia_chi="TP. Thủ Đức", sdt="0283731234", latitude=10.849506, longitude=106.772596)
    NhaCungCap.objects.create(ten_ncc="Kho Nhiên Liệu Bình Chánh", dia_chi="Bình Chánh", sdt="0909123456", latitude=10.730104, longitude=106.613254)
    NhaCungCap.objects.create(ten_ncc="Kho Cảng Cát Lái", dia_chi="Cát Lái, Q2", sdt="0918777999", latitude=10.771661, longitude=106.791583)

    TinTuc.objects.create(tieu_de="Giá xăng giảm mạnh chiều nay", anh_bia="https://cafefcdn.com/thumb_w/650/2033/1/4/photo-1-16728189874452093774880.jpg", tom_tat="Liên Bộ Công Thương - Tài chính vừa điều chỉnh giá xăng dầu...", noi_dung="...")
    TinTuc.objects.create(tieu_de="Khai trương trạm sạc xe điện", anh_bia="https://vinfastauto.com/sites/default/files/styles/news_detail/public/2021-04/VinFast-vf-e34_0.jpg", tom_tat="GSMS hợp tác lắp đặt trạm sạc nhanh...", noi_dung="...")
    
    dm1 = DanhMuc.objects.create(ten_dm="Dầu Nhớt")
    dm2 = DanhMuc.objects.create(ten_dm="Phụ Gia")
    SanPham.objects.create(danh_muc=dm1, ten_sp="Castrol Power 1", gia_tham_khao=120000, anh_sp="https://cf.shopee.vn/file/49a6224168e3708304f5533139855584", mo_ta="Dầu nhớt tổng hợp toàn phần")
    SanPham.objects.create(danh_muc=dm2, ten_sp="Nước làm mát", gia_tham_khao=50000, anh_sp="https://bizweb.dktcdn.net/100/416/542/products/nuoc-lam-mat-dong-co-o-to-xe-may-mau-xanh-blue-fobe-super-coolant-500ml-lon-p523a1.jpg", mo_ta="Giải nhiệt động cơ")

# ===================================================================
    # 5. TẠO DỮ LIỆU HÓA ĐƠN LỊCH SỬ TRONG 365 NGÀY QUA (MỚI THÊM)
    # ===================================================================
    now = timezone.now()
    bang_gia = {'A95': 24500, 'E5': 23500, 'DO': 21000}
    loai_list = ['A95', 'E5', 'DO']
    
    # Lặp qua từng ngày trong 365 ngày qua
    for i in range(365):
        fake_date = now - timedelta(days=i)
        
        # Random tạo từ 2 đến 6 hóa đơn mỗi ngày (Tạo tính dao động thực tế)
        so_khach_trong_ngay = random.randint(2, 6)
        
        for j in range(so_khach_trong_ngay):
            loai_nl = random.choice(loai_list)
            don_gia = bang_gia[loai_nl]
            # Random khách đổ từ 20 Lít đến 150 Lít
            so_lit = random.uniform(20, 150)
            tong_tien = so_lit * don_gia
            
            # 1. Tạo Hóa Đơn
            hd = HoaDon.objects.create(
                ma_hd=f"HD-{str(uuid.uuid4())[:8].upper()}",
                nhan_vien=request.user,  # Gán cho tài khoản admin hiện tại
                tong_tien=tong_tien
            )
            # MẸO QUAN TRỌNG: Cập nhật lại thời gian bằng hàm update() 
            # để lách qua thuộc tính auto_now_add của Django
            HoaDon.objects.filter(id=hd.id).update(thoi_gian=fake_date)
            
            # 2. Tạo Chi Tiết Hóa Đơn
            ChiTietHoaDon.objects.create(
                hoa_don=hd,
                ten_mat_hang=f"Xăng {loai_nl}",
                so_luong=so_lit,
                don_gia=don_gia,
                thanh_tien=tong_tien
            )
            
    messages.success(request, "Đã khởi tạo 15 Trạm Xăng, 4 Kho hàng và dữ liệu mẫu thành công!")
    return redirect('admin_dashboard')