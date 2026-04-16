import requests
import json

token = "f5TsMgr7pvKU3PEuU0lCOGieO9mASGEKS/EuPqVdT3RXIR36JrCg/fi5dAQg4yCe3Ah+/sLL90H9LCbgvNkg7xxXrWZ2iEMkuiKxiACrzQ1/vrqj6EFCTx+OX2W9s2F3djgsJ5oNZEzFtdpMg4wCjAdB04t89/1O/w1cDnyilFU="
url = "https://api.line.me/v2/bot/message/broadcast"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
data = {
    "messages": [
        {
            "type": "text",
            "text": "Test Message from AI Agent (Messaging API)"
        }
    ]
}

response = requests.post(url, headers=headers, json=data)
print(response.status_code, response.text)
