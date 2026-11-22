"""Download the ten selected LCSC PDFs and verify their recorded SHA-256 hashes."""
import concurrent.futures,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
def run(item):
 path=ROOT/item['file']
 if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']:
  print(item['part'],'verified',flush=True);return
 subprocess.run(['curl','-fLsS','--retry','3','--max-time','120',item['pdf_url'],'-o',str(path)],check=True)
 assert path.read_bytes().startswith(b'%PDF'),f'Invalid PDF: {path}'
 assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256'],f'SHA-256 mismatch: {path}'
 print(item['part'],'downloaded and verified',flush=True)
if __name__=='__main__':
 items=json.loads((ROOT/'datasheets/manifest.json').read_text())
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(run,items))
 print(f'{len(items)} PDFs ready')
