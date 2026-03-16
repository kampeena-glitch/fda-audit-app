import streamlit as st
import requests
import base64
import os
import json
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from openai import OpenAI
from datetime import datetime
import io
from PIL import Image
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except Exception:
    TESSERACT_AVAILABLE = False

# Default Tesseract paths for Windows
DEFAULT_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
FIREBASE_WEB_API_KEY = "AIzaSyBhTEKwnX6Q1B7alEYcCjBhsnhh_zLfiI4"
FIREBASE_PROJECT_ID = "food-label-verification-system" 
ADMIN_EMAIL = "kampeena@gmail.com"

LAW_FOLDER = "law_library"

st.set_page_config(page_title="AI FDA Audit Pro", layout="wide", page_icon="⚖️")

# --- CSS: ปรับแต่งตารางให้สวยงาม ---
st.markdown("""
<style>
    .verdict-box {padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; font-family: 'Sarabun', sans-serif;}
    .verdict-pass {background-color: #e6fffa; color: #047857; border: 2px solid #34d399;}
    .verdict-fail {background-color: #fff5f5; color: #c53030; border: 2px solid #fc8181;}
    .verdict-title {font-size: 28px !important; font-weight: bold; margin-bottom: 5px !important;}
    
    /* สไตล์ตาราง Audit */
    .audit-table {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
        font-size: 16px;
        font-family: sans-serif;
        box-shadow: 0 0 20px rgba(0, 0, 0, 0.05);
        border-radius: 8px; 
        overflow: hidden;
    }
    .audit-table thead tr {
        background-color: #009879;
        color: #ffffff;
        text-align: left;
    }
    .audit-table th, .audit-table td {
        padding: 12px 15px;
        border-bottom: 1px solid #dddddd;
        vertical-align: top;
        min-width: 120px; /* Prevent too narrow columns */
    }
    .audit-table td:nth-child(2) {
        min-width: 250px; /* Make 'Found Text' column wider */
        word-break: break-word;
    }
    .audit-table tbody tr:nth-of-type(even) {
        background-color: #f3f3f3;
    }
    .audit-table tbody tr:last-of-type {
        border-bottom: 2px solid #009879;
    }
    .status-pass {
        color: #009879;
        font-weight: bold;
        background-color: #e6fffa;
        padding: 4px 8px;
        border-radius: 4px;
        display: inline-block;
    }
    .status-fail {
        color: #dc3545;
        font-weight: bold;
        background-color: #fff5f5;
        padding: 4px 8px;
        border-radius: 4px;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================
def update_user_status(id_token, user_id, email, approved=False):
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{user_id}?updateMask.fieldPaths=email&updateMask.fieldPaths=approved"
    is_admin = (email.strip() == ADMIN_EMAIL.strip())
    final_approve = True if is_admin else approved
    payload = {
        "fields": {
            "email": {"stringValue": email},
            "approved": {"booleanValue": final_approve},
            "created_at": {"stringValue": str(datetime.now())}
        }
    }
    requests.patch(url, json=payload, headers={"Authorization": f"Bearer {id_token}"})

def check_user_approval(id_token, user_id):
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{user_id}"
    res = requests.get(url, headers={"Authorization": f"Bearer {id_token}"})
    if res.status_code == 200:
        try: return res.json()["fields"]["approved"]["booleanValue"]
        except: return False
    return False

def get_all_users(id_token):
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users"
    res = requests.get(url, headers={"Authorization": f"Bearer {id_token}"})
    users_list = []
    if res.status_code == 200:
        docs = res.json().get('documents', [])
        for doc in docs:
            try:
                users_list.append({
                    "id": doc['name'].split('/')[-1],
                    "email": doc['fields']['email']['stringValue'],
                    "approved": doc['fields']['approved']['booleanValue']
                })
            except: pass
    return users_list

def login_user(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    res = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True})
    if res.status_code == 200:
        data = res.json()
        is_approved = True if email.strip() == ADMIN_EMAIL.strip() else check_user_approval(data['idToken'], data['localId'])
        return True, data, is_approved
    return False, res.json().get('error', {}).get('message', 'Unknown'), False

def register_user(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_WEB_API_KEY}"
    res = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True})
    if res.status_code == 200:
        data = res.json()
        update_user_status(data['idToken'], data['localId'], email, approved=False)
        return True, data
    return False, res.json().get('error', {}).get('message', 'Unknown')

def get_pdf_text(file_path):
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            t = page.extract_text()
            if t: text += t
    except: pass
    return text

def load_law_files():
    if not os.path.exists(LAW_FOLDER): os.makedirs(LAW_FOLDER); return []
    return [f for f in os.listdir(LAW_FOLDER) if f.endswith('.pdf')]

def get_website_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, 'html.parser')
            return soup.get_text(separator=' ', strip=True)
    except: pass
    return ""

# === OCR HELPERS ===
def setup_tesseract(tesseract_path=None):
    """Configure pytesseract path. Auto-detect if not provided. Returns True if successful."""
    global TESSERACT_AVAILABLE
    try:
        # If path provided, use it
        if tesseract_path and os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            TESSERACT_AVAILABLE = True
            return True
        # Otherwise try defaults
        for default_path in DEFAULT_TESSERACT_PATHS:
            if os.path.exists(default_path):
                pytesseract.pytesseract.tesseract_cmd = default_path
                TESSERACT_AVAILABLE = True
                return True
        return False
    except Exception as e:
        st.warning(f"⚠️ Tesseract path config failed: {e}")
        return False

def ocr_image(uploaded_file):
    """Run OCR on an uploaded image file and return structured data and full text.
    Requires Tesseract binary available on the system for pytesseract to work.
    """
    try:
        img = Image.open(io.BytesIO(uploaded_file.getvalue())).convert('RGB')
        
        # Helper to run OCR with fallback
        def run_ocr(lang):
            full_text = pytesseract.image_to_string(img, lang=lang)
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang=lang)
            return full_text, data

        # Try 'eng+tha' first, then fallback to 'eng'
        try:
            full_text, raw = run_ocr('eng+tha')
        except Exception as e:
            # If 'eng+tha' fails (likely missing Thai data), try just 'eng'
            print(f"OCR 'eng+tha' failed: {e}, trying 'eng'...")
            full_text, raw = run_ocr('eng')

        # Process structured data
        data = []
        n = len(raw['text'])
        for i in range(n):
            txt = raw['text'][i].strip()
            if txt:
                # Robustly handle confidence score which might be int or str
                raw_conf = raw['conf'][i]
                try:
                    conf = int(raw_conf)
                except (ValueError, TypeError):
                    conf = -1

                data.append({
                    'text': txt,
                    'conf': conf,
                    'left': raw['left'][i],
                    'top': raw['top'][i],
                    'width': raw['width'][i],
                    'height': raw['height'][i]
                })
        return {'text': full_text, 'data': data, 'error': None}
    except Exception as e:
        return {'text': '', 'data': [], 'error': str(e)}

# ==========================================
# 🖥️ MAIN APP LOGIC
# ==========================================

if 'is_logged_in' not in st.session_state: st.session_state['is_logged_in'] = False
if 'is_admin' not in st.session_state: st.session_state['is_admin'] = False

if not st.session_state['is_logged_in']:
    st.markdown("<h2 style='text-align: center;'>🔐 ระบบตรวจสอบฉลากอาหาร (AI Audit)</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        t1, t2 = st.tabs(["เข้าสู่ระบบ", "สมัครสมาชิก"])
        with t1:
            with st.form("login"):
                email = st.text_input("อีเมล")
                password = st.text_input("รหัสผ่าน", type="password")
                if st.form_submit_button("เข้าสู่ระบบ", use_container_width=True):
                    success, info, approved = login_user(email, password)
                    if success:
                        if approved:
                            st.session_state['is_logged_in'] = True
                            st.session_state['user_email'] = email
                            st.session_state['id_token'] = info['idToken']
                            if email.strip() == ADMIN_EMAIL.strip(): st.session_state['is_admin'] = True
                            st.rerun()
                        else: st.warning("⏳ รอการอนุมัติจาก Admin")
                    else: st.error(f"Error: {info}")
        with t2:
            with st.form("reg"):
                re = st.text_input("อีเมล")
                rp = st.text_input("รหัสผ่าน (6+ ตัวอักษร)", type="password")
                if st.form_submit_button("สมัครสมาชิก", use_container_width=True):
                    if len(rp)<6: st.error("รหัสสั้นไป")
                    else:
                        s, i = register_user(re, rp)
                        if s: st.success("✅ สมัครสำเร็จ! รออนุมัติ")
                        else: st.error(f"Error: {i}")

else:
    with st.sidebar:
        st.write(f"👤 {st.session_state.get('user_email')}")
        if st.session_state['is_admin']: st.markdown("🔴 **ADMIN**")
        if st.button("ออกจากระบบ"):
            st.session_state['is_logged_in'] = False
            st.session_state['is_admin'] = False
            st.rerun()
        st.divider()
        app_mode = "Audit"
        if st.session_state['is_admin']:
            app_mode = st.radio("เลือกเมนู:", ["ตรวจสอบฉลาก (Audit)", "จัดการผู้ใช้ (Admin)"])

    if st.session_state['is_admin'] and app_mode == "จัดการผู้ใช้ (Admin)":
        st.header("👥 จัดการผู้ใช้งาน")
        users = get_all_users(st.session_state['id_token'])
        pending = [u for u in users if not u['approved']]
        st.subheader(f"⏳ รออนุมัติ ({len(pending)})")
        if not pending: st.info("ไม่มีรายการรออนุมัติ")
        for u in pending:
            c1, c2 = st.columns([3,1])
            c1.write(f"📧 {u['email']}")
            if c2.button("อนุมัติ", key=u['id']):
                update_user_status(st.session_state['id_token'], u['id'], u['email'], True)
                st.success("อนุมัติแล้ว")
                st.rerun()
    else:
        # --- AUDIT PAGE ---
        with st.sidebar:
            st.header("⚙️ ตั้งค่าการตรวจสอบ")
            api_key = st.text_input("OpenAI API Key", type="password")
            
            # --- Tesseract Configuration ---
            if not TESSERACT_AVAILABLE:
                st.warning("⚠️ Tesseract OCR ยังไม่พร้อมใช้งาน")
                st.caption("📍 ติดตั้ง Tesseract OCR: https://github.com/UB-Mannheim/tesseract/releases")
                tesseract_path = st.text_input("🔧 กำหนด Tesseract path (ถ้าติดตั้งแล้ว):", 
                                               placeholder=r"C:\Program Files\Tesseract-OCR\tesseract.exe")
                if tesseract_path:
                    setup_tesseract(tesseract_path)
                    if os.path.exists(tesseract_path):
                        st.success("✅ Tesseract path ถูกต้อง")
                    else:
                        st.error("❌ ไม่พบไฟล์ Tesseract ที่ path นี้")
            else:
                st.success("✅ Tesseract OCR พร้อมใช้งาน")
                setup_tesseract()  # Auto-setup with defaults
            
            # Fallback: ให้ user ใส่ OCR text ด้วยตัวเอง (เสมอ ไม่ว่า Tesseract จะพร้อมหรือไม่)
            st.caption("📝 ใส่ข้อความจากฉลากด้วยตัวเอง (ถ้า Tesseract ไม่ทำงาน):")
            manual_ocr_text = st.text_area("ข้อความบนฉลาก (OCR Manual Input):", height=100, 
                                            placeholder="วาง OCR text ที่ผ่านมาจากวิธีอื่นหรือพิมพ์เอง...")

            double_check = st.checkbox('🔁 เปิดการตรวจสอบซ้ำ (Double-check) (แนะนำ)', value=True)
            
            # --- Load Files ---
            all_files = load_law_files()
            
            # --- 🔍 ระบบค้นหากฎหมาย (Smart Search) ---
            st.markdown("### 📂 ค้นหากฎหมาย")
            search_query = st.text_input("พิมพ์คำค้นหาชื่อไฟล์ (เช่น health, นม):", key="law_search_box")
            
            # กรองไฟล์ตามคำค้น (จากชื่อไฟล์)
            if search_query:
                filtered_files = [f for f in all_files if search_query.lower() in f.lower()]
                st.caption(f"🔎 พบ {len(filtered_files)} ไฟล์จากคำค้น")
            else:
                filtered_files = all_files
            
            # เตรียม State สำหรับเก็บค่าที่เลือก (ป้องกันค่าหายเมื่อค้นหาใหม่)
            if 'selected_laws_state' not in st.session_state:
                st.session_state['selected_laws_state'] = []

            # ปุ่มเลือกทั้งหมด (แสดงเฉพาะเมื่อมีการค้นหาและเจอผลลัพธ์)
            if search_query and filtered_files:
                if st.button(f"✅ เลือกทั้งหมดที่เจอ ({len(filtered_files)})"):
                    # รวมของใหม่เข้ากับของเดิม (ไม่เอาตัวซ้ำ)
                    current_set = set(st.session_state['selected_laws_state'])
                    current_set.update(filtered_files)
                    st.session_state['selected_laws_state'] = list(current_set)
                    st.rerun()

            # --- Logic สำคัญ: รวมไฟล์ที่ค้นเจอเข้ากับไฟล์ที่เลือกไว้แล้ว เพื่อไม่ให้ของเก่าหาย ---
            # Options = (ไฟล์ที่ค้นเจอ) UNION (ไฟล์ที่เคยเลือกไปแล้ว)
            display_options = list(set(filtered_files + st.session_state['selected_laws_state']))
            display_options.sort() # เรียงตามตัวอักษร

            sel_files = st.multiselect(
                "รายการกฎหมายที่เลือกใช้:",
                options=display_options,
                key='selected_laws_state' # ผูกกับ Session State โดยตรง
            )
            
            if sel_files:
                st.success(f"📌 เลือกไว้แล้ว: {len(sel_files)} ฉบับ")

        st.title("📋 รายงานผลการตรวจสอบ (Audit Report)")
        
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.info("1. ข้อมูลสินค้า")
            img = st.file_uploader("รูปภาพฉลากสินค้า", type=["jpg","png","jpeg"])
            if img: st.image(img, caption="ฉลากที่อัปโหลด", use_container_width=True)
            ptype = st.text_input("ประเภทอาหาร (เช่น นม, ขนม)")
            with st.expander("ข้อมูลเพิ่มเติม"):
                url = st.text_input("URL กฎหมาย")
                note = st.text_area("หมายเหตุ")
            
            btn = st.button("🚀 เริ่มการตรวจสอบ", type="primary", use_container_width=True)

        with c2:
            st.info("2. ผลการตรวจสอบ")
            if btn:
                if not api_key or not img:
                    st.error("กรุณาใส่ API Key และอัปโหลดรูปภาพ")
                else:
                    # 1. OCR / Text Extraction
                    ocr_text = ""
                    ocr_result = None
                    with st.spinner("🔍 กำลังดึงข้อความ (OCR)..."):
                        if TESSERACT_AVAILABLE:
                            ocr_result = ocr_image(img)
                            if ocr_result.get('error'):
                                st.error(f"OCR Error details: {ocr_result['error']}")
                            ocr_text = ocr_result.get('text','').strip()
                        elif manual_ocr_text:
                            ocr_text = manual_ocr_text.strip()
                    
                    # Check text BEFORE AI spinner (Fixes infinite spinner on st.stop)
                    if not ocr_text:
                        st.warning("⚠️ ไม่มี OCR text — กรุณาตรวจสอบว่าติดตั้ง Tesseract ถูกต้อง หรือพิมพ์ข้อความด้วยตัวเอง")
                        if ocr_result and ocr_result.get('error'):
                            st.caption(f"Technical Error: {ocr_result['error']}")
                        st.stop()

                    # 2. AI Processing
                    with st.spinner("🤖 AI กำลังตรวจสอบอย่างละเอียด (รวมถึงจุดเสี่ยงเล็กๆ น้อยๆ)..."):
                        try:
                            client = OpenAI(api_key=api_key)
                            
                            law_ctx = ""
                            for f in sel_files: law_ctx += f"\n[ไฟล์: {f}]\n{get_pdf_text(os.path.join(LAW_FOLDER,f))}"
                            if url: law_ctx += f"\n[เว็บ: {url}]\n{get_website_text(url)}"
                            if note: law_ctx += f"\n[หมายเหตุ: {note}]"

                            # --- PROMPT: บังคับตาราง + ห้ามสร้าง hallucination + คะแนนความมั่นใจ ---
                            sys_prompt = """
                            คุณคือ AI ผู้ช่วยตรวจสอบความถูกต้องของฉลากสินค้า (Compliance Assistant) ที่ทำหน้าที่ช่วยสกรีนเบื้องต้นเท่านั้น (ไม่ใช่เจ้าหน้าที่ อย. และไม่ใช่คำตัดสินทางกฎหมาย)
                            หน้าที่ของคุณคือช่วยเปรียบเทียบข้อความบนฉลากกับกฎหมายที่ให้มา เพื่อหา 'จุดเสี่ยง' หรือ 'ข้อสังเกต' เท่านั้น

                            กฎสำคัญ (MUST):
                            1) ห้ามสร้าง hallucination: เขียนเฉพาะข้อความที่ **พบจริง** จาก OCR_TEXT หรือบนภาพเท่านั้น ห้ามประดิษฐ์คำใหม่
                            1.1) **การจัดรูปแบบข้อความ**: ถ้าข้อความภาษาไทยมีการเว้นวรรคระหว่างตัวอักษรผิดปกติ (เช่น "ไ ม ่ มี") ให้แก้ไขให้ติดกันให้อ่านรู้เรื่อง (เช่น "ไม่มี") แต่ห้ามแก้ตัวสะกด
                            2) ห้ามเขียนข้อความนอกเหนือจาก 1) บรรทัด VERDICT และ 2) ตาราง Markdown ที่มี 6 คอลัมน์ตามนี้:
                               | ตำแหน่งบนภาพ | ข้อความที่พบ | OCR Confidence | กฎหมายที่เกี่ยวข้อง | สถานะ | ข้อสังเกต/คำแนะนำ |
                            3) ช่อง "สถานะ" ต้องเป็นคำว่า "ผ่าน" หรือ "ไม่ผ่าน" หรือ "รอตรวจสอบ" เท่านั้น
                            4) ช่อง "OCR Confidence" ให้ระบุ confidence score 0-100 จาก OCR (หากมี) หรือประมาณการความมั่นใจว่าข้อความนั้นมีจริง (0=ไม่แน่ใจเลย, 100=แน่นอน)
                            5) **ห้ามเขียนแถวถ้า confidence < 60** — ถ้าไม่แน่ใจว่าข้อความมีจริงบนภาพ ห้ามเขียนแถวนั้น
                            6) ในกรณี "ไม่ผ่าน" ให้ระบุหลักฐานจากฉลาก (quote จาก OCR หรือคำที่พบบนภาพ) และอ้างอิงกฎหมายพร้อมข้อ/มาตรา (ถ้าทำได้)
                            7) ห้ามเพิ่มคอลัมน์หรือข้อความนอกตาราง
                            8) หากไม่แน่ใจให้ระบุว่า "รอตรวจสอบโดยมนุษย์" หรือ "ไม่แน่ใจ"

                            ตัวอย่างแถว (ภาษาไทย):
                            | ด้านบนขวา | "12 เดือนขึ้นไป" | 92 | ประกาศกระทรวงสาธารณสุข (ข้อ 2) | ไม่ผ่าน | หลักฐาน: '12 เดือนขึ้นไป'; ข้อสังเกต: ควรเพิ่มคำเตือนตามกฎหมาย |
                            """

                            user_prompt = f"""
                            สินค้า: {ptype}
                            ข้อมูลกฎหมาย: {law_ctx[:50000]}
                            OCR_TEXT (ตัด): {ocr_text[:20000]}

                            คำสั่ง: จงเติมข้อมูลลงในตารางนี้ให้สมบูรณ์ (ห้ามเปลี่ยนหัวตาราง)
                            **ขอให้เขียนเฉพาะข้อความที่มีจริงบนรูปเท่านั้น ห้ามประดิษฐ์**

                            VERDICT: [ผลการตัดสิน]

                            | ตำแหน่งบนภาพ | ข้อความที่พบ | OCR Confidence | กฎหมายที่เกี่ยวข้อง | สถานะ | คำแนะนำ |
                            |---|---|---|---|---|---|

                            (ให้ AI เขียนแถวข้อมูลต่อจากตรงนี้...)
                            """

                            # Note: some OpenAI chat endpoints/models don't accept complex message content
                            # with embedded image objects. We pass only text (including OCR text) so
                            # the model receives the label text and context reliably.
                            resp = client.chat.completions.create(
                                model="gpt-4o",
                                messages=[
                                    {"role": "system", "content": sys_prompt},
                                    {"role": "user", "content": user_prompt}
                                ],
                                max_tokens=3000
                            )
                            res = resp.choices[0].message.content

                            # --- แยกผลลัพธ์เพื่อแสดงผล ---
                            # 1. VERDICT
                            verdict = None
                            for line in res.split('\n'):
                                if line.strip().upper().startswith('VERDICT:'):
                                    verdict = line.split(':',1)[1].strip()
                                    break

                            if verdict and ('INCORRECT' in verdict or 'ไม่ถูกต้อง' in verdict):
                                st.markdown('<div class="verdict-box verdict-fail"><div class="verdict-title">❌ ไม่ถูกต้อง (FAIL)</div>พบจุดที่ต้องแก้ไข (รวมถึงรายละเอียดทางเทคนิค)</div>', unsafe_allow_html=True)
                            elif verdict and ('CORRECT' in verdict or 'ถูกต้อง' in verdict):
                                st.markdown('<div class="verdict-box verdict-pass"><div class="verdict-title">✅ ถูกต้อง (PASS)</div>ฉลากเป็นไปตามเกณฑ์</div>', unsafe_allow_html=True)
                            else:
                                st.warning('ไม่สามารถระบุ VERDICT ได้อย่างชัดเจน')

                            # 2. Parse table rows robustly and enforce 6 columns (including confidence)
                            lines = res.split('\n')
                            table_rows = []
                            for line in lines:
                                if '|' in line and 'ตำแหน่งบนภาพ' not in line and '---' not in line:
                                    raw_cells = [c.strip() for c in line.strip().strip('|').split('|')]
                                    # Normalize to exactly 6 columns
                                    if len(raw_cells) > 6:
                                        raw_cells = raw_cells[:5] + [' | '.join(raw_cells[5:])]
                                    elif len(raw_cells) < 6:
                                        raw_cells += [''] * (6 - len(raw_cells))

                                    # Extract confidence score (column 3)
                                    conf_str = raw_cells[2].strip()
                                    try:
                                        conf_score = int(conf_str)
                                    except:
                                        conf_score = 0  # Default to 0 if can't parse

                                    # Skip rows with low confidence (<60)
                                    if conf_score < 60:
                                        continue

                                    # Normalize status (column 4)
                                    status = raw_cells[4]
                                    if status not in ['ผ่าน','ไม่ผ่าน']:
                                        s_low = status.lower()
                                        if 'pass' in s_low or 'correct' in s_low or 'ผ่าน' in status:
                                            status = 'ผ่าน'
                                        elif 'fail' in s_low or 'incorrect' in s_low or 'ไม่ผ่าน' in status:
                                            status = 'ไม่ผ่าน'
                                        else:
                                            status = status
                                    raw_cells[4] = status
                                    table_rows.append(raw_cells)

                            # 3. Double-check process (Moved execution BEFORE rendering table)
                            review_results = {}
                            if double_check and table_rows:
                                try:
                                    verification_lines = []
                                    for i, r in enumerate(table_rows, start=1):
                                        verification_lines.append(f"ROW {i}: |{r[0]}|{r[1]}|{r[2]}|{r[3]}|{r[4]}|")
                                    verify_prompt = "Please verify each ROW strictly. For each ROW, return a single line in this exact format:\nROW <n>: CONFIRM: YES or NO; NOTE: <short reason>; CITATION: <law reference if any>\nDo not output anything else."
                                    verify_user = f"OCR_TEXT:\n{ocr_text[:20000]}\n\nLAWS:\n{law_ctx[:50000]}\n\nTABLE_1:\n" + "\n".join(verification_lines)
                                    vresp = client.chat.completions.create(
                                        model='gpt-4o',
                                        messages=[
                                            {'role':'system', 'content': 'You are a strict verifier. Only answer in the required single-line form for each row.'},
                                            {'role':'user', 'content': verify_prompt + "\n\n" + verify_user}
                                        ],
                                        max_tokens=1200
                                    )
                                    vtext = vresp.choices[0].message.content
                                    
                                    # parse verifier output
                                    for line in vtext.split('\n'):
                                        if line.strip().startswith('ROW'):
                                            parts = line.split(':',1)
                                            if len(parts) == 2:
                                                key = parts[0].strip() # ROW n
                                                review_results[key] = parts[1].strip()
                                except Exception as e:
                                    st.caption(f"Double-check failed: {e}")

                            # 4. Integrate Double-check results and Render Table
                            if table_rows:
                                html = '<table class="audit-table"><thead><tr>' + ''.join([f'<th>{h}</th>' for h in ['ตำแหน่งบนภาพ','ข้อความที่พบ','OCR Conf','กฎหมายที่เกี่ยวข้อง','สถานะ','ข้อสังเกต/คำแนะนำ']]) + '</tr></thead><tbody>'
                                for i, row in enumerate(table_rows, start=1):
                                    # Override status if double-check says NO
                                    key = f'ROW {i}'
                                    double_check_info = review_results.get(key, '')
                                    
                                    if 'CONFIRM: NO' in double_check_info.upper():
                                        row[4] = 'ไม่ผ่าน' # Force fail
                                        # Extract note/citation to add to recommendation
                                        note_part = double_check_info
                                        if 'NOTE:' in double_check_info:
                                            note_part = double_check_info.split('NOTE:',1)[1].strip()
                                        
                                        row[5] += f" <br><b>[Double-Check]:</b> {note_part}"

                                    status_html = row[4]
                                    if 'ไม่ผ่าน' in row[4]:
                                        status_html = f'<span class="status-fail">{row[4]}</span>'
                                    elif 'ผ่าน' in row[4]:
                                        status_html = f'<span class="status-pass">{row[4]}</span>'
                                    elif 'รอตรวจสอบ' in row[4]:
                                        status_html = f'<span style="color:#d69e2e;font-weight:bold;">{row[4]}</span>'
                                        
                                    html += f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td><td style='text-align:center;'>{status_html}</td><td>{row[5]}</td></tr>"
                                html += '</tbody></table>'
                                st.markdown(html, unsafe_allow_html=True)

                                # Show OCR snippets
                                if TESSERACT_AVAILABLE and ocr_result:
                                    with st.expander('🔎 OCR: ข้อความที่ดึงจากภาพ (ตัด):'):
                                        st.text_area('OCR Extract (ตัวอย่าง):', ocr_text[:3000], height=180)
                                        lows = [d for d in ocr_result.get('data',[]) if d.get('conf',-1) < 60]
                                        if lows:
                                            st.write('⚠️ พบคำที่มีความมั่นใจต่ำ (conf<60):')
                                            for t in lows[:20]:
                                                st.write(f"- '{t['text']}' (conf: {t['conf']}, pos: {t['left']},{t['top']})")

                            else:
                                clean_res = res.replace('VERDICT: [CORRECT]','').replace('VERDICT: [INCORRECT]','').strip()
                                st.warning('แสดงผลรูปแบบข้อความ (ไม่สามารถสร้างตารางได้)')
                                st.markdown(clean_res)

                            # Debug: raw AI output (for auditing and troubleshooting)
                            st.markdown('### 🛠️ Debug: Raw AI Output')
                            st.code(res)


                        except Exception as e:
                            st.error(f"เกิดข้อผิดพลาด: {e}")