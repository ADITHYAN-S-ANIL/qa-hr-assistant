import urllib.parse
import urllib.request
from bs4 import BeautifulSoup

def search_duckduckgo(query: str) -> str:
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    try:
        html = urllib.request.urlopen(req).read()
        soup = BeautifulSoup(html, 'html.parser')
        results = ""
        for a in soup.find_all('a', class_='result__snippet'):
            results += a.text + "\n"
        return results if results else "No results found."
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    print(search_duckduckgo("yesterday who won barcelona vs newcastle"))
