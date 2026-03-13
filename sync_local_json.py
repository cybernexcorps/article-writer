"""Sync the live n8n workflow back to article-writer-v1.0.json"""
import urllib.request, json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

KEY = os.environ.get('N8N_API_KEY', '')
if not KEY:
    print('Error: set N8N_API_KEY env var'); sys.exit(1)

req = urllib.request.Request(
    'https://ddvb.app.n8n.cloud/api/v1/workflows/olEdXGbrRTak2c9v',
    headers={'X-N8N-API-KEY': KEY}
)
with urllib.request.urlopen(req) as r:
    wf = json.loads(r.read().decode('utf-8'))

out_path = 'workflow/article-writer-v1.0.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)

print(f'Saved {len(wf.get("nodes", []))} nodes to article-writer-v1.0.json')
