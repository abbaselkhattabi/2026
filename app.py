import streamlit as st
from PIL import Image, ImageEnhance, ImageOps
import requests
from io import BytesIO
import os

# --- الإعدادات ---
WP_URL = "https://driouchcity.com/wp-json/wp/v2"
WP_USER = "ADMIN"
WP_PASS = st.secrets["WP_PASSWORD"]

def add_watermark(base_image):
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

def post_to_wp(img, title, h3_title, content):
    # قلب الصورة إجبارياً
    img = ImageOps.mirror(img)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    
    # 1. رفع الصورة
    m_res = requests.post(f"{WP_URL}/media", 
                         headers={"Content-Disposition":"attachment; filename=news.jpg","Content-Type":"image/jpeg"},
                         auth=(WP_USER, WP_PASS), data=buf.getvalue())
    
    if m_res.status_code == 201:
        mid = m_res.json()['id']
        
        # 2. بناء الـ HTML (الترويسة 3 منفصلة تماماً)
        full_html = f"<h3 style='text-align: right; direction: rtl;'>{h3_title}</h3>"
        for p in content.split('\n'):
            if p.strip():
                full_html += f"<p style='text-align: right; direction: rtl;'>{p.strip()}</p>"
        
        # 3. الإرسال كمسودة مع تصنيفات وسيو
        payload = {
            "title": title,
            "content": full_html,
            "featured_media": mid,
            "status": "draft",
            "categories": [55, 350],
            "meta": {
                "_yoast_wpseo_focuskw": "الدريوش",
                "rank_math_focus_keyword": "الدريوش"
            }
        }
        p_res = requests.post(f"{WP_URL}/posts", auth=(WP_USER, WP_PASS), json=payload)
        return p_res.status_code == 201
    return False

# --- الواجهة ---
st.set_page_config(page_title="محرر الدريوش سيتي الكامل")
st.title("🗞️ محرر الدريوش سيتي (المسودات)")

src = st.radio("مصدر الصورة:", ["رفع مباشر", "من رابط"], horizontal=True)
raw = None
headers = {'User-Agent': 'Mozilla/5.0'}

if src == "رفع مباشر":
    f = st.file_uploader("اختر صورة", type=["jpg","png","jpeg"])
    if f: raw = Image.open(f)
else:
    u = st.text_input("ضع رابط الصورة المباشر")
    if u:
        try:
            res = requests.get(u, headers=headers)
            raw = Image.open(BytesIO(res.content))
        except: st.error("لا يمكن جلب الصورة من هذا الرابط")

if raw:
    st.divider()
    col1, col2 = st.columns([2, 1])
    with col2:
        st.subheader("⚙️ تعديلات")
        sat = st.slider("تشبع الألوان", 0.0, 2.0, 1.0)
        bri = st.slider("الإضاءة", 0.0, 2.0, 1.0)
        apply_logo = st.checkbox("إضافة اللوغو", value=True)
    
    # معالجة الصورة (قلب المعاينة للتوضيح)
    img_edit = ImageEnhance.Color(raw).enhance(sat)
    img_edit = ImageEnhance.Brightness(img_edit).enhance(bri)
    if apply_logo: img_edit = add_watermark(img_edit)
    
    with col1:
        st.image(ImageOps.mirror(img_edit), caption="معاينة الصورة (مقلوبة تلقائياً)")

    st.divider()
    t_main = st.text_input("1️⃣ العنوان الرئيسي (يظهر في القائمة)")
    t_h3 = st.text_input("2️⃣ العنوان الفرعي (سيظهر كـ H3 في بداية المقال)")
    t_body = st.text_area("3️⃣ نص الخبر (فقرات عادية)", height=250)

    if st.button("🚀 إرسال المسودة للموقع"):
        if t_main and t_body:
            with st.spinner("جاري النشر كمسودة..."):
                if post_to_wp(img_edit, t_main, t_h3, t_body):
                    st.success("✅ تم الحفظ في المسودات (الرئيسية والدريوش) بنجاح!")
                else: st.error("❌ فشل الإرسال، تأكد من إعدادات الموقع.")
