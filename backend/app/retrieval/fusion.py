"""
多路召回融合：RRF (Reciprocal Rank Fusion)。

为什么用 RRF？
- 向量召回的分数是余弦相似度（0~1）
- BM25 召回的分数是无界浮点数（可能 1.2，也可能 8.7）
- 两把尺子不一样，不能直接加
- RRF 只看排名：第 1 名得 1/(k+1)，第 2 名得 1/(k+2)…
- 同一个 chunk 在两路都排前面，总分就高

k=60 是业界默认值，一般不用动。
"""


def rrf_fuse(
    *ranked_lists: list[tuple[str, float]],
    k: int = 60,
    top_n: int = 5,
) -> list[tuple[str, float]]:
    """
    把多路召回结果融合成一路。

    参数:
        ranked_lists: 每路是 [(chunk_id, score), ...]，按相关度从高到低排
        k: RRF 常数，默认 60
        top_n: 融合后取前多少个

    返回:
        [(chunk_id, rrf_score), ...]，按融合分数从高到低
    """
    fused: dict[str, float] = {}

    for ranked in ranked_lists:
        for rank, (chunk_id, _) in enumerate(ranked):
            # rank 从 0 开始，第 0 名就是 1/(k+1)
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)

    sorted_items = sorted(fused.items(), key=lambda x: -x[1])
    return [(cid, score) for cid, score in sorted_items[:top_n]]
