import os
import json
import ssl
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import requests
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Configuration
FDA_URL = 'https://food.fda.moph.go.th/food-law/category/fda-announcement'
BASE_URL = 'https://food.fda.moph.go.th/'
DOWNLOAD_DIR = r'D:\app-fda-audit\law_library'
HISTORY_FILE = r'D:\app-fda-audit\scraped_history.json'
GDRIVE_FOLDER_ID = '1yiqyq5R66eXbl4g1s0uEYT7pxTRSxImt'
SERVICE_ACCOUNT_FILE = r'D:\app-fda-audit\credentials.json'
SCOPES = ['https://www.googleapis.com/auth/drive']
# The user provided token (Note: test token, might need to change to standard Notify token if this fails)
LINE_TOKEN = "f5TsMgr7pvKU3PEuU0lCOGieO9mASGEKS/EuPqVdT3RXIR36JrCg/fi5dAQg4yCe3Ah+/sLL90H9LCbgvNkg7xxXrWZ2iEMkuiKxiACrzQ1/vrqj6EFCTx+OX2W9s2F3djgsJ5oNZEzFtdpMg4wCjAdB04t89/1O/w1cDnyilFU="

def send_line_message(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "to": "C2ef95828c48e59643efe8c128e92e79b",
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to send Line Message: {e}")
        return False

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def upload_to_gdrive(file_path, filename):
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {
            'name': filename,
            'parents': [GDRIVE_FOLDER_ID]
        }
        media = MediaFileUpload(file_path, mimetype='application/pdf')
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return file.get('id')
    except Exception as e:
        print(f"Error uploading to Google Drive: {e}")
        return None

def fetch_fda_page():
    print(f"[{datetime.datetime.now()}] Fetching FDA website...")
    req = urllib.request.Request(FDA_URL, headers={'User-Agent': 'Mozilla/5.0'})
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching FDA website: {e}")
        return None

def main():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
        
    html_content = fetch_fda_page()
    if not html_content:
        return

    soup = BeautifulSoup(html_content, 'html.parser')
    history = load_history()
    new_downloads = 0

    # Find all links
    links = soup.find_all('a')
    for a in links:
        href = a.get('href')
        text = a.text.strip()
        
        # Check if it's a media download link and has text
        if href and 'media.php' in href and text:
            # Parse URL to get ID
            parsed_url = urllib.parse.urlparse(href)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            doc_id = query_params.get('id', [None])[0]
            if doc_id and doc_id not in history:
                # Ensure it's a full URL
                download_url = href if href.startswith('http') else urllib.parse.urljoin(BASE_URL, href)
                
                # Get the filename from url or use ID
                file_name = query_params.get('name', [f"document_{doc_id}.pdf"])[0]
                # Clean filename
                file_name = "".join(c for c in file_name if c.isalnum() or c in " ._-")
                file_path = os.path.join(DOWNLOAD_DIR, file_name)
                
                print(f"Downloading new document: {text}")
                try:
                    # Download file using urllib
                    req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    
                    with urllib.request.urlopen(req, context=ctx, timeout=20) as response, open(file_path, 'wb') as out_file:
                        out_file.write(response.read())
                    
                    print(f"Saved locally to {file_path}")
                    
                    # Upload to Google Drive and delete local file
                    print(f"Uploading to Google Drive...")
                    gdrive_id = upload_to_gdrive(file_path, file_name)
                    if gdrive_id:
                        print(f"Successfully uploaded to Google Drive. File ID: {gdrive_id}")
                        # Keep local downloaded file as requested
                    
                    # Send LINE Message
                    message = f"\n📢 อัพเดทกฎหมายใหม่ (อย.)\nเรื่อง: {text}\nตรวจสอบได้ที่โฟลเดอร์: {DOWNLOAD_DIR}\nชื่อไฟล์: {file_name}"
                    send_line_message(message)
                    
                    # Update history
                    history.append(doc_id)
                    save_history(history)
                    new_downloads += 1
                    
                except Exception as e:
                    print(f"Error downloading {download_url}: {e}")

    print(f"[{datetime.datetime.now()}] Finished. Downloaded {new_downloads} new documents.")

if __name__ == "__main__":
    main()
