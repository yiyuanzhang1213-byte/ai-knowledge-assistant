"""Local evidence retrieval. Standard library only; no model weights or API keys."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import math
import re
import time
import unicodedata


@dataclass(frozen=True)
class Chunk:
    id: str
    source: str
    heading: str
    text: str


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float


STOP = {"怎么", "如何", "什么", "是否", "可以", "这个", "那个", "一下", "请问", "我们", "你们", "需要"}


def tokenize(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", text).lower()
    words = re.findall(r"[a-z0-9_]+", text)
    for segment in re.findall(r"[\u4e00-\u9fff]+", text):
        words.extend(segment[i:i + 2] for i in range(len(segment) - 1)
                     if segment[i:i + 2] not in STOP)
    return words


def split_document(source: str, text: str, max_chars: int = 420) -> list[Chunk]:
    if max_chars < 40:
        raise ValueError("max_chars must be at least 40")
    if len(text) > 200_000:
        raise ValueError("单个文档不能超过 200000 字符")
    chunks = []
    heading = "正文"
    parts = []

    def flush():
        if parts:
            content = "\n".join(parts).strip()
            if content:
                digest = hashlib.sha256(f"{source}\0{heading}\0{content}\0{len(chunks)}".encode()).hexdigest()[:12]
                chunks.append(Chunk(digest, source, heading, content))
            parts.clear()

    for line in text.splitlines():
        if line.startswith("#"):
            flush()
            heading = line.lstrip("# ").strip() or "正文"
        elif not line.strip():
            flush()
        else:
            for start in range(0, len(line), max_chars):
                piece = line[start:start + max_chars]
                if sum(map(len, parts)) + len(piece) > max_chars:
                    flush()
                parts.append(piece)
    flush()
    return chunks


class Retriever:
    """BM25 ranks lexical evidence; coverage gate is a heuristic, not confidence."""
    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self.tokens = [Counter(tokenize(c.heading + " " + c.text)) for c in chunks]
        self.df = Counter(t for tokens in self.tokens for t in tokens)
        self.avglen = sum(sum(t.values()) for t in self.tokens) / max(1, len(chunks))

    def search(self, query: str, k: int = 3, method: str = "bm25") -> list[Hit]:
        terms = set(tokenize(query))
        hits = []
        for chunk, counts in zip(self.chunks, self.tokens):
            score = 0.0
            length = sum(counts.values())
            for term in terms:
                frequency = counts[term]
                if not frequency:
                    continue
                if method == "overlap":
                    score += 1
                else:
                    idf = math.log(1 + (len(self.chunks) - self.df[term] + .5) / (self.df[term] + .5))
                    score += idf * frequency * 2.5 / (frequency + 1.5 * (.25 + .75 * length / max(1, self.avglen)))
            if score > 0:
                hits.append(Hit(chunk, round(score, 6)))
        return sorted(hits, key=lambda h: (-h.score, h.chunk.id))[:max(0, k)]


def coverage(query: str, hit: Hit) -> float:
    terms = set(tokenize(query))
    return len(terms & set(tokenize(hit.chunk.heading + " " + hit.chunk.text))) / max(1, len(terms))


def answer(query: str, retriever: Retriever, min_coverage: float = .22, k: int = 3) -> dict:
    started = time.perf_counter()
    if not query.strip():
        return {"status": "empty", "answer": "请输入问题。", "sources": [], "latency_ms": 0}
    private_request = any(term in query for term in ("身份证", "银行卡号", "密码", "手机号")) and any(
        verb in query for verb in ("查询", "告诉我", "给我", "泄露", "列出"))
    medical_request = any(term in query for term in ("诊断", "开药", "康复处方", "治疗方案"))
    if private_request or medical_request:
        return {"status": "refused", "answer": "此问题涉及个人敏感信息或医疗决策，请通过授权渠道或专业人员处理。",
                "sources": [], "latency_ms": round((time.perf_counter() - started) * 1000, 3)}
    hits = retriever.search(query, k=k)
    accepted = [h for h in hits if coverage(query, h) >= min_coverage]
    if not accepted:
        result = {"status": "refused", "answer": "当前知识库未找到充分依据，请联系工作人员确认。", "sources": []}
    else:
        result = {"status": "evidence", "answer": "\n\n".join(
            f"[{i}] {hit.chunk.text}" for i, hit in enumerate(accepted, 1)),
            "sources": [{"citation": i, **asdict(h.chunk), "score": h.score,
                         "coverage": round(coverage(query, h), 3)} for i, h in enumerate(accepted, 1)]}
    result["latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
    return result
