import tempfile
import subprocess
import sys
import unittest
from pathlib import Path
import ingesta


class PersistenciaTests(unittest.TestCase):
    def test_reutiliza_indice_y_detecta_documentos_modificados(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / 'data'
            data.mkdir()
            file = data / 'manual.md'
            file.write_text('Texto de prueba para indexar.', encoding='utf-8')
            # Un proceso separado libera los archivos de Chroma en Windows
            # antes de que TemporaryDirectory limpie la carpeta de prueba.
            code = '''
import sys
from pathlib import Path
from unittest.mock import patch
import ingesta
root = Path(sys.argv[1])
with patch.object(ingesta, 'DATA_DIR', root / 'data'), patch.object(ingesta, 'DB_DIR', root / 'db'), patch.object(ingesta, 'token_count', side_effect=lambda t: len(t.split())), patch.object(ingesta, 'embed_documents', return_value=[[1.0, 0.0, 0.0]]) as embed:
    assert ingesta.ingest_documents() == 1
    assert ingesta.ingest_documents() == 1
    assert embed.call_count == 1
    (root / 'data/manual.md').write_text('Documento modificado.', encoding='utf-8')
    try:
        ingesta.get_collection()
    except RuntimeError:
        pass
    else:
        raise AssertionError('El indice modificado debe rechazarse')
'''
            result = subprocess.run([sys.executable, '-c', code, str(root)], capture_output=True, text=True, cwd=Path(ingesta.__file__).parent)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
