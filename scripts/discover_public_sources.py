"""Read-only discovery of public source interfaces; no account or token required."""
import concurrent.futures
import html
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'data' / 'research'
URLS = {
    'smard_urls': 'https://www.smard.de/resource/sites/bnetza/editorial/content/0__js_charts__0/lib/intern/mod_urls-220146-5.js',
    'smard_csv': 'https://www.smard.de/resource/sites/bnetza/editorial/content/0__js_charts__0/lib/intern/mod_csv-220142-3.js',
    'smard_prices': 'https://www.smard.de/page/home/topic-article/46/218364/modellierte-strompreise',
    'gas_industry': 'https://www.bundesnetzagentur.de/DE/Gasversorgung/aktuelle_gasversorgung/_svg/GasverbrauchRLM_woechentlich/Gasverbrauch_RLM_W_2023_2.html',
    'gas_dashboard': 'https://www.bundesnetzagentur.de/DE/Gasversorgung/aktuelle_gasversorgung/start.html',
    'kba_catalog': 'https://www.arcgis.com/sharing/rest/search?f=json&num=100&q=group%3A79ca799ea9db493fb06eb08fbdd87117',
}

def read(item):
    name, url = item
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'Stadtwerke-MVP-research/0.1'}), timeout=25) as response:
            raw = response.read()
        content = raw.decode('utf-8', errors='replace')
        (ROOT / (name + '.txt')).write_text(content)
        if name == 'kba_catalog':
            result = json.loads(content)
            details = [{'id':r['id'], 'title':r['title'], 'type':r['type'], 'url':r.get('url')} for r in result.get('results', [])]
        elif name.startswith('gas'):
            details = [urllib.parse.urljoin(url, html.unescape(x)) for x in re.findall(r'href="([^"]+)"',content) if any(t in x.lower() for t in ['.csv','.xlsx','gasverbrauchslp','gasverbrauchrlm'])]
        elif name.startswith('smard_') and name != 'smard_prices':
            details = content[:18000]
        else:
            details = [content[max(0,m.start()-100):m.end()+200] for m in re.finditer(r'(?i)(?:\.csv|data-config|data-chart|csv_url|csvUrl|mod_charts)',content)][-20:]
        return {'source':name,'bytes':len(raw),'details':details}
    except Exception as exc:
        return {'source':name,'error':str(exc)}

if __name__ == '__main__':
    ROOT.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(read, URLS.items()):
            print(json.dumps(result,ensure_ascii=False))
