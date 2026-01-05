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

def add_watermark(base_image):
    """إضافة شعار الموقع logo.png من المجلد الرئيسي"""
    try:
        if os.path.exists("logo.png"):
            logo = Image.open("logo.png").convert("RGBA")
            base_image = base_image.convert("RGBA")
            width, height = base_image.size
            logo_w = int(width * 0.15)
            w_percent = (logo_w / float(logo.size[0]))
            logo_h = int((float(logo.size[1]) * float(w_percent)))
            logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            base_image.paste(logo, (width - logo_w - 20, height - logo_h - 20), mask=logo)
            return base_image.convert("RGB")
        return base_image
    except:
        return base_image

def post_to_wp(img, t, c):
    """رفع الصورة أولاً ثم نشر المقال لضمان الترابط والفقرات"""
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    
    # 1. رفع الصورة
    res_m = requests.post(f"{URL}/media", 
                         headers={"Content-Disposition":"attachment; filename=news_img.jpg","Content-Type":"image/jpeg"},
                         auth=(USER, PASS), data=buf.getvalue())
    
    if res_m.status_code == 201:
        mid = res_m.json()['id']
        # 2. حل مشكلة الفقرات (تحويل السطور إلى HTML)
        html_content = "".join([f"<p style='text-align: right;'>{p}</p>" for p in c.split('\n') if p.strip()])
        
        # 3. نشر المقال
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
st.set_page_config(page_title="محرر الدريوش سيتي الذكي", page_icon="🗞️")
st.title("🗞️ محرر ونشر أخبار الدريوش سيتي")

src = st.radio("مصدر الصورة:", ["رفع صورة من جهازي", "جلب من رابط مقال خارجي"], horizontal=True)
raw = None

if src == "رفع صورة من جهازي":
    f = st.file_uploader("اختر ملف الصورة", type=["jpg","png","jpeg"])
    if f: raw = Image.open(f)
else:
    u = st.text_input("ضع رابط المقال الإخباري هنا")
    if u:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            with st.spinner("جاري استخراج الصورة من المقال..."):
                response = requests.get(u, headers=headers, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # البحث عن الصورة البارزة في المقال
                img_tag = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
                img_url = img_tag["content"] if img_tag else None
                
                if not img_url: # محاولة إيجاد أول صورة كبيرة إذا فشل الـ meta
                    first_img = soup.find("img")
                    if first_img: img_url = first_img.get("src")

                if img_url:
                    img_url = urljoin(u, img_url) # توحيد الرابط
                    res_img = requests.get(img_url, headers=headers)
                    raw = Image.open(BytesIO(res_img.content))
                    st.success("✅ تم العثور على الصورة بنجاح!")
                else:
                    st.error("لم نتمكن من العثور على صورة في هذا الرابط.")
        except Exception as e:
            st.error(f"خطأ في الوصول للرابط: {e}")

if raw:
    st.divider()
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.subheader("⚙️ تعديل الصورة")
        sat = st.slider("الألوان", 0.0, 2.0, 1.0)
        bri = st.slider("الإضاءة", 0.0, 2.0, 1.0)
        apply_logo = st.checkbox("إضافة شعار الموقع", value=True)
        if st.button("قلب الصورة ↔️"): raw = ImageOps.mirror(raw)
        
    img = ImageEnhance.Color(raw).enhance(sat)
    img = ImageEnhance.Brightness(img).enhance(bri)
    if apply_logo:
        img = add_watermark(img)
        
    with col1:
        st.image(img, use_container_width=True, caption="معاينة نهائية")

    st.divider()
    t_in = st.text_input("عنوان الخبر")
    c_in = st.text_area("نص الخبر (استخدم Enter للفقرات)", height=250)
    
    st.caption(f"عدد الكلمات: {len(c_in.split())}")

    if st.button("🚀 انشر الآن على الموقع"):
        if t_in and c_in:
            with st.spinner("جاري النشر..."):
                if post_to_wp(img, t_in, c_in):
                    st.success("🎉 تم النشر بنجاح على DriouchCity.com")
                else:
                    st.error("❌ فشل النشر. تأكد من إعدادات الموقع وكلمة المرور.")
        else:
            st.warning("الرجاء إدخال العنوان والنص.")
