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

def post_to_wp(img, title, h3_sub, content):
    # 1. قلب الصورة إجبارياً (Mirror)
    img = ImageOps.mirror(img)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    
    # 2. رفع الصورة
    m_res = requests.post(f"{WP_URL}/media", 
                         headers={"Content-Disposition":"attachment; filename=news.jpg","Content-Type":"image/jpeg"},
                         auth=(WP_USER, WP_PASS), data=buf.getvalue())
    
    if m_res.status_code == 201:
        mid = m_res.json()['id']
        
        # 3. هندسة النص: الفقرة الأولى -> العنوان الفرعي H3 -> باقي الفقرات
        paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
        first_p = f"<p style='text-align: right; direction: rtl;'>{paragraphs[0]}</p>" if paragraphs else ""
        h3_part = f"<h3 style='text-align: right; direction: rtl;'>{h3_sub}</h3>" if h3_sub else ""
        rest_p = "".join([f"<p style='text-align: right; direction: rtl;'>{p}</p>" for p in paragraphs[1:]])
        
        full_html = first_p + h3_part + rest_p
        
        # 4. الإرسال كمسودة
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
st.set_page_config(page_title="محرر الدريوش سيتي برو", layout="wide")
st.title("🗞️ محرر الدريوش سيتي المتطور")

up_file = st.file_uploader("اختر صورة الخبر", type=["jpg","png","jpeg"])
raw = None

if up_file:
    raw = Image.open(up_file)

if raw:
    st.divider()
    col_tools, col_view = st.columns([1, 1.5])
    
    with col_tools:
        st.subheader("🛠️ أدوات التعديل")
        
        # ميزة القص (Crop)
        width, height = raw.size
        st.write(f"المقاس الحالي: {width}x{height}")
        left = st.number_input("القص من اليسار", 0, width, 0)
        top = st.number_input("القص من الأعلى", 0, height, 0)
        right = st.number_input("القص من اليمين", 0, width, width)
        bottom = st.number_input("القص من الأسفل", 0, height, height)
        
        # الألوان والإضاءة
        sat = st.slider("تشبع الألوان", 0.0, 2.0, 1.0)
        bri = st.slider("الإضاءة", 0.0, 2.0, 1.0)
        apply_logo = st.checkbox("إضافة اللوغو", value=True)
    
    # تطبيق العمليات
    img_edit = raw.crop((left, top, right, bottom))
    img_edit = ImageEnhance.Color(img_edit).enhance(sat)
    img_edit = ImageEnhance.Brightness(img_edit).enhance(bri)
    if apply_logo: img_edit = add_watermark(img_edit)
    
    with col_view:
        # عرض المعاينة مقلوبة للتأكيد
        st.image(ImageOps.mirror(img_edit), caption="معاينة نهائية (مقلوبة إجبارياً)")

    st.divider()
    t_main = st.text_input("عنوان المقال")
    t_h3 = st.text_input("العنوان الفرعي (H3) - سيظهر بعد الفقرة الأولى")
    t_body = st.text_area("نص المقال (اكتب الفقرة الأولى أولاً ثم البقية)", height=300)

    if st.button("🚀 حفظ كمسودة احترافية"):
        if t_main and t_body:
            with st.spinner("جاري الإرسال..."):
                if post_to_wp(img_edit, t_main, t_h3, t_body):
                    st.success("✅ تم الحفظ بنجاح! السطر الأول نُشر كفقرة، ثم تلاه العنوان الفرعي، ثم باقي الخبر.")
                else: st.error("❌ فشل الإرسال.")
