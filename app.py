import streamlit as st
from PIL import Image, ImageOps
import requests
from io import BytesIO

# --- إعدادات الربط ---
# تأكد من وضع كلمة المرور في Secrets باسم WP_PASSWORD
WP_URL = "https://driouchcity.com/wp-json/wp/v2"
WP_USER = "ADMIN"

def post_as_draft(img, title, content):
    try:
        WP_PASS = st.secrets["WP_PASSWORD"]
        # 1. قلب الصورة إجبارياً
        img = ImageOps.mirror(img)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        
        # 2. رفع الصورة
        m_res = requests.post(
            f"{WP_URL}/media", 
            headers={"Content-Disposition": "attachment; filename=d_news.jpg", "Content-Type": "image/jpeg"},
            auth=(WP_USER, WP_PASS), data=buf.getvalue(), timeout=30
        )
        
        if m_res.status_code == 201:
            img_id = m_res.json()['id']
            
            # 3. تنسيق النص (أول سطر H3 والباقي فقرات)
            lines = [l.strip() for l in content.split('\n') if l.strip()]
            if not lines: return False
            
            h3_part = f"<h3 style='text-align: right; direction: rtl;'>{lines[0]}</h3>"
            body_part = "".join([f"<p style='text-align: right; direction: rtl;'>{p}</p>" for p in lines[1:]])
            
            # 4. إرسال المسودة
            payload = {
                "title": title,
                "content": h3_part + body_part,
                "featured_media": img_id,
                "status": "draft",
                "categories": [55, 350],
                "meta": {
                    "_yoast_wpseo_focuskw": "الدريوش",
                    "rank_math_focus_keyword": "الدريوش"
                }
            }
            p_res = requests.post(f"{WP_URL}/posts", auth=(WP_USER, WP_PASS), json=payload, timeout=30)
            return p_res.status_code == 201
    except Exception as e:
        st.error(f"خطأ تقني: {e}")
    return False

# --- واجهة التطبيق (تأكد من عدم وجود مسافات قبل الأسطر التالية) ---
st.set_page_config(page_title="محرر الدريوش سيتي")
st.title("📝 محرر المسودات")

up = st.file_uploader("ارفع صورة الخبر", type=["jpg", "png", "jpeg"])

if up:
    image = Image.open(up)
    # معاينة الصورة المقلوبة للتأكد من استجابة التطبيق
    st.image(ImageOps.mirror(image), caption="المعاينة المقلوبة")
    
    t = st.text_input("عنوان المقال")
    c = st.text_area("نص المقال (السطر الأول H3)", height=250)
    
    if st.button("🚀 حفظ كمسودة"):
        if t and c:
            with st.spinner("جاري الإرسال للموقع..."):
                if post_as_draft(image, t, c):
                    st.success("✅ تم الحفظ في المسودات بنجاح!")
                else:
                    st.error("❌ فشل الإرسال، تحقق من كلمة المرور.")
        else:
            st.warning("يرجى ملء العنوان والنص.")
