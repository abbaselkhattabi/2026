import streamlit as st
from PIL import Image, ImageEnhance, ImageOps
import requests
from io import BytesIO
import os

# --- الإعدادات ---
URL = "https://driouchcity.com/wp-json/wp/v2"
USER = "ADMIN"
PASS = st.secrets["WP_PASSWORD"]

# الأرقام المؤكدة
CAT_MAIN = 350    # الرئيسية
CAT_DRIOUCH = 55  # الدريوش

def post_to_wp_final(img, title, content):
    buf = BytesIO()
    # قلب الصورة إجبارياً كما طلبت
    img = ImageOps.mirror(img)
    img.save(buf, format="JPEG", quality=85)
    
    # 1. رفع الصورة
    res_m = requests.post(f"{URL}/media", 
                         headers={"Content-Disposition":"attachment; filename=d_img.jpg","Content-Type":"image/jpeg"},
                         auth=(USER, PASS), data=buf.getvalue())
    
    if res_m.status_code == 201:
        mid = res_m.json()['id']
        
        # 2. معالجة النص: السطر الأول H3 والباقي فقرات
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        h3_part = f"<h3 style='text-align: right; direction: rtl;'>{lines[0]}</h3>" if lines else ""
        body_part = "".join([f"<p style='text-align: right; direction: rtl;'>{p}</p>" for p in lines[1:]])
        
        full_html = h3_part + body_part
        
        # 3. إرسال البيانات (المسودة + السيو + التصنيفات)
        payload = {
            "title": title,
            "content": full_html,
            "featured_media": mid,
            "status": "draft", # تأكيد المسودة
            "categories": [CAT_MAIN, CAT_DRIOUCH],
            "meta": {
                "_yoast_wpseo_focuskw": "الدريوش",
                "rank_math_focus_keyword": "الدريوش",
                "_yoast_wpseo_title": title,
                "_yoast_wpseo_metadesc": lines[0] if lines else title
            }
        }
        
        res_p = requests.post(f"{URL}/posts", auth=(USER, PASS), json=payload)
        return res_p.status_code == 201
    return False

# --- الواجهة ---
st.set_page_config(page_title="محرر الدريوش سيتي الجديد", layout="centered")
st.title("📝 المحرر الاحترافي - الدريوش سيتي")

f = st.file_uploader("ارفع الصورة هنا (سيتم قلبها تلقائياً)", type=["jpg","png","jpeg","webp"])
raw = None
if f: raw = Image.open(f)

if raw:
    # تعديلات اختيارية إضافية
    sat = st.slider("تشبع الألوان", 0.0, 2.0, 1.0)
    bri = st.slider("الإضاءة", 0.0, 2.0, 1.0)
    
    img_ready = ImageEnhance.Color(raw).enhance(sat)
    img_ready = ImageEnhance.Brightness(img_ready).enhance(bri)
    
    st.image(ImageOps.mirror(img_ready), caption="معاينة (مقلوبة تلقائياً)", use_container_width=True)

    st.divider()
    t_in = st.text_input("عنوان المقال (الذي يظهر في الرئيسية)")
    st.warning("⚠️ تنبيه: السطر الأول في المربع أدناه سيصبح 'ترويسة 3' تلقائياً.")
    c_in = st.text_area("نص الخبر (السطر الأول = العنوان الفرعي H3)", height=300)

    if st.button("💾 حفظ في المسودات"):
        if t_in and c_in:
            with st.spinner("جاري الإرسال كمسودة..."):
                if post_to_wp_final(img_ready, t_in, c_in):
                    st.success("✅ نجحت العملية! المقال الآن في 'المسودات' بموقعك.")
                else:
                    st.error("❌ فشل الإرسال - تحقق من كلمة المرور.")
