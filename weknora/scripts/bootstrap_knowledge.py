import json,pathlib,secrets,sys,time
import requests
ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:18081/api/v1'
s=requests.Session();s.trust_env=False
cred_path=ROOT/'.local/login.json'
if not cred_path.exists():
 cred_path.write_text(json.dumps({'username':'芯片知识库管理员','email':'admin@weknora.local','password':'Wk!'+secrets.token_urlsafe(15)},ensure_ascii=False,indent=2));cred_path.chmod(0o600)
cred=json.loads(cred_path.read_text())
def call(method,path,**kwargs):
 r=s.request(method,BASE+path,timeout=180,**kwargs)
 if not r.ok:raise RuntimeError(str(r.status_code)+' '+r.text[:1500])
 return r.json()
r=s.post(BASE+'/auth/register',json=cred)
if r.status_code not in [200,201,409] and 'exist' not in r.text.lower():print('registration',r.status_code,r.text[:300])
r=call('POST','/auth/login',json={'email':cred['email'],'password':cred['password']})
(ROOT/'.local/auth-response.json').write_text(json.dumps(r));(ROOT/'.local/auth-response.json').chmod(0o600)
print('login response keys',list(r),flush=True)
print('login data keys',list(r.get('data',{})),flush=True)
s.headers['Authorization']='Bearer '+r['token']
s.headers['X-Tenant-ID']=str(r['active_tenant']['id'])
existing=call('GET','/models').get('data',[])
def model(name,typ,display):
 found=next((m for m in existing if m['name']==name),None)
 if found:return found['id']
 data={'name':name,'display_name':display,'type':typ,'source':'remote','parameters':{'base_url':'http://host.docker.internal:18083/v1','api_key':'local-gateway','provider':'openai','interface_type':'openai','embedding_parameters':{'dimension':512}}}
 result=call('POST','/models',json=data);print('created model',name,flush=True);return result['data']['id']
chat=model('deepseek-v4.1-flash','KnowledgeQA','OpenCode Go · DeepSeek V4.1 Flash')
embedding=model('BAAI/bge-small-zh-v1.5','Embedding','本地中文向量 BGE Small')
kbs=call('GET','/knowledge-bases').get('data',[])
kb=next((k for k in kbs if k['name']=='嘉立创芯片手册（10篇）'),None)
if kb is None:
 payload={'name':'嘉立创芯片手册（10篇）','type':'document','description':'来自嘉立创商城的10份芯片原厂PDF：USB、电源、运放、比较器、移位寄存器、Flash与ESP32-C3。回答请引用手册，并区分不同厂商版本。','embedding_model_id':embedding,'summary_model_id':chat,'chunking_config':{'chunk_size':900,'chunk_overlap':120,'split_markers':['\n\n','\n','。'],'parser_engine_rules':[{'file_types':['pdf'],'engine':'builtin'}]},'image_processing_config':{'enable_multimodal':False},'question_generation_config':{'enabled':False},'storage_config':{'provider':'local'}}
 kb=call('POST','/knowledge-bases',json=payload)['data'];print('created KB',kb['id'],flush=True)
state={'chat_model_id':chat,'embedding_model_id':embedding,'knowledge_base_id':kb['id']}
(ROOT/'.local/knowledge-state.json').write_text(json.dumps(state,indent=2))
manifest=json.loads((ROOT/'datasheets/manifest.json').read_text())
known=call('GET',f"/knowledge-bases/{kb['id']}/knowledge?page_size=100").get('data',[])
if isinstance(known,dict):known=known.get('items',known.get('data',[]))
for item in manifest:
 f=ROOT/item['file'];existing=next((d for d in known if d.get('file_name')==f.name),None)
 if existing:item['knowledge_id']=existing['id'];continue
 with f.open('rb') as file:
  response=call('POST',f"/knowledge-bases/{kb['id']}/knowledge/file",files={'file':(f.name,file,'application/pdf')},data={'enable_multimodal':'false'})
 item['knowledge_id']=response['data']['id'];print('uploaded',f.name,item['knowledge_id'],flush=True)
(ROOT/'datasheets/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print('All documents submitted',flush=True)
