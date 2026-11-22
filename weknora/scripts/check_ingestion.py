import json,pathlib,requests
R=pathlib.Path(__file__).resolve().parents[1];a=json.loads((R/'.local/auth-response.json').read_text());st=json.loads((R/'.local/knowledge-state.json').read_text());s=requests.Session();s.trust_env=False;s.headers['Authorization']='Bearer '+a['token']
r=s.get('http://127.0.0.1:18081/api/v1/knowledge-bases/'+st['knowledge_base_id']+'/knowledge',params={'page_size':100});d=r.json();(R/'evidence/ingestion-status.json').write_text(json.dumps(d,ensure_ascii=False,indent=2));print(json.dumps(d,ensure_ascii=False)[:6000])
