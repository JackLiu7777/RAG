"""
只下载 bge-reranker-base 需要的文件（跳过 onnx 和 pytorch_model.bin）。
"""
from modelscope import snapshot_download

model_dir = snapshot_download(
    "BAAI/bge-reranker-base",
    cache_dir="C:/Users/26819/Desktop/models",
    allow_patterns=[
        "config.json",
        "model.safetensors",
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "sentencepiece.bpe.model",
    ],
)
print(f"\n模型已下载到: {model_dir}")
