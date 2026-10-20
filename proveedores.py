"""Consultas HTTP asíncronas opcionales. Nunca registra claves ni cuerpos de error."""

import asyncio
import os
from pathlib import Path
from urllib.parse import quote

import httpx
from dotenv import load_dotenv

from orquestador import log


async def llamar_proveedor(client, nombre, clave, modelo, prompt, semaforo):
    if not clave:
        log(f"ERROR {nombre}: falta configurar su API key en .env.")
        return False
    async with semaforo:
        log(f"INICIO {nombre} ({modelo})")
        try:
            if nombre == "OpenRouter":
                respuesta = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {clave}"},
                    json={"model": modelo, "messages": [{"role": "user", "content": prompt}], "max_tokens": 512},
                )
            else:
                respuesta = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{quote(modelo, safe='')}:generateContent",
                    headers={"x-goog-api-key": clave},
                    json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": 128}},
                )
            respuesta.raise_for_status()
            datos = respuesta.json()
            if nombre == "OpenRouter":
                texto = datos["choices"][0]["message"]["content"]
            else:
                texto = "".join(parte.get("text", "") for parte in datos["candidates"][0]["content"]["parts"])
            if not isinstance(texto, str) or not texto.strip():
                raise ValueError("Respuesta sin texto")
            # Evita imprimir una clave incluso ante una respuesta que la refleje.
            for variable in ("OPENROUTER_API_KEY", "GEMINI_API_KEY"):
                secreto = os.getenv(variable)
                if secreto:
                    texto = texto.replace(secreto, "[CLAVE OCULTA]")
            log(f"FIN {nombre}: {texto}")
            return True
        except asyncio.CancelledError:
            log(f"CANCELADA {nombre}")
            raise
        except httpx.HTTPStatusError as error:
            codigo = error.response.status_code
            detalle = {
                400: "revisá la clave, el modelo y la solicitud",
                401: "clave inválida o revocada",
                402: "saldo insuficiente",
                403: "acceso no autorizado",
                404: "modelo no disponible; revisá la variable del modelo en .env",
                429: "cuota agotada o demasiadas solicitudes",
            }.get(codigo, "el proveedor devolvió un error")
            log(f"ERROR {nombre}: HTTP {codigo}; {detalle}.")
        except httpx.TimeoutException:
            log(f"ERROR {nombre}: se agotó el tiempo de la conexión.")
        except httpx.RequestError:
            log(f"ERROR {nombre}: no se pudo conectar al servicio.")
        except (KeyError, IndexError, TypeError, ValueError):
            log(f"ERROR {nombre}: respuesta sin texto utilizable.")
        return False


async def consultar_reales(prompt, timeout=2):
    load_dotenv(Path(__file__).with_name(".env"), override=False)
    semaforo = asyncio.Semaphore(2)
    configuraciones = [
        ("OpenRouter", os.getenv("OPENROUTER_API_KEY"), os.getenv("OPENROUTER_MODEL", "openrouter/free")),
        ("Gemini", os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_MODEL", "gemini-3.8-flash")),
    ]
    log(f"Consultas reales: límite global de {timeout:g} segundos; máximo 2 simultáneas.")
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        try:
            async with asyncio.timeout(timeout):
                resultados = await asyncio.gather(*(
                    llamar_proveedor(client, nombre, clave, modelo, prompt, semaforo)
                    for nombre, clave, modelo in configuraciones
                ))
        except TimeoutError:
            log("ERROR: se superó el tiempo límite global. Las consultas pendientes se cancelaron.")
            return 1
    log(f"Consultas exitosas: {sum(resultados)}/{len(resultados)}")
    return 0 if all(resultados) else 1
