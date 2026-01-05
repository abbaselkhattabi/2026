import streamlit as st
from PIL import Image, ImageEnhance, ImageOps
import requests
from io import BytesIO
import os

# --- الإعدادات ---
URL = "https://driouchcity.com/wp-json/wp/v2"
USER = "ADMIN"
PASS = st.secrets["WP_PASSWORD"]

# الأرقام التي زودتني بها
CAT_MAIN = 350    # الرئيسية
CAT_DRIOUCH = 55  # الدريوش

def add_watermark(base_image):
    """إضافة الشعار من ملف logo.png"""
    if os.path.exists("logo.png"):
        try:
            logo = Image.open("logo.png").convert("RGBA")
            base_image = base_image.convert("RGBA")
            width, height = base_image.size
            logo_w = int(width * 0.18)
            w_percent = (logo_w / float(logo.size[0]))
            logo_h = int((float(logo.size[1]) * float(w_percent)))
            logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            base_image.paste(logo, (width - logo_w - 25, height - logo_h - 25), mask=logo)
            return base_image.convert("RGB")
        except: return base_image
    return base_image

def post_to_wp_draft(img, title, content):
    """إرسال المقال كمسودة مع التنسيقات المطلوبة"""
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    
    # 1. رفع الصورة أولاً
    media_res = requests.post(
        f"{URL}/media", 
        headers={"Content-Disposition": "attachment; filename=driouch_news.jpg", "Content-Type": "image/jpeg"},
        auth=(USER, PASS), 
        data=buf.getvalue()
    )
    
    if media_res.status_code == 201:
        media_id = media_res.json()['id']
        
        # 2. معالجة النص: السطر الأول ترويسة 3 والباقي فقرات
        lines = content.split('\n')
        h3_title = lines[0].strip() if lines else ""
        rest_of_body = lines[1:] if len(lines) > 1 else []
        
        # بناء محتوى HTML مع ضبط الاتجاه من اليمين لليسار
        html_content = f"<h3 style='text-align: right; direction: rtl;'>{h3_title}</h3>"
        for p in rest_of_body:
            if p.strip():
                html_content += f"<p style='text-align: right; direction: rtl;'>{p.strip()}</p>"
        
        # 3. إعداد بيانات المقال (مسودة + تصنيفات + SEO)
        payload = {
            "title": title,
            "content": html_content,
            "featured_media": media_id,
            "status": "draft",  # حفظ كمسودة
            "categories": [CAT_MAIN, CAT_DRIOUCH], # التصنيفات التلقائية
            "meta": {
                "_yoast_wpseo_focuskw": "الدريوش", # للـ Yoast SEO
                "rank_math_focus_keyword": "الدريوش" # للـ Rank Math SEO
            }
        }
        
        post_res = requests.post(f"{URL}/posts", auth=(USER, PASS), json=payload)
        return post_res.status_code == 201
    return False

# --- واجهة التطبيق ---
st.set_page_config(page_title="محرر الدريوش سيتي", page_icon="📝")
st.title("📝 محرر المسودات - الدريوش سيتي")

# مصدر الصورة
src = st.radio("مصدر الصورة:", ["رابط مباشر", "رفع من جهازي"], horizontal=True)
raw = None
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36'}

if src == "رابط مباشر":
    u = st.text_input("ضع رابط الصورة المباشر")
    if u:
        try:
            res = requests.get(u, headers=headers)
            raw = Image.open(BytesIO(res.content))
        except: st.error("فشل جلب الصورة من الرابط")
else:
    f = st.file_uploader("اختر صورة", type=["jpg","png","jpeg","webp"])
    if f: raw = Image.open(f)

if raw:
    st.divider()
    col1, col2 = st.columns([2, 1])
    with col2:
        st.subheader("⚙️ تعديل")
        sat = st.slider("الألوان", 0.0, 2.0, 1.0)
        bri = st.slider("الإضاءة", 0.0, 2.0, 1.0)
        apply_logo = st.checkbox("إضافة الشعار", value=True)
    
    img_ready = ImageEnhance.Color(raw).enhance(sat)
    img_ready = ImageEnhance.Brightness(img_ready).enhance(bri)
    if apply_logo: img_ready = add_watermark(img_ready)
    
    with col1:
        st.image(img_ready, use_container_width=True)

    t_in = st.text_input("العنوان الأساسي")
    st.info("💡 ملاحظة: أول سطر تكتبه في الأسفل سيتحول تلقائياً إلى ترويسة H3")
    c_in = st.text_area("نص الخبر (السطر الأول = ترويسة 3)", height=250)

    if st.button("💾 إرسال إلى المسودات"):
        if t_in and c_in:
            with st.spinner("جاري الحفظ في موقعك..."):
                if post_to_wp_draft(img_ready, t_in, c_in):
                    st.success("🎉 نجاح! المقال محفوظ الآن كمسودة في قسم الرئيسية والدريوش.")
                else:
                    st.error("❌ فشل الإرسال. تأكد من كلمة المرور في Secrets.")
        else:
            st.warning("الرجاء إكمال العنوان والنص.")
