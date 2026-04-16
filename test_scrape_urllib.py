import urllib.request
import ssl

url = 'https://food.fda.moph.go.th/food-law/category/announcement-of-the-ministry-of-public-health-1?ppp=50&kw=&page=1'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

try:
    with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
        html = response.read().decode('utf-8')
        print(html[:1000])
except Exception as e:
    print(f"Error: {e}")
