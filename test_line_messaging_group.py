import requests

LINE_TOKEN = "f5TsMgr7pvKU3PEuU0lCOGieO9mASGEKS/EuPqVdT3RXIR36JrCg/fi5dAQg4yCe3Ah+/sLL90H9LCbgvNkg7xxXrWZ2iEMkuiKxiACrzQ1/vrqj6EFCTx+OX2W9s2F3djgsJ5oNZEzFtdpMg4wCjAdB04t89/1O/w1cDnyilFU="

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
            "text": "🤖 ทดสอบระบบ: ตั้งค่าสำเร็จ! บอทพร้อมส่งแจ้งเตือนการอัพเดทกฎหมายใหม่ของ อย. เข้ากลุ่มนี้แล้วครับ"
        }
    ]
}

response = requests.post(url, headers=headers, json=data)
print(response.status_code)
print(response.text)
