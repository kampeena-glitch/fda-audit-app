import requests

token = "f5TsMgr7pvKU3PEuU0lCOGieO9mASGEKS/EuPqVdT3RXIR36JrCg/fi5dAQg4yCe3Ah+/sLL90H9LCbgvNkg7xxXrWZ2iEMkuiKxiACrzQ1/vrqj6EFCTx+OX2W9s2F3djgsJ5oNZEzFtdpMg4wCjAdB04t89/1O/w1cDnyilFU="
url = "https://notify-api.line.me/api/notify"
headers = {"Authorization": f"Bearer {token}"}
data = {"message": "Test Message from AI Agent"}

response = requests.post(url, headers=headers, data=data)
print(response.status_code, response.text)
