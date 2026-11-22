"""Contract tests against the actual PDFs and the installed DeerFlow formatter."""
import asyncio
import json
import unittest
from pathlib import Path
import yaml
from pdf_citations import PageProvider
from deerflow.knowledge import KnowledgeRequestContext
from deerflow.knowledge.sources import format_result, sources_from_messages

class Citations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provider = PageProvider(yaml.safe_load(Path('/app/backend/config.yaml').read_text())['plugins'][0]['config'])
        cls.doc = next(d for d in cls.provider.docs if d['id'] == 'f82f9530-58c6-405a-a9f4-f07cab35c47f')
        cls.context = KnowledgeRequestContext(user_id='0f03160c-dc51-42b2-a9b0-b3df10924016', agent_name='chip-docs')

    def test_cross_page_chunk_uses_both_physical_pages(self):
        d = self.doc
        joined = d['pages'][307][-800:] + d['pages'][308][:800]
        pages = {x[0] for x in self.provider.locate(d, joined)}
        self.assertEqual(pages, {308, 309})

    def test_no_locator_for_fabricated_evidence(self):
        self.assertEqual(self.provider.locate(self.doc, 'An entirely fabricated quotation with no original PDF evidence whatsoever.'), [])

    def test_exact_mcp_quote_and_shared_source_contract(self):
        async def run():
            for page, quote in [(308, 'Channel 4 SPI4_RX(1) SPI4_TX(1) USART1_RX SDIO - USART1_RX SDIO USART1_TX'),
                                (1066, 'Bit 3 DMAEN: DMA enable bit')]:
                # A longer actual original passage meets the minimum proof length.
                raw = self.doc['pages'][page-1]
                pos = raw.index(quote.split(' ')[0] + ' ' + quote.split(' ')[1]) if page == 1066 else raw.index('Channel 4 SPI4_RX')
                actual = raw[pos:pos+200]
                result = await self.provider.search_scoped('pdf-evidence '+json.dumps({'document_id':self.doc['id'], 'quote': actual}), context=self.context)
                self.assertEqual([h.source.page for h in result.hits], [page])
                content, artifact = format_result(result)
                sources = sources_from_messages([{'type':'tool', 'content':content, 'artifact':artifact}])
                self.assertEqual(len(sources), 1)
                self.assertEqual(sources[0].page, page)
                self.assertTrue(str(sources[0].url).endswith(f'#page={page}'))
        asyncio.run(run())

    def test_scope_cannot_be_bypassed_by_explicit_quote(self):
        async def run():
            query='pdf-evidence '+json.dumps({'document_id':self.doc['id'], 'quote':self.doc['pages'][307][:200]})
            datasets = await self.provider._datasets(self.context)
            main = next(d.id for d in datasets.values() if d.native_id != self.doc['kb'])
            large = next(d.id for d in datasets.values() if d.native_id == self.doc['kb'])
            for ctx in [KnowledgeRequestContext(user_id='unbound-user'),
                        KnowledgeRequestContext(user_id=self.context.user_id, agent_name='chip-docs', scope={'mode':'disabled'}),
                        KnowledgeRequestContext(user_id=self.context.user_id, agent_name='chip-docs', scope={'mode':'selected', 'dataset_ids':[main]}),
                        KnowledgeRequestContext(user_id=self.context.user_id, agent_name='chip-docs', scope={'mode':'selected', 'dataset_ids':[large], 'document_filters':[{'dataset_id':large, 'document_ids':['other-doc']} ]})]:
                with self.assertRaises(PermissionError):
                    await self.provider.search_scoped(query, context=ctx)
        asyncio.run(run())

    def test_wiki_native_evidence_and_citations(self):
        async def run():
            query = 'wiki-page '+json.dumps({'knowledge_base_id':'ba96e1d9-12a6-43a1-b836-d868c34eed68','slug':'entity/ch340c','offset':0,'limit':6})
            result = await self.provider.entries_search(query,context=self.context)
            self.assertTrue(result.hits[0].source.title.startswith('Wiki'))
            self.assertIn('slug=entity%2Fch340c',str(result.hits[0].source.url))
            evidence = [h for h in result.hits if h.source.page]
            self.assertTrue(evidence)
            self.assertTrue(all('native exact source locator' in h.content for h in evidence))
            content, artifact = format_result(result)
            sources = sources_from_messages([{'type':'tool','content':content,'artifact':artifact}])
            self.assertTrue(any(s.page for s in sources))
            self.assertTrue(any(s.title.startswith('Wiki') for s in sources))
            datasets = await self.provider._datasets(self.context)
            large = next(d.id for d in datasets.values() if d.native_id == self.doc['kb'])
            denied = KnowledgeRequestContext(user_id=self.context.user_id,agent_name='chip-docs',scope={'version':1,'mode':'selected','dataset_ids':[large]})
            with self.assertRaises(PermissionError):
                await self.provider.entries_search(query,context=denied)
            # A stale local PDF must never receive a native page locator.
            doc_id = '1b9aacf1-c450-4979-a3f6-6bf557654568'
            previous = self.provider.pdf_hashes[doc_id]
            try:
                self.provider.pdf_hashes[doc_id] = 'stale'
                stale = await self.provider.entries_search(query,context=self.context)
                self.assertFalse(any(h.source.page for h in stale.hits))
            finally:
                self.provider.pdf_hashes[doc_id] = previous
        asyncio.run(run())

if __name__ == '__main__':
    unittest.main()
