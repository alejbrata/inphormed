# app/indexers/lexical_indexer.py
from __future__ import annotations

from typing import List
from datetime import datetime, timezone
import os, shutil

from whoosh import index
from whoosh.fields import Schema, TEXT, ID, NUMERIC, DATETIME
from whoosh.qparser import MultifieldParser
from whoosh.scoring import BM25F

from app.schemas import Chunk, SearchHit
from app.audit.auditor import Auditor


class LexicalIndexer:
    """
    Indexador léxico (Whoosh) con trazabilidad:
    - Guarda doc_hash y chunk_hash.
    - 'ingested_at' como DATETIME.
    """

    def __init__(self, index_dir: str):
        self.index_dir = index_dir
        if not os.path.exists(self.index_dir):
            os.makedirs(self.index_dir, exist_ok=True)
            self._create_index()
        elif not index.exists_in(self.index_dir):
            self._create_index()
        self.ix = index.open_dir(self.index_dir)

    def _create_index(self):
        schema = Schema(
            chunk_id=ID(stored=True, unique=True),
            doc_id=ID(stored=True),
            source=ID(stored=True),
            title=TEXT(stored=True),
            url=ID(stored=True),
            span_start=NUMERIC(stored=True),
            span_end=NUMERIC(stored=True),
            text=TEXT(stored=True),
            doc_hash=ID(stored=True),
            chunk_hash=ID(stored=True),
            ingested_at=DATETIME(stored=True),
        )
        index.create_in(self.index_dir, schema)

    def clear(self):
        if os.path.exists(self.index_dir):
            shutil.rmtree(self.index_dir)
        os.makedirs(self.index_dir, exist_ok=True)
        self._create_index()
        self.ix = index.open_dir(self.index_dir)

    def index(self, chunks: List[Chunk]) -> int:
        if not chunks:
            return 0
        writer = self.ix.writer(limitmb=512)
        now_dt = datetime.now(timezone.utc)

        n = 0
        for c in chunks:
            doc_hash = c.doc_hash or ""
            chunk_hash = Auditor.compute_chunk_hash(doc_hash, c.span_start, c.span_end) if doc_hash else None

            writer.update_document(
                chunk_id=c.id,
                doc_id=c.doc_id,
                source=c.source,
                title=c.title or "",
                url=c.url or "",
                span_start=c.span_start,
                span_end=c.span_end,
                text=c.text,
                doc_hash=doc_hash,
                chunk_hash=chunk_hash or "",
                ingested_at=now_dt,
            )
            n += 1

        writer.commit()
        return n

    def search(self, query: str, top_k: int = 20) -> List[SearchHit]:
        with self.ix.searcher(weighting=BM25F()) as searcher:
            parser = MultifieldParser(["text", "title"], schema=self.ix.schema)
            q = parser.parse(query)
            results = searcher.search(q, limit=top_k)
            hits: List[SearchHit] = []
            for r in results:
                hits.append(SearchHit(
                    chunk=Chunk(
                        id=r["chunk_id"],
                        doc_id=r["doc_id"],
                        source=r["source"],
                        title=r.get("title"),
                        url=r.get("url"),
                        span_start=r["span_start"],
                        span_end=r["span_end"],
                        text=r["text"],
                        doc_hash=r.get("doc_hash"),
                    ),
                    score=float(r.score),
                ))
            return hits
