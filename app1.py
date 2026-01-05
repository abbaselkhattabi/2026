import streamlit as st
from PIL import Image, ImageEnhance, ImageOps
import requests
from io import BytesIO
import os

# --- الإعدادات القطعية ---
WP_URL = "https://driouchcity.com/wp-json/wp/v2"
WP_USER = "ADMIN"
WP_PASS = st.secrets["WP_PASSWORD"]

# التصنيفات المطلوبة
CAT_DRIOUCH = 55
CAT_MAIN = 350

def force_post_to_draft(processed_img, news_title, news_content):
    """وظيفة الإرسال الإجباري كمسودة مع التنسيقات الصارمة"""
    
    # قلب الصورة إجبارياً كما طلبت
    flipped_img = ImageOps.mirror(processed_img)
    
    buf = BytesIO()
    flipped_img.save(buf, format="JPEG", quality=85)
    
    # 1. رفع الصورة
    m_res = requests.post(
        f"{WP_URL}/media", 
        headers={"Content-Disposition": "attachment; filename=driouch_photo.jpg", "Content-Type": "image/jpeg"},
        auth=(WP_USER, WP_PASS), 
        data=buf.getvalue()
    )
    
    if m_res.status_code == 201:
        img_id = m_res.json()['id']
        
        # 2. هندسة النص (السطر الأول H3 والباقي فقرات)
        lines = [l.strip() for l in news_content.split('\n') if l.strip()]
        if not lines: return False
        
        # تحويل السطر الأول لترويسة 3 والباقي لفقرات
        h3_header = f"<h3 style='text-align: right; direction: rtl;'>{lines[0]}</h3>"
        paragraphs = "".join([f"<p style='text-align: right; direction: rtl;'>{p}</p>" for p in lines[1:]])
        final_html = h3_header + paragraphs
        
        # 3. إرسال البيانات كمسودة حصراً
        data_payload = {
            "title": news_title,
            "content": final_html,
            "featured_media": img_id,
            "status": "draft",  # هذه الكلمة تضمن عدم النشر العلني
            "categories": [CAT_DRIOUCH, CAT_MAIN],
            "meta": {
                "_yoast_wpseo_focuskw": "الدريوش",
                "rank_math_focus_keyword": "الدريوش"
            }
        }
        
        p_res = requests.post(f"{WP_URL}/posts", auth=(WP_USER, WP_PASS), json=data_payload)
        return p_res.status_code == 201
    return False

# --- الواجهة البرمجية المتفاعلة ---
st.set_page_config(page_title="محرر الدريوش سيتي - تحديث إجباري", layout="centered")
st.header("🗞️ محرر المسودات (تحديث صارم)")

uploaded_file = st.file_uploader("ارفع الصورة (سيتم قلبها تلقائياً)", type=["jpg","jpeg","png","webp"])

if uploaded_file:
    raw_image = Image.open(uploaded_file)
    
    # عرض معاينة مقلوبة لتأكيد التفاعل
    st.image(ImageOps.mirror(raw_image), caption="معاينة الصورة المقلوبة", use_container_width=True)
    
    # المدخلات
    post_title = st.text_input("عنوان الخبر الرئيسي")
    post_body = st.text_area("نص الخبر (تذكر: السطر الأول سيصبح H3)", height=300)
    
    if st.button("🚀 إرسال كمسودة إلى الموقع"):
        if post_title and post_body:
            with st.spinner("جاري المعالجة والإرسال للمسودات..."):
                if force_post_to_draft(raw_image, post_title, post_body):
                    st.success("✅ تم الحفظ كمسودة بنجاح في قسم الدريوش والرئيسية.")
                    st.balloons()
                else:
                    st.error("❌ حدث خطأ. تأكد من إعدادات الموقع أو كلمة المرور.")
        else:
            st.warning("يرجى ملء كافة البيانات.")
