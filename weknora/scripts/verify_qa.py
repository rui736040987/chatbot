import json,pathlib,requests,time
R=pathlib.Path(__file__).resolve().parents[1];a=json.loads((R/'.local/auth-response.json').read_text());st=json.loads((R/'.local/knowledge-state.json').read_text());s=requests.Session();s.trust_env=False;s.headers['Authorization']='Bearer '+a['token'];B='http://127.0.0.1:18081/api/v1'
def call(m,p,**kw):
 r=s.request(m,B+p,timeout=240,**kw);r.raise_for_status();return r.json()
search=call('POST','/knowledge-bases/'+st['knowledge_base_id']+'/hybrid-search',json={'query_text':'CH340C 是否需要外部晶振，工作电压是多少？','vector_threshold':0.1,'match_count':8})
(R/'evidence/retrieval.json').write_text(json.dumps(search,ensure_ascii=False,indent=2));print('search',str(search)[:1000],flush=True)
session=call('POST','/sessions',json={'title':'芯片手册验证：CH340C晶振和供电'})
print('session',str(session)[:500],flush=True)
sid=session['data']['id'];st['example_session_id']=sid;(R/'.local/knowledge-state.json').write_text(json.dumps(st,indent=2))
payload={'query':'请根据CH340C数据手册回答：CH340C是否需要外部晶振？它支持哪些供电电压？请引用检索到的资料，不要混淆其他CH340型号。','knowledge_base_ids':[st['knowledge_base_id']],'summary_model_id':st['chat_model_id'],'agent_enabled':False,'disable_title':True}
r=s.post(B+'/knowledge-chat/'+sid,json=payload,stream=True,timeout=240);print('chat status',r.status_code,flush=True)
with (R/'evidence/qa-stream.txt').open('w') as out:
 for line in r.iter_lines(decode_unicode=True):
  if line:out.write(line+'\n');out.flush()
print('chat stream saved',flush=True)
