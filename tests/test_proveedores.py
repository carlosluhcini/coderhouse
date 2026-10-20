import asyncio
import contextlib
import io
import unittest

import httpx

from proveedores import llamar_proveedor


class ProveedoresTests(unittest.IsolatedAsyncioTestCase):
    async def test_ambos_formatos_y_autenticacion(self):
        def responder(request):
            if request.url.host == "openrouter.ai":
                self.assertEqual(request.headers["Authorization"], "Bearer clave-ficticia")
                return httpx.Response(200, json={"choices": [{"message": {"content": "Hola"}}]})
            self.assertEqual(request.headers["x-goog-api-key"], "clave-ficticia")
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "Hola"}]}}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(responder)) as client:
            with contextlib.redirect_stdout(io.StringIO()):
                for nombre in ("OpenRouter", "Gemini"):
                    self.assertTrue(await llamar_proveedor(client, nombre, "clave-ficticia", "modelo", "Hola", asyncio.Semaphore(2)))

    async def test_error_http_no_imprime_cuerpo_ni_clave(self):
        def responder(request):
            return httpx.Response(401, json={"error": "clave-ficticia"})

        salida = io.StringIO()
        async with httpx.AsyncClient(transport=httpx.MockTransport(responder)) as client:
            with contextlib.redirect_stdout(salida):
                self.assertFalse(await llamar_proveedor(client, "OpenRouter", "clave-ficticia", "modelo", "Hola", asyncio.Semaphore(2)))
        self.assertIn("HTTP 401", salida.getvalue())
        self.assertNotIn("clave-ficticia", salida.getvalue())

    async def test_timeout_cancela_y_libera_semaforo(self):
        cancelada = asyncio.Event()

        async def responder(request):
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                cancelada.set()
                raise

        semaforo = asyncio.Semaphore(1)
        async with httpx.AsyncClient(transport=httpx.MockTransport(responder)) as client:
            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(TimeoutError):
                    async with asyncio.timeout(0.02):
                        await llamar_proveedor(client, "Gemini", "clave-ficticia", "modelo", "Hola", semaforo)
        self.assertTrue(cancelada.is_set())
        self.assertFalse(semaforo.locked())

    async def test_clave_ausente_no_hace_solicitud(self):
        def responder(request):
            self.fail("No debe enviar una consulta sin clave")

        async with httpx.AsyncClient(transport=httpx.MockTransport(responder)) as client:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertFalse(await llamar_proveedor(client, "Gemini", "", "modelo", "Hola", asyncio.Semaphore(2)))


if __name__ == "__main__":
    unittest.main()
