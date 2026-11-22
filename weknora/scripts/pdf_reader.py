"""Serve WeKnora's native PDFParser via its documented HTTP docreader protocol."""
import base64,json,os,pathlib,sys,types,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'WeKnora'))
# Load the PDF submodule without eagerly importing unrelated Office parsers.
pkg=types.ModuleType('docreader.parser');pkg.__path__=[str(ROOT/'WeKnora/docreader/parser')];sys.modules['docreader.parser']=pkg
os.environ.setdefault('DOCREADER_PDF_EXTRACT_EMBEDDED_IMAGES','false')
from docreader.parser.pdf_parser import PDFParser
class Handler(BaseHTTPRequestHandler):
 def send(self,data,status=200):
  payload=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
 def do_GET(self):self.send({'status':'ok','parser':'WeKnora PDFParser (pypdfium2)'})
 def do_POST(self):
  try:
   if self.path=='/list-engines':return self.send({'engines':[{'name':'builtin','description':'WeKnora native PDF parser','file_types':['pdf'],'available':True}]})
   if self.path!='/read':return self.send({'error':'Unknown endpoint'},404)
   if int(self.headers.get('Content-Length','0'))>75*1024*1024:return self.send({'error':'File too large'},413)
   req=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))))
   data=base64.b64decode(req['file_content']);doc=PDFParser(file_name=req.get('file_name','document.pdf'),file_type='pdf').parse(data)
   self.send({'markdown_content':doc.content,'source_blocks':[{'start':b['start'],'end':b['end'],'locator_json':json.dumps(b['locator'],ensure_ascii=False)} for b in doc.source_blocks],'metadata':{k:str(v) for k,v in doc.metadata.items()},'image_refs':[]})
   print(req.get('file_name'),len(doc.content),'characters',flush=True)
  except Exception as e:self.send({'error':str(e)},500)
if __name__=='__main__':
 bridge=os.environ.get('HOST_BRIDGE_IP','172.17.0.1')
 local=ThreadingHTTPServer(('127.0.0.1',18084),Handler)
 threading.Thread(target=local.serve_forever,daemon=True).start()
 ThreadingHTTPServer((bridge,18084),Handler).serve_forever()
