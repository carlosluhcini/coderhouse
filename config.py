from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')
DATA_DIR = ROOT / 'data'
DB_DIR = ROOT / 'vectorstore'
MODEL_NAME = 'intfloat/multilingual-e5-small'
MODEL_FILE = 'onnx/model.onnx'
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 4
COLLECTION = 'manual_microservicios'
EMBEDDING_SPEC = f'{MODEL_NAME}|{MODEL_FILE}|mean|normalized|e5-prefix-v1'
