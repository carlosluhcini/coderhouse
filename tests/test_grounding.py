import unittest
from rag import RespuestaRAG, Referencia, validate_grounding


class GroundingTests(unittest.TestCase):
    def setUp(self):
        self.docs = [{'id': 'manual.md#fragmento-1', 'documento': 'manual.md', 'texto': 'La orden es nc rollback --revision estable.'}]

    def test_referencia_valida(self):
        answer = RespuestaRAG(texto='Usar nc rollback --revision estable.', referencias=[Referencia(documento='manual.md', fragmento='manual.md#fragmento-1', cita='nc rollback --revision estable')])
        self.assertEqual(validate_grounding(answer, self.docs), answer)

    def test_cita_inventada_se_rechaza(self):
        answer = RespuestaRAG(texto='Respuesta falsa', referencias=[Referencia(documento='manual.md', fragmento='manual.md#fragmento-1', cita='Esto no está documentado')])
        with self.assertRaises(ValueError):
            validate_grounding(answer, self.docs)

    def test_respuesta_sin_fuentes_se_rechaza(self):
        with self.assertRaises(ValueError):
            validate_grounding(RespuestaRAG(texto='Dato externo', referencias=[]), self.docs)

    def test_abstencion_sin_referencias(self):
        answer = validate_grounding(RespuestaRAG(texto='No lo sé.', referencias=[]), self.docs)
        self.assertEqual(answer.texto, 'No lo sé')
        self.assertEqual(answer.referencias, [])


if __name__ == '__main__':
    unittest.main()
