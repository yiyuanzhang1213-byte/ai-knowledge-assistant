"""Frozen self-authored smoke benchmark, not a production quality estimate."""
import json
from pathlib import Path
from portfolio.core import Retriever, answer, split_document


def evaluate():
    folder = Path(__file__).parent
    data = json.loads((folder / "data/eval.json").read_text(encoding="utf-8"))
    retriever = Retriever(split_document("fitness_faq.md", (folder / "data/fitness_faq.md").read_text(encoding="utf-8")))
    report = {"dataset": "self-authored synthetic 32 questions; dev=16,test=16",
              "scope": "lexical retrieval and refusal only; no live LLM calls",
              "threshold": .22, "splits": {}}
    for split in ("dev", "test"):
        cases = [c for c in data if c["split"] == split]
        rows = []
        for c in cases:
            hits = retriever.search(c["question"])
            baseline = retriever.search(c["question"], method="overlap")
            result = answer(c["question"], retriever)
            rows.append({**c, "bm25_top1": hits[0].chunk.heading if hits else None,
                         "overlap_top1": baseline[0].chunk.heading if baseline else None,
                         "top3": [h.chunk.heading for h in hits],
                         "status": result["status"], "latency_ms": result["latency_ms"]})
        positive = [r for r in rows if r["heading"] is not None]
        negative = [r for r in rows if r["heading"] is None]
        metrics = {"answerable_n": len(positive), "unanswerable_n": len(negative),
                   "bm25_hit_at_1": sum(r["heading"] == r["bm25_top1"] for r in positive) / len(positive),
                   "overlap_hit_at_1": sum(r["heading"] == r["overlap_top1"] for r in positive) / len(positive),
                   "bm25_hit_at_3": sum(r["heading"] in r["top3"] for r in positive) / len(positive),
                   "negative_refusal_rate": sum(r["status"] == "refused" for r in negative) / len(negative),
                   "positive_false_refusal_rate": sum(r["status"] == "refused" for r in positive) / len(positive)}
        report["splits"][split] = {"metrics": metrics, "cases": rows}
    target = folder / "reports/evaluation.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for split, result in report["splits"].items():
        print(split, json.dumps(result["metrics"]))


if __name__ == "__main__":
    evaluate()
