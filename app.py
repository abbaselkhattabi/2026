import streamlit as st
from PIL import Image, ImageEnhance, ImageOps
import requests
from io import BytesIO
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# --- الإعدادات الأساسية ---
URL = "https://driouchcity.com/wp-json/wp/v2"
USER = "ADMIN"
PASS = st.secrets["WP_PASSWORD"]

# --- الدوال البرمجية ---

@st.cache_data(ttl=600) # تحديث القائمة كل 10 دقائق
def get_categories():
    """جلب قائمة الأقسام من ووردبريس تلقائياً"""
    try:
        res = requests.get(f"{URL}/categories", auth=(USER, PASS), params={"per_page": 100})
        if res.status_code == 200:
            return {cat['name']: cat['id'] for cat in res.json()}
    except:
        return {"عام": 1}
    return {"عام": 1}

def add_watermark(base_image):
    """إضافة الشعار المرفوع على GitHub"""
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

def post_to_wp(img, title, content, cat_id):
    """رفع الصورة وربطها بالمقال"""
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    
    # 1. رفع الصورة أولاً
    media_res = requests.post(
        f"{URL}/media", 
        headers={"Content-Disposition": "attachment; filename=news.jpg", "Content-Type": "image/jpeg"},
        auth=(USER, PASS), data=buf.getvalue()
    )
    
    if media_res.status_code == 201:
        media_id = media_res.json()['id']
        # 2. تنسيق الفقرات (HTML)
        html_content = "".join([f"<p style='text-align: right; direction: rtl;'>{p}</p>" for p in content.split('\n') if p.strip()])
        
        # 3. إنشاء المقال وربطه بالصورة
        payload = {
            "title": title,
            "content": html_content,
            "featured_media": media_id,
            "categories": [cat_id],
            "status": "publish"
        }
        post_res = requests.post(f"{URL}/posts", auth=(USER, PASS), json=payload)
        return post_res.status_code == 201
    return False

# --- واجهة التطبيق ---
st.set_page_config(page_title="محرر الدريوش سيتي", layout="wide")
st.title("🗞️ محرر ونشر أخبار الدريوش سيتي")

# شريط جانبي للأقسام
st.sidebar.header("📂 إعدادات الخبر")
categories_dict = get_categories()
selected_cat_name = st.sidebar.selectbox("اختر القسم:", list(categories_dict.keys()))
selected_cat_id = categories_dict[selected_cat_name]

# مصدر الصورة
src = st.radio("مصدر الصورة:", ["رابط مباشر (لهسبريس)", "رفع من جهازي", "جلب من رابط مقال"], horizontal=True)
raw_img = None
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36'}

if src == "رابط مباشر (لهسبريس)":
    u = st.text_input("ضع رابط الصورة المباشر (.jpg / .webp)")
    if u:
        try:
            res = requests.get(u, headers=headers)
            raw_img = Image.open(BytesIO(res.content))
        except: st.error("فشل جلب الرابط المباشر")

elif src == "رفع من جهازي":
    f = st.file_uploader("اختر صورة", type=["jpg", "png", "jpeg", "webp"])
    if f: raw_img = Image.open(f)

else:
    u_art = st.text_input("ضع رابط المقال الإخباري")
    if u_art:
        try:
            res = requests.get(u_art, headers=headers)
            soup = BeautifulSoup(res.text, 'html.parser')
            img_tag = soup.find("meta", property="og:image")
            if img_tag:
                img_res = requests.get(img_tag["content"], headers=headers)
                raw_img = Image.open(BytesIO(img_res.content))
            else: st.error("لم نجد صورة بارزة في المقال")
        except: st.error("الموقع المصدر حظر عملية الجلب")

if raw_img:
    st.divider()
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.subheader("⚙️ تعديلات")
        sat = st.slider("الألوان", 0.0, 2.0, 1.0)
        bri = st.slider("الإضاءة", 0.0, 2.0, 1.0)
        apply_logo = st.checkbox("إضافة شعار الموقع", value=True)
        if st.button("قلب الصورة ↔️"): raw_img = ImageOps.mirror(raw_img)
    
    # معالجة الصورة
    proc_img = ImageEnhance.Color(raw_img).enhance(sat)
    proc_img = ImageEnhance.Brightness(proc_img).enhance(bri)
    if apply_logo: proc_img = add_watermark(proc_img)
    
    with col1: st.image(proc_img, use_container_width=True, caption="المعاينة النهائية")

    st.divider()
    title_in = st.text_input("عنوان الخبر")
    text_in = st.text_area("نص الخبر (استخدم Enter للفقرات)", height=250)
    
    if st.button("🚀 انشر الآن على الموقع"):
        if title_in and text_in:
            with st.spinner("جاري النشر..."):
                if post_to_wp(proc_img, title_in, text_in, selected_cat_id):
                    st.success("✅ تم النشر بنجاح مع الصورة البارزة في قسم: " + selected_cat_name)
                else: st.error("❌ فشل النشر - تحقق من إعدادات الموقع")
        else: st.warning("اكتب العنوان والنص أولاً")
