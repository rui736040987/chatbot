"""Build physical-page evidence from an operator-owned manifest; no fixed IDs."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
import pypdfium2 as pdfium

BASE = Path(__file__).resolve().parents[1]

def build(manifest, output):
    items = json.loads(manifest.read_text())
    result = []
    output.mkdir(parents=True, exist_ok=True)
    for item in items:
        doc_id, kb = item['id'], item['kb']
        if not all(isinstance(x, str) and x and all(c.isalnum() or c in '-_' for c in x) for x in [doc_id, kb]):
            raise ValueError('Document and KB IDs must be native IDs, not paths')
        path = Path(item['path'])
        if not path.is_absolute():
            path = BASE / path
        with pdfium.PdfDocument(path) as doc:
            pages = []
            for page in doc:
                tp = page.get_textpage()
                pages.append(tp.get_text_range())
                tp.close()
                page.close()
        shutil.copyfile(path, output / f'{doc_id}.pdf')
        result.append({'id': doc_id, 'kb': kb, 'title': item.get('title', path.name),
                       'pages': pages, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    tmp = output / 'catalog.json.tmp'
    tmp.write_text(json.dumps(result, ensure_ascii=False))
    tmp.replace(output / 'catalog.json')
    print(f'Catalog: {len(result)} PDFs / {sum(len(d["pages"]) for d in result)} physical pages')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=BASE / '.local/pdf-sources.json')
    parser.add_argument('--output', type=Path, default=BASE / '.local/deerflow-runtime/pdf-catalog')
    args = parser.parse_args()
    build(args.manifest, args.output)
