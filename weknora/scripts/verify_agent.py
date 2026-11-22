import json,pathlib,requests
R=pathlib.Path(__file__).resolve().parents[1];a=json.loads((R/'.local/auth-response.json').read_text());st=json.loads((R/'.local/knowledge-state.json').read_text());s=requests.Session();s.trust_env=False;s.headers['Authorization']='Bearer '+a['token'];B='http://127.0.0.1:18081/api/v1'
r=s.post(B+'/sessions',json={'title':'已验证：CH340C晶振和供电（引用手册）'});r.raise_for_status();sid=r.json()['data']['id'];st['example_session_id']=sid;(R/'.local/knowledge-state.json').write_text(json.dumps(st,indent=2))
r=s.post(B+'/knowledge-chat/'+sid,json={'query':'请用三句话简要回答（200字以内）：CH340C需要外部晶振吗？5V供电和3.3V供电时V3引脚应如何连接？请附手册引用。','agent_id':st['agent_id'],'agent_enabled':False,'summary_model_id':st['chat_model_id'],'knowledge_base_ids':[st['knowledge_base_id']],'disable_title':True},stream=True,timeout=240);r.raise_for_status()
answer=[];done=False;truncated=False
with (R/'evidence/verified-qa-stream.txt').open('w') as out:
 for line in r.iter_lines(decode_unicode=True):
  if not line:continue
  out.write(line+'\n');out.flush()
  if line.startswith('data:'):
   try:d=json.loads(line[5:])
   except ValueError:continue
   if d.get('response_type')=='answer':
    answer.append(d.get('content',''));truncated|=d.get('data',{}).get('truncated',False)
   if d.get('response_type')=='complete':done=True
text=''.join(answer);(R/'evidence/CH340C问答.md').write_text(text);print(text);print('complete',done,'truncated',truncated,'citations',text.count('<kb '))
assert done and not truncated and '<kb ' in text
