import streamlit as st
import requests
import base64
import os
import json
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from datetime import datetime
import io
from PIL import Image
import google.generativeai as genai

# ==========================================
# ⚙️ CONFIGURATION (Loaded from Streamlit Secrets)
# ==========================================
# Gemini API Key (Direct from Google AI Studio)
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "YOUR_KEY_HERE")

ADMIN_EMAIL = st.secrets.get("ADMIN_EMAIL", "kampeena@gmail.com")
FIREBASE_WEB_API_KEY = st.secrets.get("FIREBASE_WEB_API_KEY", "YOUR_KEY_HERE")
FIREBASE_PROJECT_ID = st.secrets.get("FIREBASE_PROJECT_ID", "gen-lang-client-0731069779") 
LAW_FOLDER = "law_library"

# Configure Gemini AI
genai.configure(api_key=GEMINI_API_KEY)

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
            st.header("⚙️ ระบบตรวจสอบ AI")
            st.success("✅ Google Gemini 1.5 พร้อมใช้งาน")
            st.caption("Mode: Direct API Key")
            
            st.divider()
            # --- Load Files ---
            all_files = load_law_files()
            
            st.markdown("### 📂 ค้นหากฎหมาย")
            search_query = st.text_input("พิมพ์คำค้นหาชื่อไฟล์ (เช่น health, นม):", key="law_search_box")
            
            if search_query:
                filtered_files = [f for f in all_files if search_query.lower() in f.lower()]
                st.caption(f"🔎 พบ {len(filtered_files)} ไฟล์จากคำค้น")
            else:
                filtered_files = all_files
            
            if 'selected_laws_state' not in st.session_state:
                st.session_state['selected_laws_state'] = []

            if search_query and filtered_files:
                if st.button(f"✅ เลือกทั้งหมดที่เจอ ({len(filtered_files)})"):
                    current_set = set(st.session_state['selected_laws_state'])
                    current_set.update(filtered_files)
                    st.session_state['selected_laws_state'] = list(current_set)
                    st.rerun()

            display_options = list(set(filtered_files + st.session_state['selected_laws_state']))
            display_options.sort()

            sel_files = st.multiselect(
                "รายการกฎหมายที่เลือกใช้:",
                options=display_options,
                key='selected_laws_state'
            )
            
            if sel_files:
                st.success(f"📌 เลือกไว้แล้ว: {len(sel_files)} ฉบับ")

        st.title("📋 รายงานผลการตรวจสอบ (Audit Report)")
        
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.info("1. ข้อมูลสินค้า")
            img_file = st.file_uploader("รูปภาพฉลากสินค้า", type=["jpg","png","jpeg"])
            if img_file: st.image(img_file, caption="ฉลากที่อัปโหลด", use_container_width=True)
            ptype = st.text_input("ประเภทอาหาร (เช่น นม, ขนม)")
            with st.expander("ข้อมูลเพิ่มเติม"):
                url = st.text_input("URL กฎหมายเพิ่มเติม")
                note = st.text_area("หมายเหตุ")
            
            btn = st.button("🚀 เริ่มการตรวจสอบด้วย Gemini AI", type="primary", use_container_width=True)

        with c2:
            st.info("2. ผลการตรวจสอบ")
            if btn:
                if not img_file:
                    st.error("กรุณาอัปโหลดรูปภาพฉลากสินค้า")
                else:
                    with st.spinner("🤖 Gemini AI กำลังอ่านฉลากและวิเคราะห์ตามข้อกฎหมาย..."):
                        try:
                            # 1. Prepare Content
                            law_ctx = ""
                            for f in sel_files: law_ctx += f"\n[ไฟล์: {f}]\n{get_pdf_text(os.path.join(LAW_FOLDER,f))}"
                            if url: law_ctx += f"\n[เว็บ: {url}]\n{get_website_text(url)}"
                            if note: law_ctx += f"\n[หมายเหตุ: {note}]"

                            image_data = img_file.getvalue()
                            
                            prompt = f"""
                            คุณคือ AI ผู้เชี่ยวชาญด้านการตรวจสอบความถูกต้องของฉลากอาหารตามกฎหมายของ อย. (FDA Compliance Expert)
                            งานของคุณคือ "มอง" ไปที่รูปภาพฉลากที่แนบมา และเปรียบเทียบกับ "ข้อมูลกฎหมาย" ที่ให้ไว้

                            สินค้าประเภท: {ptype}
                            ข้อมูลกฎหมายอ้างอิง:
                            {law_ctx[:30000]}

                            คำสั่ง:
                            1. วิเคราะห์ฉลากในรูปภาพอย่างละเอียด (รวมถึงตัวอักษรเล็กๆ, สัญลักษณ์, และตำแหน่งการวาง)
                            2. ตรวจสอบว่ามีข้อมูลครบถ้วนตามกฎหมายที่อ้างอิงหรือไม่ (เช่น ชื่ออาหาร, ส่วนประกอบ, เลขสารบบ, ข้อมูลโภชนาการ, คำเตือน ฯลฯ)
                            3. สรุปผลการตัดสิน (VERDICT) เป็น "ถูกต้อง" หรือ "ไม่ถูกต้อง"
                            4. แสดงรายละเอียดการตรวจสอบในรูปแบบตาราง Markdown โดยมี 5 คอลัมน์คือ:
                               | หัวข้อที่ตรวจสอบ | สิ่งที่พบในฉลาก | กฎหมายที่เกี่ยวข้อง | สถานะ | ข้อสังเกต/คำแนะนำ |
                            
                            กฎเหล็ก:
                            - ห้ามสร้างข้อมูลเท็จ (Hallucination) ให้เขียนเฉพาะสิ่งที่เห็นในรูปจริงเท่านั้น
                            - หากในภาพอ่านไม่ออกหรือไม่ชัดเจน ให้ระบุว่า "ไม่ชัดเจน/รอตรวจสอบ"
                            - ในช่องสถานะ ให้ใช้คำว่า "ผ่าน", "ไม่ผ่าน", หรือ "รอตรวจสอบ" เท่านั้น
                            - ตอบกลับเป็นภาษาไทยที่สุภาพและเป็นทางการ

                            รูปแบบการตอบกลับ:
                            VERDICT: [ถูกต้อง/ไม่ถูกต้อง]
                            [ตาราง Markdown]
                            """

                            model = genai.GenerativeModel("gemini-1.5-flash")
                            
                            # Using the standard SDK format for multimodal input
                            response = model.generate_content(
                                [
                                    {"mime_type": img_file.type, "data": image_data},
                                    prompt
                                ],
                                generation_config={
                                    "max_output_tokens": 8192,
                                    "temperature": 0.1,
                                    "top_p": 0.95,
                                }
                            )
                            
                            res = response.text

                            # --- Display Results ---
                            verdict = None
                            for line in res.split('\n'):
                                if line.strip().upper().startswith('VERDICT:'):
                                    verdict = line.split(':',1)[1].strip()
                                    break

                            if verdict and ('ไม่ถูกต้อง' in verdict or 'FAIL' in verdict.upper()):
                                st.markdown('<div class="verdict-box verdict-fail"><div class="verdict-title">❌ ไม่ถูกต้อง (FAIL)</div>พบจุดที่ไม่เป็นไปตามเกณฑ์กฎหมาย</div>', unsafe_allow_html=True)
                            elif verdict and ('ถูกต้อง' in verdict or 'PASS' in verdict.upper()):
                                st.markdown('<div class="verdict-box verdict-pass"><div class="verdict-title">✅ ถูกต้อง (PASS)</div>ฉลากเป็นไปตามเกณฑ์เบื้องต้น</div>', unsafe_allow_html=True)
                            else:
                                st.info(f"VERDICT: {verdict}")

                            # Display the markdown table
                            if '|' in res:
                                table_part = ""
                                in_table = False
                                for line in res.split('\n'):
                                    if '|' in line:
                                        table_part += line + '\n'
                                        in_table = True
                                    elif in_table:
                                        break
                                
                                table_lines = table_part.strip().split('\n')
                                if len(table_lines) >= 3:
                                    headers = [h.strip() for h in table_lines[0].strip('|').split('|')]
                                    html = '<table class="audit-table"><thead><tr>' + ''.join([f'<th>{h}</th>' for h in headers]) + '</tr></thead><tbody>'
                                    
                                    for line in table_lines[2:]:
                                        cells = [c.strip() for c in line.strip('|').split('|')]
                                        row_html = "<tr>"
                                        for i, cell in enumerate(cells):
                                            if i == 3: # Status column
                                                if 'ไม่ผ่าน' in cell:
                                                    row_html += f'<td><span class="status-fail">{cell}</span></td>'
                                                elif 'ผ่าน' in cell:
                                                    row_html += f'<td><span class="status-pass">{cell}</span></td>'
                                                else:
                                                    row_html += f'<td>{cell}</td>'
                                            else:
                                                row_html += f'<td>{cell}</td>'
                                        row_html += "</tr>"
                                        html += row_html
                                    html += '</tbody></table>'
                                    st.markdown(html, unsafe_allow_html=True)
                                else:
                                    st.markdown(res)
                            else:
                                st.markdown(res)

                            with st.expander("🛠️ Raw AI Output (Debug)"):
                                st.code(res)

                        except Exception as e:
                            st.error(f"เกิดข้อผิดพลาดในการประมวลผล: {e}")
                            st.info("💡 ข้อแนะนำ: ตรวจสอบความถูกต้องของ API Key ในโค้ด")