"""Local OpenAI-compatible embedding service and OpenCode Go adapter."""
import hashlib,json,os,pathlib,threading,uuid
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import requests
from fastembed import TextEmbedding
ROOT=pathlib.Path(__file__).resolve().parents[1]
MODEL='BAAI/bge-small-zh-v1.5'
embedder=TextEmbedding(model_name=MODEL,cache_dir=str(ROOT/'.local/model-cache'),threads=4,local_files_only=True)
embed_lock=threading.Lock()
class Handler(BaseHTTPRequestHandler):
 protocol_version='HTTP/1.1'
 def log_message(self,fmt,*args):
  print(self.address_string(),fmt%args,flush=True)
 def send_json(self,body,status=200):
  data=json.dumps(body,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 def do_GET(self):
  if self.path=='/health':return self.send_json({'status':'ok','embedding_model':MODEL})
  return self.send_json({'object':'list','data':[{'id':MODEL,'object':'model'},{'id':'deepseek-v4.1-flash','object':'model'}]})
 def do_POST(self):
  try:
   body=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))))
   if self.path.rstrip('/').endswith('/embeddings'):
    texts=body['input'];texts=[texts] if isinstance(texts,str) else texts
    with embed_lock: vectors=list(embedder.embed(texts,batch_size=32))
    return self.send_json({'object':'list','model':MODEL,'data':[{'object':'embedding','index':i,'embedding':v.tolist()} for i,v in enumerate(vectors)],'usage':{'prompt_tokens':sum(len(t) for t in texts),'total_tokens':sum(len(t) for t in texts)}})
   if not self.path.rstrip('/').endswith('/chat/completions'):return self.send_json({'error':'Unknown endpoint'},404)
   key=(ROOT/'.local/secrets/opencode-go.key').read_text().strip()
   messages=body.get('messages',[]);seed=next((m.get('content','') for m in messages if m.get('role')=='user'),'default')
   session=self.headers.get('x-opencode-session') or 'weknora-'+hashlib.sha256(json.dumps(seed,ensure_ascii=False).encode()).hexdigest()[:32]
   body.setdefault('max_tokens',4096)
   body['reasoning_effort']='low'
   resp=requests.post('https://opencode.ai/zen/go/v1/chat/completions',json=body,headers={'Authorization':'Bearer '+key,'User-Agent':'weknora-local/1.0','x-opencode-session':session},stream=True,timeout=(30,240))
   self.send_response(resp.status_code);self.send_header('Content-Type',resp.headers.get('Content-Type','application/json'));self.send_header('Connection','close');self.end_headers();self.close_connection=True
   try:
    for data in resp.iter_content(chunk_size=1 if body.get('stream') else 8192):
     if data:self.wfile.write(data);self.wfile.flush()
   finally:resp.close()
  except (BrokenPipeError,ConnectionResetError):pass
  except Exception as e:
   print(type(e).__name__,str(e),flush=True)
   try:self.send_json({'error':type(e).__name__+': '+str(e)},502)
   except Exception:pass
if __name__=='__main__':
 print('Model gateway listening on :18083',flush=True)
 bridge=os.environ.get('HOST_BRIDGE_IP','172.17.0.1')
 local=ThreadingHTTPServer(('127.0.0.1',18083),Handler)
 threading.Thread(target=local.serve_forever,daemon=True).start()
 ThreadingHTTPServer((bridge,18083),Handler).serve_forever()
