import urllib.request
import json

def get(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as res:
        return res.status, res.read().decode('utf-8')

def post(url, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as res:
        return res.status, json.loads(res.read().decode('utf-8'))

# 1. Test frontend
status, html = get('http://127.0.0.1:5173/')
print('[+] Vite Frontend Status:', status)
print('[+] Has tab-btn-explorer:', 'tab-btn-explorer' in html)
print('[+] Has tab-explorer:', 'id="tab-explorer"' in html)

# 2. Test Explorer Apps API
status, apps_data = post('http://127.0.0.1:8000/api/explorer/crawl', {'app': 'com.miui.calculator'})
print('[+] Crawl Status:', status, '| App:', apps_data['app'], '| Indexed:', apps_data['total_ui_elements_indexed'])

# 3. Test Semantic UI Query API
status, query_data = post('http://127.0.0.1:8000/api/explorer/query-ui', {'app': 'com.miui.calculator', 'query': 'clear all numbers on screen', 'n_results': 1})
match1 = query_data['matches'][0]
print(f"[+] Calculator Match: '{match1['metadata']['label']}' at ({match1['metadata']['center_x']}, {match1['metadata']['center_y']}) | Sim: {match1['similarity']}")

# 4. Test Chrome Query API
status, query_data2 = post('http://127.0.0.1:8000/api/explorer/query-ui', {'app': 'com.android.chrome', 'query': 'speak voice query to search', 'n_results': 1})
match2 = query_data2['matches'][0]
print(f"[+] Chrome Match: '{match2['metadata']['label']}' at ({match2['metadata']['center_x']}, {match2['metadata']['center_y']}) | Sim: {match2['similarity']}")

# 5. Test Settings Query API
status, query_data3 = post('http://127.0.0.1:8000/api/explorer/query-ui', {'app': 'com.android.settings', 'query': 'connect to wifi network', 'n_results': 1})
match3 = query_data3['matches'][0]
print(f"[+] Settings Match: '{match3['metadata']['label']}' at ({match3['metadata']['center_x']}, {match3['metadata']['center_y']}) | Sim: {match3['similarity']}")
