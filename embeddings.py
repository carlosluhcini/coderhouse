"""Un solo modelo local para ingesta y consultas, sin claves ni PyTorch."""
from functools import lru_cache
from fastembed import TextEmbedding
from fastembed.common.model_description import ModelSource, PoolingType
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer
from config import MODEL_NAME, MODEL_FILE, ROOT


@lru_cache(maxsize=1)
def tokenizer():
    path = hf_hub_download(MODEL_NAME, 'tokenizer.json', cache_dir=str(ROOT / '.cache/huggingface'))
    result = Tokenizer.from_file(path)
    result.no_truncation()
    result.no_padding()
    return result


def token_count(text):
    return len(tokenizer().encode(text, add_special_tokens=False).ids)


@lru_cache(maxsize=1)
def model():
    if MODEL_NAME not in {m['model'] for m in TextEmbedding.list_supported_models()}:
        TextEmbedding.add_custom_model(
            model=MODEL_NAME, pooling=PoolingType.MEAN, normalization=True,
            sources=ModelSource(hf=MODEL_NAME), dim=384, model_file=MODEL_FILE,
        )
    return TextEmbedding(model_name=MODEL_NAME, cache_dir=str(ROOT / '.cache/fastembed'), threads=2)


def embed_documents(texts):
    # E5 necesita estos prefijos incluso para textos en español.
    return [v.tolist() for v in model().embed(['passage: ' + t for t in texts], batch_size=8)]


def embed_query(text):
    if token_count('query: ' + text) > 510:
        raise ValueError('La consulta excede la longitud del modelo. Usá una pregunta más breve.')
    return next(model().embed(['query: ' + text])).tolist()
