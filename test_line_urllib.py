import urllib.request
import urllib.parse
import ssl

token = "f5TsMgr7pvKU3PEuU0lCOGieO9mASGEKS/EuPqVdT3RXIR36JrCg/fi5dAQg4yCe3Ah+/sLL90H9LCbgvNkg7xxXrWZ2iEMkuiKxiACrzQ1/vrqj6EFCTx+OX2W9s2F3djgsJ5oNZEzFtdpMg4wCjAdB04t89/1O/w1cDnyilFU="
url = "https://notify-api.line.me/api/notify"
headers = {"Authorization": f"Bearer {token}"}
data = urllib.parse.urlencode({"message": "Test Message from AI Agent"}).encode('utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request(url, headers=headers, data=data, method='POST')

try:
    with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
        print(response.getcode(), response.read().decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
