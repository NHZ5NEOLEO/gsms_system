"""
Django settings for gsms_system project.
"""

from pathlib import Path
import os
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-87q8&5h5(q)(_ktvq#y%fs5hwk%ghm5$53-@gee%)l5%d79+2%'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'core', # App của bạn
    # --- THÊM DÒNG NÀY VÀO ---
    'django.contrib.sites',
    # --- THÊM CÁC APP CỦA ALLAUTH (CHO GOOGLE LOGIN) ---
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # --- THÊM MIDDLEWARE NÀY CỦA ALLAUTH ---
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'gsms_system.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], # Đảm bảo trỏ đúng thư mục templates
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'gsms_system.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

# CẤU HÌNH CŨ (ẨN ĐI ĐỂ DÀNH):
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# ==========================================
# CẤU HÌNH MỚI: SỬ DỤNG POSTGRESQL CHUẨN ERP
# ==========================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'gsms_db',                  # Tên Database bạn vừa tạo ở Bước 2
        'USER': 'postgres',                 # Tên User của PostgreSQL (thường là postgres)
        'PASSWORD': '123456',# Mật khẩu phần mềm PostgreSQL của bạn
        'HOST': 'localhost',                # Chạy trên máy cá nhân
        'PORT': '5432',                     # Cổng mặc định của PostgreSQL
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

# --- CẬP NHẬT: Ngôn ngữ và Múi giờ ---
LANGUAGE_CODE = 'vi'        # Chuyển sang Tiếng Việt
TIME_ZONE = 'Asia/Ho_Chi_Minh' # Chuyển sang giờ Việt Nam (GMT+7)

USE_I18N = True
USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/


MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# --- CẤU HÌNH TÙY CHỈNH CHO DỰ ÁN ---

# 1. Sử dụng Model User tùy chỉnh trong core/models.py
AUTH_USER_MODEL = 'core.User'

# 2. Fix lỗi cảnh báo Auto-created primary key (models.W042)
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 3. Cấu hình đường dẫn Đăng nhập
LOGIN_URL = 'login' 

# 4. Đường dẫn mặc định sau khi đăng nhập (Fallback)
# Lưu ý: Logic chính xác đã được xử lý trong views.dang_nhap (Admin -> Dashboard, Staff -> POS)
LOGIN_REDIRECT_URL = 'trang_chu'

# ==========================================
# CẤU HÌNH GỬI EMAIL QUA MAILTRAP
# ==========================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'sandbox.smtp.mailtrap.io'
EMAIL_PORT = 2525
EMAIL_HOST_USER = '390a3a82b26538'
EMAIL_HOST_PASSWORD = '79b67f907907d0'
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = 'noreply@gsms.com' # Email gửi mặc định

STATIC_URL = '/static/'

# THÊM ĐOẠN NÀY VÀO: Chỉ cho Django biết thư mục static của bạn nằm ở đâu
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
# ==========================================
# CẤU HÌNH ĐĂNG NHẬP BẰNG GOOGLE (ALLAUTH)
# ==========================================
AUTHENTICATION_BACKENDS = [
    # Đăng nhập bằng username/password bình thường của hệ thống
    'django.contrib.auth.backends.ModelBackend',
    # Xác thực qua Google của allauth
    'allauth.account.auth_backends.AuthenticationBackend',
]

# ID của trang web (Bắt buộc phải có đối với allauth)
SITE_ID = 1 

# --- Tối ưu hóa trải nghiệm (UX) cho khách hàng ---
ACCOUNT_EMAIL_VERIFICATION = 'none' # Khách không cần check mail để xác thực rườm rà
ACCOUNT_LOGIN_METHODS = {'username', 'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
SOCIALACCOUNT_LOGIN_ON_GET = True # Bấm nút Google là tự động đăng nhập luôn, không bắt xác nhận lần 2

# --- Cấu hình riêng cho nhà cung cấp Google ---
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        }
    }
}