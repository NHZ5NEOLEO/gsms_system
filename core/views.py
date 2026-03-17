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
from django.contrib.auth import get_user_model
User = get_user_model()

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

    # ========================================================
    # XỬ LÝ FORM NHẬP KHO (VÀ TỰ ĐỘNG ĐÓNG YÊU CẦU)
    # ========================================================
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
                # 1. Bơm xăng vào bồn
                bon.muc_hien_tai += so_lit
                bon.save()
                
                # 2. Tạo phiếu nhập
                PhieuNhap.objects.create(
                    ma_pn=f"PN-{timezone.now().strftime('%d%m%H%M')}",
                    nha_cung_cap_id=ncc_id,
                    bon_chua=bon,
                    so_lit_nhap=so_lit,
                    thanh_tien=so_lit * 22000
                )

                # 3. TỰ ĐỘNG TÌM VÀ ĐÓNG YÊU CẦU CỦA TRẠM NÀY (Nếu có)
                from .models import YeuCauNhapHang
                YeuCauNhapHang.objects.filter(
                    tram=bon.tram,
                    loai_nhien_lieu=bon.loai_nhien_lieu,
                    trang_thai='cho_duyet'
                ).update(trang_thai='da_duyet')

                messages.success(request, f"Đã nhập {so_lit:,.0f} lít vào {bon.ten_bon}. Yêu cầu của trạm (nếu có) đã được tự động phê duyệt!")
                return redirect('admin_dashboard')
        except Exception as e:
            messages.error(request, f"Lỗi nhập liệu: {e}")

    # ========================================================
    # LẤY DANH SÁCH YÊU CẦU ĐỂ HIỂN THỊ
    # ========================================================
    from .models import YeuCauNhapHang
    ds_yeu_cau = YeuCauNhapHang.objects.filter(trang_thai='cho_duyet').order_by('-thoi_gian')

    ds_ncc = NhaCungCap.objects.all()
    ds_bon = BonChua.objects.select_related('tram').all()

    ncc_list = [{
        'id': n.id, 'name': n.ten_ncc, 'lat': float(n.latitude or 0), 'lng': float(n.longitude or 0), 'address': n.dia_chi
    } for n in ds_ncc]

    tank_list = []
    station_dict = {}

    for b in ds_bon:
        phan_tram = round((b.muc_hien_tai / b.suc_chua_toi_da) * 100, 1) if b.suc_chua_toi_da > 0 else 0
        tank_list.append({
            'id': b.id, 'ten_bon': b.ten_bon, 'loai': b.get_loai_nhien_lieu_display(),
            'muc_hien_tai': float(b.muc_hien_tai), 'suc_chua': float(b.suc_chua_toi_da),
            'phan_tram': phan_tram, 'tram_id': b.tram.id
        })
        if b.tram.id not in station_dict:
            station_dict[b.tram.id] = {'id': b.tram.id, 'name': b.tram.ten_tram, 'lat': float(b.tram.latitude or 0), 'lng': float(b.tram.longitude or 0)}

    context = {
        'ds_ncc': ds_ncc, 'ncc_json': json.dumps(ncc_list), 'tank_json': json.dumps(tank_list),
        'station_json': json.dumps(list(station_dict.values())), 'ds_yeu_cau': ds_yeu_cau,
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

            tram_moi = TramXang.objects.create(
                ten_tram=ten_tram,
                dia_chi=dia_chi,
                latitude=float(lat),
                longitude=float(lng)
            )

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
    user = request.user
    
    if user.role == 'admin':
        return redirect('admin_dashboard')

    if not user.tram_xang:
        messages.error(request, "Tài khoản của bạn chưa được phân công về Trạm Xăng nào. Vui lòng liên hệ Admin!")
        return redirect('login')

    tram_cua_toi = user.tram_xang
    today = timezone.now().date()

    ds_bon = BonChua.objects.filter(tram=tram_cua_toi)

    if user.role == 'tram_truong':
        lich_su = HoaDon.objects.filter(nhan_vien__tram_xang=tram_cua_toi, thoi_gian__date=today).order_by('-thoi_gian')[:20]
    else:
        lich_su = HoaDon.objects.filter(nhan_vien=user, thoi_gian__date=today).order_by('-thoi_gian')[:10]

    context = {
        'tram': tram_cua_toi,
        'ds_bon': ds_bon,
        'lich_su_ban': lich_su,
    }
    return render(request, 'staff_pos.html', context)


@login_required
def xu_ly_ban_hang(request):
    if request.method == 'POST':
        if not request.user.tram_xang:
            messages.error(request, "Lỗi bảo mật: Bạn không thuộc trạm xăng nào!")
            return redirect('staff_pos')

        try:
            loai_nl = request.POST.get('loai_nhien_lieu')
            so_tien = float(request.POST.get('so_tien'))
            bang_gia = {'A95': 24500, 'E5': 23500, 'DO': 21000}
            don_gia = bang_gia.get(loai_nl, 20000)
            so_lit = so_tien / don_gia
            
            bon = BonChua.objects.filter(tram=request.user.tram_xang, loai_nhien_lieu=loai_nl).first()
            
            if bon and bon.muc_hien_tai >= so_lit:
                bon.muc_hien_tai -= so_lit
                bon.save()
                
                ma_hd_moi = f"HD-{timezone.now().strftime('%y%m%d%H%M%S')}-{request.user.id}"
                hd = HoaDon.objects.create(
                    ma_hd=ma_hd_moi,
                    nhan_vien=request.user,
                    tong_tien=so_tien
                )
                ChiTietHoaDon.objects.create(
                    hoa_don=hd,
                    ten_mat_hang=f"Nhiên liệu {loai_nl}",
                    so_luong=so_lit,
                    don_gia=don_gia,
                    thanh_tien=so_tien
                )
                
                messages.success(request, f"Đã xuất {so_lit:.2f}L {loai_nl} từ {request.user.tram_xang.ten_tram}")
            else:
                messages.error(request, "Trạm của bạn đã hết loại nhiên liệu này!")
                
        except Exception as e:
            messages.error(request, "Có lỗi xảy ra!")
            
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
    # CHỈ DÀNH CHO ADMIN
    if request.user.role != 'admin':
        return redirect('trang_chu')

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
    # 5. TẠO DỮ LIỆU HÓA ĐƠN LỊCH SỬ TRONG 365 NGÀY QUA
    # ===================================================================
    now = timezone.now()
    bang_gia = {'A95': 24500, 'E5': 23500, 'DO': 21000}
    loai_list = ['A95', 'E5', 'DO']
    
    for i in range(365):
        fake_date = now - timedelta(days=i)
        so_khach_trong_ngay = random.randint(2, 6)
        
        for j in range(so_khach_trong_ngay):
            loai_nl = random.choice(loai_list)
            don_gia = bang_gia[loai_nl]
            so_lit = random.uniform(20, 150)
            tong_tien = so_lit * don_gia
            
            hd = HoaDon.objects.create(
                ma_hd=f"HD-{str(uuid.uuid4())[:8].upper()}",
                nhan_vien=request.user, 
                tong_tien=tong_tien
            )
            HoaDon.objects.filter(id=hd.id).update(thoi_gian=fake_date)
            
            ChiTietHoaDon.objects.create(
                hoa_don=hd,
                ten_mat_hang=f"Xăng {loai_nl}",
                so_luong=so_lit,
                don_gia=don_gia,
                thanh_tien=tong_tien
            )

   # ===================================================================
    # 6. TẠO TÀI KHOẢN NHÂN VIÊN CHO 3 TRẠM XĂNG ĐỂ TEST PHÂN QUYỀN
    # ===================================================================
    cac_tram = TramXang.objects.all()

    if cac_tram.count() >= 3:
        # Xóa các tài khoản cũ để không bị lỗi trùng lặp khi bấm Reset nhiều lần
        User.objects.filter(username__in=[
            'truongtram1', 'nhanvien1',
            'truongtram2', 'nhanvien2',
            'truongtram3', 'nhanvien3'
        ]).delete()

        # --- TRẠM SỐ 1 ---
        tram_1 = cac_tram[0]
        User.objects.create_user(username='truongtram1', password='123', full_name='Trưởng Trạm Một', phone='0909111001', role='tram_truong', tram_xang=tram_1)
        User.objects.create_user(username='nhanvien1', password='123', full_name='Nhân Viên Một', phone='0909111002', role='staff', tram_xang=tram_1)

        # --- TRẠM SỐ 2 ---
        tram_2 = cac_tram[1]
        User.objects.create_user(username='truongtram2', password='123', full_name='Trưởng Trạm Hai', phone='0909222001', role='tram_truong', tram_xang=tram_2)
        User.objects.create_user(username='nhanvien2', password='123', full_name='Nhân Viên Hai', phone='0909222002', role='staff', tram_xang=tram_2)

        # --- TRẠM SỐ 3 ---
        tram_3 = cac_tram[2]
        User.objects.create_user(username='truongtram3', password='123', full_name='Trưởng Trạm Ba', phone='0909333001', role='tram_truong', tram_xang=tram_3)
        User.objects.create_user(username='nhanvien3', password='123', full_name='Nhân Viên Ba', phone='0909333002', role='staff', tram_xang=tram_3)

    # ĐÂY LÀ DÒNG BÁO THÀNH CÔNG VÀ CHUYỂN TRANG CUỐI CÙNG (CỰC KỲ QUAN TRỌNG)
    messages.success(request, "Đã khởi tạo 15 Trạm Xăng, 4 Kho hàng, dữ liệu mẫu và 6 Tài khoản nhân viên test thành công!")
    return redirect('admin_dashboard')

@login_required
def bao_cao_tram(request):
    user = request.user
    
    # Chỉ Trạm trưởng mới được xem
    if user.role != 'tram_truong':
        messages.error(request, "Lỗi bảo mật: Chỉ Cửa hàng trưởng mới có quyền xem Báo cáo Trạm!")
        return redirect('staff_pos')

    tram = user.tram_xang
    if not tram:
        messages.error(request, "Tài khoản của bạn chưa gắn với Trạm nào!")
        return redirect('staff_pos')

    today = timezone.now().date()
    
    # 1. Thống kê Doanh thu & Sản lượng của TẤT CẢ nhân viên trong trạm (Hôm nay)
    hds_hom_nay = HoaDon.objects.filter(nhan_vien__tram_xang=tram, thoi_gian__date=today)
    doanh_thu_hom_nay = hds_hom_nay.aggregate(Sum('tong_tien'))['tong_tien__sum'] or 0
    so_gd_hom_nay = hds_hom_nay.count()
    
    san_luong_hom_nay = ChiTietHoaDon.objects.filter(hoa_don__in=hds_hom_nay).aggregate(Sum('so_luong'))['so_luong__sum'] or 0

    # 2. Thống kê Tồn kho hiện tại của Trạm
    ds_bon = BonChua.objects.filter(tram=tram)

    # 3. Danh sách nhân viên và doanh thu từng người trong ngày
    doanh_thu_nhan_vien = HoaDon.objects.filter(
        nhan_vien__tram_xang=tram, thoi_gian__date=today
    ).values('nhan_vien__username', 'nhan_vien__full_name').annotate(
        tong_ban=Sum('tong_tien'),
        so_don=Count('id')
    ).order_by('-tong_ban')

    context = {
        'tram': tram,
        'ngay_bao_cao': timezone.now(),
        'doanh_thu_hom_nay': doanh_thu_hom_nay,
        'so_gd_hom_nay': so_gd_hom_nay,
        'san_luong_hom_nay': san_luong_hom_nay,
        'ds_bon': ds_bon,
        'doanh_thu_nhan_vien': doanh_thu_nhan_vien,
    }
    return render(request, 'bao_cao_tram.html', context)

# --- LOGIC GỬI VÀ DUYỆT YÊU CẦU NHẬP HÀNG ---
@login_required
def tao_yeu_cau_nhap(request):
    if request.method == 'POST' and request.user.role == 'tram_truong':
        loai_nl = request.POST.get('loai_nl')
        so_luong = request.POST.get('so_luong')
        ghi_chu = request.POST.get('ghi_chu', '')
        
        from .models import YeuCauNhapHang
        YeuCauNhapHang.objects.create(
            tram=request.user.tram_xang,
            nguoi_yeu_cau=request.user,
            loai_nhien_lieu=loai_nl,
            so_luong=so_luong,
            ghi_chu=ghi_chu
        )
        messages.success(request, f"Đã gửi yêu cầu cấp {so_luong}L {loai_nl} lên Giám đốc thành công!")
    return redirect('bao_cao_tram')

@login_required
def duyet_yeu_cau(request, req_id):
    if request.user.role == 'admin':
        from .models import YeuCauNhapHang
        yeu_cau = YeuCauNhapHang.objects.get(id=req_id)
        yeu_cau.trang_thai = 'da_duyet'
        yeu_cau.save()
        messages.success(request, f"Đã duyệt lệnh xuất hàng cho {yeu_cau.tram.ten_tram}! Vui lòng lập lộ trình GIS.")
    return redirect('admin_import')