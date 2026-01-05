import streamlit as st
from PIL import Image, ImageEnhance, ImageOps
import requests
from io import BytesIO
import os

# --- إعدادات الاتصال بموقعك ---
URL = "https://driouchcity.com/wp-json/wp/v2"
USER = "ADMIN"
# تأكد من وضع كلمة المرور في إعدادات Secrets في موقع Streamlit وليس هنا
PASS = st.secrets["WP_PASSWORD"]

def add_watermark(base_image):
    """إضافة الشعار من ملف باسم logo.png موجود في GitHub"""
    try:
        if os.path.exists("logo.png"):
            logo = Image.open("logo.png").convert("RGBA")
            base_image = base_image.convert("RGBA")
            width, height = base_image.size
            # حجم الشعار 15% من عرض الصورة
            logo_w = int(width * 0.15)
            w_percent = (logo_w / float(logo.size[0]))
            logo_h = int((float(logo.size[1]) * float(w_percent)))
            logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            # وضع الشعار في الزاوية اليمنى السفلى
            base_image.paste(logo, (width - logo_w - 20, height - logo_h - 20), mask=logo)
            return base_image.convert("RGB")
        return base_image
    except:
        return base_image

def post_to_wp(img, t, c):
    """رفع الصورة أولاً ثم ربطها بالمقال لضمان عدم فقدانها"""
    buf = BytesIO()
    # جودة 85% لضمان سرعة تصفح موقعك
    img.save(buf, format="JPEG", quality=85)
    
    # 1. رفع الصورة إلى مكتبة الوسائط
    res_m = requests.post(f"{URL}/media", 
                         headers={"Content-Disposition":"attachment; filename=driouch_news.jpg","Content-Type":"image/jpeg"},
                         auth=(USER, PASS), data=buf.getvalue())
    
    if res_m.status_code == 201:
        mid = res_m.json()['id']
        # 2. حل مشكلة الفقرات عبر HTML
        html_content = "".join([f"<p style='text-align: right;'>{p}</p>" for p in c.split('\n') if p.strip()])
        
        # 3. إرسال المقال كاملاً مع الصورة البارزة
        payload = {
            "title": t,
            "content": html_content,
            "featured_media": mid,
            "status": "publish"
        }
        res_p = requests.post(f"{URL}/posts", auth=(USER, PASS), json=payload)
        return res_p.status_code == 201
    return False

# --- واجهة التطبيق ---
st.set_page_config(page_title="محرر الدريوش سيتي", page_icon="🗞️")
st.title("🗞️ محرر ونشر أخبار الدريوش سيتي")

# شريط جانبي للمعلومات
st.sidebar.info("تأكد من رفع ملف logo.png إلى GitHub ليظهر الشعار تلقائياً.")

src = st.radio("مصدر الصورة:", ["من جهازي", "رابط خارجي"], horizontal=True)
raw = None

if src == "من جهازي":
    f = st.file_uploader("اختر الصورة", type=["jpg","png","jpeg"])
    if f: raw = Image.open(f)
else:
    u = st.text_input("ضع رابط الصورة المباشر")
    if u:
        try: raw = Image.open(BytesIO(requests.get(u).content))
        except: st.error("رابط الصورة غير صحيح أو لا يمكن الوصول إليه.")

if raw:
    st.divider()
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.subheader("⚙️ تعديلات")
        sat = st.slider("تشبع الألوان", 0.0, 2.0, 1.0)
        bri = st.slider("درجة الإضاءة", 0.0, 2.0, 1.0)
        apply_logo = st.checkbox("إضافة شعار الموقع", value=True)
        if st.button("قلب الصورة ↔️"): raw = ImageOps.mirror(raw)
        
    img = ImageEnhance.Color(raw).enhance(sat)
    img = ImageEnhance.Brightness(img).enhance(bri)
    if apply_logo:
        img = add_watermark(img)
        
    with col1:
        st.image(img, use_container_width=True, caption="معاينة الصورة قبل النشر")

    st.divider()
    t_in = st.text_input("عنوان الخبر")
    c_in = st.text_area("نص الخبر (اضغط Enter بين الفقرات)", height=250)
    
    # عداد الكلمات
    words = len(c_in.split())
    st.caption(f"عدد الكلمات: {words}")

    if st.button("🚀 انشر الآن على الموقع"):
        if t_in and c_in:
            with st.spinner("جاري رفع الصورة ونشر المقال..."):
                if post_to_wp(img, t_in, c_in):
                    st.success("✅ تم النشر بنجاح! المقال متاح الآن على DriouchCity.com")
                else:
                    st.error("❌ فشل النشر. تأكد من كلمة مرور التطبيق (Secrets) وتوافر مساحة على موقعك.")
        else:
            st.warning("يرجى ملء العنوان ونص الخبر قبل الضغط على نشر.")