import streamlit as st
from PIL import Image, ImageEnhance, ImageOps
import requests
from io import BytesIO
import os

# --- الإعدادات ---
URL = "https://driouchcity.com/wp-json/wp/v2"
USER = "ADMIN"
PASS = st.secrets["WP_PASSWORD"]

# حدد هنا أرقام التصنيفات (ID) الخاصة بموقعك
# يمكنك معرفتها من لوحة تحكم ووردبريس (تصنيفات)
CAT_MAIN = 1      # رقم تصنيف "الرئيسية"
CAT_DRIOUCH = 5   # رقم تصنيف "الدريوش"

def post_to_wp_draft(img, title, content):
    """إرسال المقال كمسودة مع التنسيقات المطلوبة"""
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    
    # 1. رفع الصورة أولاً
    media_res = requests.post(
        f"{URL}/media", 
        headers={"Content-Disposition": "attachment; filename=news_img.jpg", "Content-Type": "image/jpeg"},
        auth=(USER, PASS), 
        data=buf.getvalue()
    )
    
    if media_res.status_code == 201:
        media_id = media_res.json()['id']
        
        # 2. معالجة النص: السطر الأول H3 والباقي فقرات
        lines = content.split('\n')
        h3_title = lines[0] if lines else ""
        rest_of_body = lines[1:] if len(lines) > 1 else []
        
        # بناء محتوى HTML
        html_content = f"<h3 style='text-align: right; direction: rtl;'>{h3_title}</h3>"
        for p in rest_of_body:
            if p.strip():
                html_content += f"<p style='text-align: right; direction: rtl;'>{p}</p>"
        
        # 3. إعداد بيانات المقال (مسودة + تصنيفات + SEO)
        payload = {
            "title": title,
            "content": html_content,
            "featured_media": media_id,
            "status": "draft",           # حفظ كمسودة
            "categories": [CAT_MAIN, CAT_DRIOUCH], # التصنيفات التلقائية
            "meta": {
                "_yoast_wpseo_focuskw": "الدريوش", # إضافة الكلمة المفتاحية لـ Yoast SEO
                "rank_math_focus_keyword": "الدريوش" # إضافة الكلمة المفتاحية لـ Rank Math
            }
        }
        
        post_res = requests.post(f"{URL}/posts", auth=(USER, PASS), json=payload)
        return post_res.status_code == 201
    return False

# --- الواجهة ---
st.set_page_config(page_title="محرر الدريوش سيتي", page_icon="📝")
st.title("📝 محرر المسودات الذكي - الدريوش سيتي")

# مصدر الصورة
src = st.radio("مصدر الصورة:", ["رفع من جهازي", "رابط مباشر"], horizontal=True)
raw = None
if src == "رفع من جهازي":
    f = st.file_uploader("اختر صورة", type=["jpg","png","jpeg"])
    if f: raw = Image.open(f)
else:
    u = st.text_input("رابط الصورة المباشر")
    if u:
        res = requests.get(u, headers={'User-Agent': 'Mozilla/5.0'})
        raw = Image.open(BytesIO(res.content))

if raw:
    st.divider()
    col1, col2 = st.columns([2, 1])
    with col2:
        st.subheader("⚙️ تعديل")
        sat = st.slider("الألوان", 0.0, 2.0, 1.0)
        bri = st.slider("الإضاءة", 0.0, 2.0, 1.0)
        apply_logo = st.checkbox("إضافة الشعار", value=True)
    
    img_final = ImageEnhance.Color(raw).enhance(sat)
    img_final = ImageEnhance.Brightness(img_final).enhance(bri)
    
    with col1:
        st.image(img_final, use_container_width=True)

    t_in = st.text_input("العنوان الأساسي (يظهر في القائمة)")
    st.info("💡 ملاحظة: أول سطر في المربع أدناه سيظهر كعنوان فرعي (H3) داخل المقال.")
    c_in = st.text_area("نص الخبر (السطر الأول = ترويسة 3)", height=250)

    if st.button("💾 حفظ كمسودة الآن"):
        if t_in and c_in:
            with st.spinner("جاري الإرسال لموقعك..."):
                if post_to_wp_draft(img_final, t_in, c_in):
                    st.success("✅ تم الحفظ بنجاح! المقال الآن في 'المسودات' داخل ووردبريس.")
                else:
                    st.error("❌ فشل الاتصال بالموقع.")
        else:
            st.warning("أدخل العنوان والنص")
