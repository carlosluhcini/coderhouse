"""Chunking por tokens y persistencia idempotente en ChromaDB."""
import argparse
import hashlib
import json
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import DATA_DIR, DB_DIR, CHUNK_SIZE, CHUNK_OVERLAP, COLLECTION, EMBEDDING_SPEC
from embeddings import embed_documents, token_count


def documents_fingerprint():
    files = sorted(p for p in DATA_DIR.rglob('*') if p.suffix.lower() in {'.txt', '.md'} and p.is_file())
    if not files:
        raise ValueError('No hay documentos .txt o .md en data/.')
    h = hashlib.sha256(f'{EMBEDDING_SPEC}|{CHUNK_SIZE}|{CHUNK_OVERLAP}|split-v1'.encode())
    for path in files:
        h.update(path.relative_to(DATA_DIR).as_posix().encode())
        h.update(path.read_bytes())
    return files, h.hexdigest()


def client():
    return chromadb.PersistentClient(path=str(DB_DIR))


def get_collection():
    db = client()
    if COLLECTION not in {c.name for c in db.list_collections()}:
        raise RuntimeError('Primero ejecutá: python ingesta.py')
    collection = db.get_collection(COLLECTION, embedding_function=None)
    if collection.metadata.get('embedding_spec') != EMBEDDING_SPEC:
        raise RuntimeError('El índice usa otro modelo. Ejecutá python ingesta.py --rebuild.')
    _, fingerprint = documents_fingerprint()
    if collection.metadata.get('fingerprint') != fingerprint:
        raise RuntimeError('Los documentos cambiaron. Ejecutá python ingesta.py --rebuild.')
    if not collection.metadata.get('ready') or not collection.count():
        raise RuntimeError('Índice incompleto. Ejecutá python ingesta.py --rebuild.')
    return collection


def ingest_documents(rebuild=False):
    files, fingerprint = documents_fingerprint()
    db = client()
    exists = COLLECTION in {c.name for c in db.list_collections()}
    if exists and not rebuild:
        collection = get_collection()
        print(f'Índice existente reutilizado: {collection.count()} fragmentos. No se recalculan embeddings.')
        return collection.count()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
        length_function=token_count, separators=['\n\n', '\n', '. ', ' ', ''],
    )
    chunks, metadatas, ids = [], [], []
    for path in files:
        source = path.relative_to(DATA_DIR).as_posix()
        for number, text in enumerate(splitter.split_text(path.read_text(encoding='utf-8')), start=1):
            # Reserva espacio para prefijo E5 y tokens especiales (límite: 512).
            if token_count('passage: ' + text) > 510:
                raise ValueError(f'Fragmento demasiado largo: {source}:{number}')
            chunk_id = f'{source}#fragmento-{number}'
            chunks.append(text)
            ids.append(chunk_id)
            metadatas.append({'source': source, 'chunk': number, 'tokens': token_count(text)})
    if not chunks:
        raise ValueError('Los documentos están vacíos.')
    vectors = embed_documents(chunks)
    # Solo reemplaza el índice anterior después de generar todos los embeddings.
    if exists:
        db.delete_collection(COLLECTION)
    collection = db.create_collection(
        COLLECTION, embedding_function=None, configuration={'hnsw': {'space': 'cosine'}},
        metadata={'embedding_spec': EMBEDDING_SPEC, 'fingerprint': fingerprint, 'ready': False},
    )
    collection.add(ids=ids, embeddings=vectors, documents=chunks, metadatas=metadatas)
    collection.modify(metadata={'embedding_spec': EMBEDDING_SPEC, 'fingerprint': fingerprint, 'ready': True})
    print(json.dumps({'archivos': len(files), 'fragmentos': collection.count(), 'tokens_por_fragmento': [m['tokens'] for m in metadatas]}, ensure_ascii=False))
    return collection.count()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild', action='store_true', help='Recrear la colección si cambiaron documentos o configuración')
    try:
        ingest_documents(parser.parse_args().rebuild)
    except (ValueError, RuntimeError) as error:
        parser.exit(1, str(error) + '\n')
