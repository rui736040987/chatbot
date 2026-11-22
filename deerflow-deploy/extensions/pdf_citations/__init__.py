"""Local citation adapter using DeerFlow's public provider/router contracts."""
import json
import os
import hashlib
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from difflib import SequenceMatcher
from urllib.parse import quote, urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from deerflow_extension_api import extension
from deerflow_extension_api.auth import resolve_principal
from deerflow.knowledge import KnowledgeRequestContext, KnowledgeSource, RetrievalHit, RetrievalResult
from deerflow_extension_weknora.provider import WeKnoraProvider
from deerflow.knowledge_scope import execution_scope

ROOT = Path('/opt/pdf-catalog')
DEERFLOW_URL = os.environ.get('DEERFLOW_PUBLIC_URL', 'http://localhost:2026').rstrip('/')
WEKNORA_URL = os.environ.get('WEKNORA_PUBLIC_URL', 'http://localhost:18088').rstrip('/')


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKC', text).lower() if c.isalnum())


class PageProvider(WeKnoraProvider):
    def __init__(self, config):
        super().__init__(config)
        self.docs = json.loads((ROOT / 'catalog.json').read_text())
        self.by_title = {d['title']: d for d in self.docs}
        self.index = {}
        self.pdf_hashes = {d['id']: hashlib.md5((ROOT / f"{d['id']}.pdf").read_bytes()).hexdigest() for d in self.docs}
        for d in self.docs:
            normalized = [normalize(p) for p in d['pages']]
            grams = defaultdict(set)
            for i, p in enumerate(normalized):
                for j in range(0, max(0, len(p) - 23), 8):
                    grams[p[j:j+24]].add(i)
            self.index[d['id']] = (normalized, grams)

    async def admitted(self, doc, context):
        datasets = await self._datasets(context)
        scope = context.scope or {'mode': 'all'}
        if scope.get('mode') == 'disabled':
            raise PermissionError('Knowledge disabled')
        for ds in datasets.values():
            if ds.native_id != doc['kb']:
                continue
            if scope.get('mode') == 'selected' and ds.id not in scope.get('dataset_ids', []):
                continue
            filters = {x['dataset_id']: x['document_ids'] for x in scope.get('document_filters', [])}
            if ds.id in filters and doc['id'] not in filters[ds.id]:
                continue
            await self._document(ds, doc['id'])
            return ds
        raise PermissionError('Document unavailable')

    def locate(self, doc, text):
        needle = normalize(text)
        pages, grams = self.index[doc['id']]
        votes = Counter()
        for i in range(0, max(0, len(needle)-23)):
            votes.update(grams.get(needle[i:i+24], ()))
        found = []
        for i, count in votes.most_common(4):
            match = SequenceMatcher(None, needle, pages[i], autojunk=False).find_longest_match()
            # Long exact overlap excludes headers, page-footers and incidental identifiers.
            if match.size >= 64:
                found.append((i+1, match.size, match.b))
        return sorted(found, key=lambda x: -x[1])[:2]

    def page_hit(self, doc, page, position, dataset_name, score=None):
        raw = doc['pages'][page-1]
        offsets = [i for i, c in enumerate(raw) for n in unicodedata.normalize('NFKC', c).lower() if n.isalnum()]
        start = offsets[position] if position < len(offsets) else 0
        text = f'PDF physical page {page} (1-based):\n' + raw[max(0, start-60):start+600]
        url = f"{DEERFLOW_URL}/api/plugins/pdf-citations/documents/{doc['id']}#page={page}"
        source = KnowledgeSource(provider='weknora', title=doc['title'], excerpt=text,
                                 dataset_name=dataset_name, url=url, page=page)
        return RetrievalHit(content=text, source=source, score=score)

    async def search_scoped(self, query, *, context):
        # Explicit bridge from native MCP excerpts to the existing citation contract.
        # It cannot register arbitrary/model-invented pages: the supplied quotation
        # must occur in the original PDF, and scope admission is checked live.
        if query.startswith('pdf-evidence '):
            args = json.loads(query[len('pdf-evidence '):])
            if set(args) != {'document_id', 'quote'} or not isinstance(args['quote'], str):
                raise ValueError('Expected document_id and verbatim quote')
            doc = next((d for d in self.docs if d['id'] == args['document_id']), None)
            if doc is None:
                raise FileNotFoundError('PDF not catalogued')
            ds = await self.admitted(doc, context)
            needle = normalize(args['quote'])
            if len(needle) < 40:
                raise ValueError('Quote needs at least 40 letters/digits')
            pages, _ = self.index[doc['id']]
            matches = [(i+1, p.index(needle)) for i, p in enumerate(pages) if needle in p]
            return RetrievalResult(hits=[self.page_hit(doc, p, pos, ds.name) for p, pos in matches[:4]])
        result = await super().search_scoped(query, context=context)
        hits, seen, admitted = [], set(), set()
        for hit in result.hits:
            doc = self.by_title.get(hit.source.title) if hit.source else None
            if not doc:
                hits.append(hit)
                continue
            if doc['id'] not in admitted:
                await self.admitted(doc, context)
                admitted.add(doc['id'])
            matches = self.locate(doc, hit.content)
            if not matches:
                hits.append(hit)
            for page, overlap, position in matches:
                key = (doc['id'], page)
                if key not in seen:
                    seen.add(key)
                    hits.append(self.page_hit(doc, page, position, hit.source.dataset_name, hit.score))
        return RetrievalResult(hits=hits)

    async def entries_search(self, query, *, context):
        """Native Wiki discovery plus explicitly paginated, source-bound evidence."""
        scope = execution_scope(context.scope) if context.scope is not None else {'mode': 'all'}
        if scope['mode'] == 'disabled':
            raise PermissionError('Knowledge disabled')
        if scope.get('document_filters'):
            raise ValueError('Wiki pages may span documents; use document search for document filters')
        datasets = await self._datasets(context)
        selected = scope['dataset_ids'] if scope['mode'] == 'selected' else list(datasets)
        if not set(selected) <= datasets.keys():
            raise PermissionError('Unknown dataset')
        requested = None
        if query.startswith('wiki-page '):
            requested = json.loads(query[len('wiki-page '):])
            if set(requested) - {'knowledge_base_id', 'slug', 'offset', 'limit'}:
                raise ValueError('Invalid Wiki read arguments')
            offset, limit = requested.get('offset', 0), requested.get('limit', 6)
            if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 12:
                raise ValueError('Invalid evidence pagination')
            if not requested.get('knowledge_base_id'):
                wiki_bases = [datasets[x].native_id for x in selected if datasets[x].wiki_enabled]
                if len(wiki_bases) != 1:
                    raise ValueError('Specify knowledge_base_id when several Wikis are in scope')
                requested['knowledge_base_id'] = wiki_bases[0]
            if requested['knowledge_base_id'] not in {datasets[x].native_id for x in selected}:
                raise PermissionError('Wiki outside scope')
        hits = []
        for key in selected:
            ds = datasets[key]
            if not ds.wiki_enabled or (requested and ds.native_id != requested['knowledge_base_id']):
                continue
            base = f'/api/v1/knowledgebase/{ds.native_id}/wiki'
            if requested:
                pages = [await self._request(ds.binding, 'GET', base+'/pages/'+quote(requested['slug'], safe='/'), envelope=False)]
            else:
                response = await self._request(ds.binding, 'GET', base+'/search', envelope=False,
                                               params={'q': query, 'limit': 3})
                pages = response.get('pages') or []
                if not pages:
                    seen = set()
                    for term in list(dict.fromkeys(t for t in query.split() if len(t) >= 2))[:4]:
                        response = await self._request(ds.binding, 'GET', base+'/search', envelope=False,
                                                       params={'q': term, 'limit': 3})
                        for page in response.get('pages') or []:
                            if page['slug'] not in seen:
                                pages.append(page)
                                seen.add(page['slug'])
                    pages = pages[:3]
                offset, limit = 0, 2
            for page in pages:
                if page.get('knowledge_base_id') != ds.native_id:
                    raise PermissionError('Wiki outside scope')
                if page.get('status') != 'published':
                    continue
                refs = page.get('chunk_refs') or []
                source_ids = {r.split('|', 1)[0] for r in (page.get('source_refs') or [])}
                cursor = {'knowledge_base_id': ds.native_id, 'slug': page['slug'], 'offset': offset, 'limit': 6}
                body = page.get('content', '') if requested else page.get('summary', '')
                text = (f"Wiki page: {page['title']}\nKB: {ds.native_id}\nSlug: {page['slug']}\n"
                        f"Source document IDs: {json.dumps(sorted(source_ids))}\n"
                        f"Evidence chunks: {len(refs)}; selected [{offset}:{min(offset+limit,len(refs))}].\n"
                        'Read full Wiki and original evidence with knowledge_entries_search query: wiki-page '
                        + json.dumps(cursor, ensure_ascii=False) + '\n'
                        + ('Next evidence offset: '+str(offset+limit)+'\n' if offset+limit < len(refs) else '')
                        + 'Wiki is generated synthesis; verify numerical claims against the original evidence below.\n'+body)
                url = WEKNORA_URL+'/platform/knowledge-bases/'+ds.native_id+'?'+urlencode({'tab':'wiki','slug':page['slug']})
                source = KnowledgeSource(provider='weknora',title='Wiki · '+page['title'],excerpt=text,dataset_name=ds.name,url=url)
                hits.append(RetrievalHit(content=text,source=source))
                for cid in refs[offset:offset+limit]:
                    chunk = (await self._request(ds.binding,'GET','/api/v1/chunks/by-id/'+quote(cid,safe='')))['data']
                    if chunk.get('knowledge_base_id') != ds.native_id or chunk.get('knowledge_id') not in source_ids:
                        raise PermissionError('Evidence outside Wiki sources')
                    if not chunk.get('is_enabled',False):
                        continue
                    doc = next((d for d in self.docs if d['id'] == chunk['knowledge_id']),None)
                    if doc is None:
                        continue
                    await self.admitted(doc,context)
                    by_page = defaultdict(list)
                    for loc in chunk.get('source_locators') or []:
                        number = loc.get('page')
                        if (loc.get('type') == 'pdf' and loc.get('mapping') == 'exact'
                            and loc.get('source_hash') == self.pdf_hashes[doc['id']]
                            and type(number) is int and 1 <= number <= len(doc['pages']) and loc.get('quote')):
                            if loc['quote'] not in by_page[number]:
                                by_page[number].append(loc['quote'])
                    for number, quotes in by_page.items():
                        text = (f"Original PDF evidence for Wiki {page['slug']}\nDocument ID: {doc['id']}\n"
                                f"Chunk ID: {cid}; chunk index: {chunk['chunk_index']}\n"
                                f"PDF physical page {number} (1-based); native exact source locator, source hash verified.\n"
                                +'\n'.join(quotes))
                        url = f"{DEERFLOW_URL}/api/plugins/pdf-citations/documents/{doc['id']}#page={number}"
                        source = KnowledgeSource(provider='weknora',title=doc['title'],excerpt=text,dataset_name=ds.name,url=url,page=number)
                        hits.append(RetrievalHit(content=text,source=source))
                    if not by_page:
                        text = f"Wiki {page['slug']} original chunk {cid}; document {doc['id']}; PDF page unverified.\n"+chunk['content']
                        hits.append(RetrievalHit(content=text,source=KnowledgeSource(provider='weknora',title=doc['title'],excerpt=text,dataset_name=ds.name)))
        return RetrievalResult(hits=hits)


@extension(api='0.2.7', name='pdf-citations')
def install(registry, config):
    provider = PageProvider(dict(config))
    if not registry.knowledge_provider('weknora', provider):
        raise RuntimeError('Knowledge provider API unavailable')
    router = APIRouter(prefix='/api/plugins/pdf-citations')

    @router.get('/documents/{document_id}')
    async def document(document_id: str, request: Request):
        principal = resolve_principal(request)
        if principal is None:
            raise HTTPException(401, 'Sign in required')
        doc = next((d for d in provider.docs if d['id'] == document_id), None)
        if not doc:
            raise HTTPException(404, 'Unknown document')
        try:
            # Route is bound to the same operator-authorized assistant as retrieval.
            await provider.admitted(doc, KnowledgeRequestContext(user_id=principal.user_id, agent_name='chip-docs'))
        except (PermissionError, FileNotFoundError):
            raise HTTPException(403, 'Document unavailable') from None
        return FileResponse(ROOT / f"{doc['id']}.pdf", media_type='application/pdf',
                            filename=doc['title'], content_disposition_type='inline',
                            headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})

    registry.routers([router])
