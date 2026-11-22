"""Resume large public downloads through proxies that stall on long responses."""
import concurrent.futures,hashlib,pathlib,subprocess,sys,time

def download(url,path,size,workers=8,headers=()):
 path=pathlib.Path(path);chunks=path.with_name(path.name+'.parts');chunks.mkdir(parents=True,exist_ok=True)
 cmd=['curl','-fLsSI','--retry','2','--max-time','30',url,'-o','/dev/null','-w','%{url_effective}']
 for h in headers:cmd+=['-H',h]
 direct=subprocess.check_output(cmd,text=True).strip()
 step=512*1024
 def part(i):
  start=i*step;end=min(size-1,start+step-1);p=chunks/str(i)
  if p.exists() and p.stat().st_size==end-start+1:return p
  for attempt in range(5):
   args=['curl','-fLsS','--max-time','25','--range',f'{start}-{end}',direct,'-o',str(p)]
   # Registry redirected blobs use signed URLs, so do not forward Authorization.
   if direct==url:
    for h in headers:args+=['-H',h]
   r=subprocess.run(args,capture_output=True)
   if r.returncode==0 and p.stat().st_size==end-start+1:return p
  raise RuntimeError(f'Failed chunk {i} of {path.name}')
 count=(size+step-1)//step
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
  for n,_ in enumerate(ex.map(part,range(count)),1):
   if n%20==0 or n==count:print(path.name,n,'/',count,flush=True)
 with path.open('wb') as out:
  for i in range(count):out.write((chunks/str(i)).read_bytes())
 return path
if __name__=='__main__':download(sys.argv[1],sys.argv[2],int(sys.argv[3]))
