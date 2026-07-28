"""知识库检索测试 CLI。

用法:
  python -m sellpilot.cli.retrieve_knowledge "耳机电池不耐用怎么办"
  python -m sellpilot.cli.retrieve_knowledge "how to return a product" --top-k 3 --category faq
"""

import argparse
import json

from sellpilot.services.embedding import EmbeddingService
from sellpilot.services.vector_store import ChromaVectorStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test RAG knowledge retrieval"
    )
    parser.add_argument(
        "query", type=str, help="Search query (Chinese or English)"
    )
    parser.add_argument(
        "--top-k", type=int, default=5, help="Number of results (default: 5)"
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        choices=["product", "review", "faq"],
        help="Filter by category",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print(f"Query: {args.query}")
    print(f"Top-K: {args.top_k}")
    if args.category:
        print(f"Category filter: {args.category}")

    # 1. Embedding
    print("\n[1/3] Generating query embedding ...")
    embedding_service = EmbeddingService()
    query_vec = embedding_service.encode_single(args.query)
    print(f"  Model: {embedding_service._model_name} (dim={embedding_service.dim})")

    # 2. Search ChromaDB
    print("[2/3] Searching ChromaDB ...")
    vector_store = ChromaVectorStore()
    where = {"category": args.category} if args.category else None
    results = vector_store.search(query_vec, top_k=args.top_k, where=where)

    print(f"  Collection: {vector_store._collection_name} ({vector_store.count} vectors)")

    # 3. Display
    print(f"\n[3/3] Results ({len(results)} found):\n")
    for i, r in enumerate(results):
        score_pct = round(r["score"] * 100, 1)
        print(f"── #{i + 1} 匹配度 {score_pct}% ──────────────────────")
        print(f"  ID: {r['chroma_id']}")
        if r.get("metadata"):
            meta = r["metadata"]
            print(f"  Category: {meta.get('category', 'N/A')}  |  Chunk: {meta.get('chunk_index', 'N/A')}")
        doc = r.get("document", "")
        # 截断过长文本
        if len(doc) > 400:
            doc = doc[:400] + "..."
        print(f"  {doc}")
        print()


if __name__ == "__main__":
    main()
