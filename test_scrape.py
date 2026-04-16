import requests
from bs4 import BeautifulSoup
import time

url = 'https://food.fda.moph.go.th/food-law/category/announcement-of-the-ministry-of-public-health-1?ppp=50&kw=&page=1'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

try:
    print("Fetching URL...")
    start_time = time.time()
    response = requests.get(url, headers=headers, timeout=15, verify=False)
    print(f"Status Code: {response.status_code}, Time: {time.time() - start_time:.2f}s")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    announcements = soup.select('div.list-item') # Attempting finding the correct container.
    print(f"Found {len(announcements)} list-items")
    
    if len(announcements) == 0:
        # Try generic links
        links = soup.find_all('a')
        print(f"Total links: {len(links)}")
        for a in links:
            text = a.text.strip()
            if 'ประกาศ' in text:
                print(f"Link: {text} | URL: {a.get('href')}")
                
except Exception as e:
    print(f"Error: {e}")
