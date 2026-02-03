import streamlit as st
import requests
import base64
import os
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from openai import OpenAI

# ==========================================
# 🔐 ส่วนที่ 1: ตั้งค่าระบบ Login (Firebase)
# ==========================================

# ⚠️ ใส่ Web API Key จาก Firebase Console ตรงนี้
FIREBASE_WEB_API_KEY = "AIzaSyBhTEKwnX6Q1B7alEYcCjBhsnhh_zLfiI4" 

def login_user(email, password):
    # ยิง Request ไปที่ Firebase เพื่อเช็คระหัสผ่าน
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    res = requests.post(url, json=payload)
    
    if res.status_code == 200:
        return True, res.json()
    else:
        return False, res.json().get('error', {}).get('message', 'Unknown error')

def init_login_page():
    # ถ้ายังไม่ล็อกอิน ให้โชว์หน้า Login
    if 'is_logged_in' not in st.session_state:
        st.session_state['is_logged_in'] = False

    if not st.session_state['is_logged_in']:
        st.markdown("""<h2 style='text-align: center;'>🔐 เข้าสู่ระบบตรวจสอบฉลาก (Factory Audit)</h2>""", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form"):
                email = st.text_input("Email ผู้ใช้งาน")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("เข้าสู่ระบบ")
                
                if submit:
                    success, info = login_user(email, password)
                    if success:
                        st.session_state['is_logged_in'] = True
                        st.session_state['user_email'] = email
                        st.success("ล็อกอินสำเร็จ! กำลังเข้าสู่ระบบ...")
                        st.rerun() # รีเฟรชหน้าเพื่อเข้าสู่แอพหลัก
                    else:
                        st.error(f"ล็อกอินไม่ผ่าน: {info}")
        return False # ยังไม่ผ่าน
    else:
        # ทำปุ่ม Logout ไว้ที่ Sidebar
        with st.sidebar:
            st.write(f"👤 ผู้ใช้: {st.session_state.get('user_email')}")
            if st.button("ออกจากระบบ (Logout)"):
                st.session_state['is_logged_in'] = False
                st.rerun()
        return True # ผ่านแล้ว

# ==========================================
# 🏭 ส่วนที่ 2: แอพตรวจสอบฉลาก (Logic เดิม)
# ==========================================

# ตั้งค่า Path ของโฟลเดอร์เก็บกฎหมาย
LAW_FOLDER = "law_library"

def get_pdf_text(file_path):
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted
    except Exception as e:
        st.error(f"อ่านไฟล์ {file_path} ไม่ได้: {e}")
    return text

def load_law_files():
    if not os.path.exists(LAW_FOLDER):
        os.makedirs(LAW_FOLDER)
        return []
    files = [f for f in os.listdir(LAW_FOLDER) if f.endswith('.pdf')]
    return files

def get_website_text(url):
    text = ""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
    except Exception as e:
        st.warning(f"ดึงเว็บ {url} ไม่ได้: {e}")
    return text

# --- เริ่มต้นโปรแกรม ---
st.set_page_config(page_title="Pro FDA Auditor", layout="wide", page_icon="⚖️")

st.markdown("""
<style>
    .verdict-box {padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;}
    .verdict-pass {background-color: #d4edda; color: #155724; border: 2px solid #c3e6cb;}
    .verdict-fail {background-color: #f8d7da; color: #721c24; border: 2px solid #f5c6cb;}
    .verdict-title {font-size: 24px !important; font-weight: bold; margin-bottom: 5px !important;}

    table {width: 100% !important; border-collapse: collapse;}
    th {background-color: #f2f2f2 !important; color: #333 !important; font-weight: bold !important; font-size: 16px !important; text-align: center !important;}
    td {font-size: 15px !important; vertical-align: top !important; border-bottom: 1px solid #ddd !important;}
</style>
""", unsafe_allow_html=True)

# เช็ค Login ก่อน! ถ้าผ่านถึงจะรันโค้ดข้างล่างนี้
if init_login_page():
    
    st.markdown("""
        <h1 style='text-align: center; color: #2E86C1;'>⚖️ AI Pro FDA Auditor (Online System)</h1>
        <p style='text-align: center;'>ระบบตรวจสอบฉลากอาหารอัจฉริยะ (สำหรับภายในโรงงาน)</p>
        <hr>
    """, unsafe_allow_html=True)

    # Sidebar: ตั้งค่า
    with st.sidebar:
        st.header("🔑 ตั้งค่าระบบ")
        # ให้ User ใส่ API Key เอง หรือคุณจะฝังไว้ใน Code เลยก็ได้ถ้ารวย (ไม่แนะนำ)
        api_key = st.text_input("OpenAI API Key", type="password") 
        
        st.markdown("---")
        st.header("📂 คลังกฎหมาย (Law Library)")
        law_files = load_law_files()
        
        if not law_files:
            st.warning(f"ไม่พบไฟล์ในโฟลเดอร์ {LAW_FOLDER}")
        
        selected_files = st.multiselect(
            "เลือกกฎหมายที่เกี่ยวข้อง:",
            law_files,
            placeholder="เลือกไฟล์ประกาศฯ..."
        )

    if api_key:
        client = OpenAI(api_key=api_key)

        col1, col2 = st.columns([1, 1.2])
        
        with col1:
            st.subheader("1. ข้อมูลสินค้า")
            uploaded_image = st.file_uploader("อัปโหลดรูปฉลาก", type=["jpg", "png", "jpeg"])
            if uploaded_image:
                st.image(uploaded_image, caption="ตัวอย่างฉลาก", use_column_width=True)
            
            product_type = st.text_input("ประเภทอาหาร (เช่น นมพาสเจอร์ไรซ์)", placeholder="ระบุให้ชัดเจน")

        with col2:
            st.subheader("2. บริบทการตรวจสอบ")
            
            st.markdown("### 🚨 โหมดจับผิด")
            audit_mode = st.radio(
                "ระดับความเข้มข้น:",
                ["ตรวจสอบทั่วไป", "ตรวจสอบเข้มข้น / จำลองเรื่องร้องเรียน"]
            )
            
            complaint_details = ""
            if "เข้มข้น" in audit_mode:
                st.warning("⚠️ AI จะเพ่งเล็งจุดเล็กๆ น้อยๆ เป็นพิเศษ")
                complaint_details = st.text_area("ระบุประเด็นที่กังวล (ถ้ามี):", height=100)

            st.markdown("---")
            extra_url = st.text_input("ลิงก์กฎหมายเพิ่มเติม (URL)")
            extra_text = st.text_area("ข้อความกฎหมายเพิ่มเติม", height=100)

        # ปุ่มตรวจสอบ
        if st.button("เริ่มการตรวจสอบ (Audit Now) ⚡", type="primary"):
            if not uploaded_image or not product_type:
                st.error("กรุณาอัปโหลดรูปและระบุประเภทอาหาร")
            elif not selected_files and not extra_text and not extra_url:
                st.warning("⚠️ กรุณาเลือกกฎหมายอ้างอิงอย่างน้อย 1 อย่าง")
            else:
                with st.spinner("🤖 AI กำลังสวมบทบาทเจ้าหน้าที่ ตรวจสอบข้อมูล..."):
                    try:
                        # 1. รวบรวมกฎหมาย
                        law_context = ""
                        for file_name in selected_files:
                            file_path = os.path.join(LAW_FOLDER, file_name)
                            law_context += f"\n\n--- กฎหมาย: {file_name} ---\n{get_pdf_text(file_path)}"
                        
                        if extra_url: law_context += f"\n\n--- เว็บ: {extra_url} ---\n{get_website_text(extra_url)}"
                        if extra_text: law_context += f"\n\n--- เพิ่มเติม ---\n{extra_text}"
                            
                        law_context = law_context[:60000]

                        # 2. เตรียมรูป
                        base64_image = base64.b64encode(uploaded_image.getvalue()).decode('utf-8')

                        # 3. Prompt
                        if "เข้มข้น" in audit_mode:
                            system_role = "คุณคือผู้ตรวจสอบฉลากอาหารอาวุโส ที่มีความเข้มงวดสูงสุด เน้นจับผิด"
                            specific_focus = f"ตรวจสอบประเด็นร้องเรียนเรื่อง: '{complaint_details}' อย่างละเอียด"
                        else:
                            system_role = "คุณคือผู้เชี่ยวชาญด้านกฎหมายอาหาร ให้คำแนะนำเชิงสร้างสรรค์"
                            specific_focus = "ตรวจสอบความถูกต้องทั่วไปตามมาตรฐาน"

                        table_header = "| ตำแหน่งบนภาพ | ข้อความที่พบ | กฎหมายที่เกี่ยวข้อง | สถานะ | คำแนะนำ |"
                        table_divider = "|---|---|---|---|---|"

                        system_prompt = f"""
                        คุณคือผู้ตรวจสอบฉลากอาหาร อย. (FDA Auditor)
                        หน้าที่: ตรวจสอบฉลากเทียบกับกฎหมายอย่างละเอียด

                        คำสั่งสำคัญ (STRICT RULES):
                        1. ถ้าพบความผิดปกติ หรือความเสี่ยงแม้แต่นิดเดียว ให้สรุปว่า "INCORRECT"
                        2. ห้ามเขียนข้อความเกริ่นนำ หรือสรุปความใดๆ นอกเหนือจากรูปแบบที่กำหนด
                        3. ให้แสดงผลลัพธ์เป็น 2 ส่วนเท่านั้น:
                           ส่วนที่ 1: บรรทัดแรกเขียนว่า "VERDICT: [CORRECT]" หรือ "VERDICT: [INCORRECT]"
                           ส่วนที่ 2: ตาราง Markdown ตามหัวข้อที่กำหนดให้เท่านั้น

                        การกรอกข้อมูลในตาราง:
                        - ช่อง "สถานะ": ต้องใช้คำว่า "ผ่าน" หรือ "ไม่ผ่าน" เท่านั้น
                        - ช่อง "กฎหมายที่เกี่ยวข้อง": ระบุชื่อประกาศและข้อให้ชัดเจน
                        - ช่อง "คำแนะนำ": ถ้าไม่ผ่าน ต้องบอกวิธีแก้ให้ชัดเจน
                        """

                        user_prompt = f"""
                        สินค้า: {product_type}
                        โหมดตรวจสอบ: {specific_focus}
                        ข้อมูลกฎหมาย: {law_context}

                        จงเติมข้อมูลลงในตารางนี้ให้สมบูรณ์ (ห้ามเปลี่ยนหัวตาราง):

                        VERDICT: [ผลการตัดสิน]

                        {table_header}
                        {table_divider}
                        (ให้ AI เขียนแถวข้อมูลต่อจากตรงนี้...)
                        """

                        response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": [
                                    {"type": "text", "text": user_prompt},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                                ]}
                            ],
                            max_tokens=3000,
                        )

                        st.success("เสร็จสิ้น!")
                        result_text = response.choices[0].message.content

                        if "VERDICT: [INCORRECT]" in result_text or "VERDICT: INCORRECT" in result_text:
                            st.markdown(
                                '<div class="verdict-box verdict-fail"><div class="verdict-title">❌ ไม่ผ่าน (FAIL)</div>พบจุดที่ต้องแก้ไขตามกฎหมาย</div>',
                                unsafe_allow_html=True,
                            )
                        elif "VERDICT: [CORRECT]" in result_text or "VERDICT: CORRECT" in result_text:
                            st.markdown(
                                '<div class="verdict-box verdict-pass"><div class="verdict-title">✅ ผ่าน (PASS)</div>ฉลากเป็นไปตามเกณฑ์</div>',
                                unsafe_allow_html=True,
                            )

                        lines = result_text.splitlines()
                        table_rows = [
                            line for line in lines
                            if "|" in line and "ตำแหน่งบนภาพ" not in line and "---" not in line
                        ]

                        st.markdown("### 📋 รายละเอียดการตรวจสอบ")
                        if table_rows:
                            full_table = f"{table_header}\n{table_divider}\n" + "\n".join(table_rows)
                            st.markdown(full_table)
                        else:
                            clean_result = (
                                result_text
                                .replace("VERDICT: [CORRECT]", "")
                                .replace("VERDICT: [INCORRECT]", "")
                                .replace("VERDICT: CORRECT", "")
                                .replace("VERDICT: INCORRECT", "")
                                .strip()
                            )
                            st.markdown(clean_result)

                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")
