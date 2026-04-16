import os
import sys
import json
import ssl
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import datetime
import requests

# Configuration
CONFIG = [
    {
        "url": "https://food.fda.moph.go.th/food-law/category/announcement-of-the-ministry-of-public-health-1?ppp=50&kw=&page=1",
        "dir": r"D:\app-fda-audit\law_library",
        "name": "Ministry of Public Health Announcement"
    },
    {
        "url": "https://food.fda.moph.go.th/food-law/category/fda-announcement?ppp=50&kw=&page=1",
        "dir": r"D:\app-fda-audit\fda_announce",
        "name": "FDA Announcement"
    }
]

BASE_URL = 'https://food.fda.moph.go.th/'
# Reusing LINE configuration from v1 if available, but the request didn't explicitly ask for it.
# However, keeping the boilerplate for notifications is usually good.
LINE_TOKEN = "f5TsMgr7pvKU3PEuU0lCOGieO9mASGEKS/EuPqVdT3RXIR36JrCg/fi5dAQg4yCe3Ah+/sLL90H9LCbgvNkg7xxXrWZ2iEMkuiKxiACrzQ1/vrqj6EFCTx+OX2W9s2F3djgsJ5oNZEzFtdpMg4wCjAdB04t89/1O/w1cDnyilFU="
LINE_TO = "C2ef95828c48e59643efe8c128e92e79b"

def send_line_message(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "to": LINE_TO,
        "messages": [{"type": "text", "text": message}]
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            print(f"LINE Message sent successfully!")
        else:
            print(f"Failed to send LINE Message. Status: {response.status_code}, Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to send Line Message: {e}")
        return False

def clean_filename(filename):
    return "".join(c for c in filename if c.isalnum() or c in " ._-").strip()

def fetch_page(url):
    print(f"[{datetime.datetime.now()}] Fetching: {url}")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching URL {url}: {e}")
        return None

def download_file(url, filepath):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response, open(filepath, 'wb') as out_file:
            out_file.write(response.read())
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def process_category(config):
    url = config['url']
    target_dir = config['dir']
    category_name = config['name']
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        
    html_content = fetch_page(url)
    if not html_content:
        return 0

    soup = BeautifulSoup(html_content, 'html.parser')
    new_downloads = 0
    
    # Existing files in directory
    existing_files = os.listdir(target_dir)

    links = soup.find_all('a')
    for a in links:
        href = a.get('href')
        text = a.text.strip()
        
        if href and 'media.php' in href:
            parsed_url = urllib.parse.urlparse(href)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            # File name from query params or fallback
            file_name = query_params.get('name', [f"document_{query_params.get('id', ['unknown'])[0]}.pdf"])[0]
            file_name = clean_filename(file_name)
            
            if not file_name.endswith('.pdf'):
                file_name += '.pdf'
                
            file_path = os.path.join(target_dir, file_name)
            
            if file_name not in existing_files:
                download_url = href if href.startswith('http') else urllib.parse.urljoin(BASE_URL, href)
                print(f"New file found: {file_name} ({category_name})")
                
                if download_file(download_url, file_path):
                    print(f"Successfully downloaded to {file_path}")
                    new_downloads += 1
                    # Notify via LINE if a token is present
                    if LINE_TOKEN:
                        msg = (f"\n🔔 ตรวจพบประกาศใหม่!\n"
                               f"----------------------------\n"
                               f"📁 ประเภท: {category_name}\n"
                               f"📄 เรื่อง: {text if text else file_name}\n"
                               f"💾 บันทึกไว้ที่: {target_dir}\n"
                               f"----------------------------\n"
                               f"ตรวจสอบได้ในเครื่องคอมพิวเตอร์ของคุณ")
                        send_line_message(msg)
            else:
                # File already exists
                pass
                
    return new_downloads

def main():
    print(f"--- Scraper Started at {datetime.datetime.now()} ---")
    target = sys.argv[1].lower() if len(sys.argv) > 1 else None
    total_new = 0
    for category in CONFIG:
        if target == 'moph' and category['name'] != "Ministry of Public Health Announcement":
            continue
        if target == 'fda' and category['name'] != "FDA Announcement":
            continue
        new_count = process_category(category)
        print(f"Completed {category['name']}: {new_count} new files downloaded.")
        total_new += new_count
    print(f"--- Job Finished. Total new files: {total_new} ---")

if __name__ == "__main__":
    main()
