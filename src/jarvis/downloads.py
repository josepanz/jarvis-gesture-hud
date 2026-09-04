"""H-03: descarga atomica y verificada de artefactos grandes (modelos de
MediaPipe/llama.cpp), compartida por hand_tracker.py/pose_tracker.py/
llm_intent.py - los tres tenian la misma logica ("si no existe, descargar")
sin escritura atomica ni verificacion de tamaño, asi que una descarga
interrumpida (wifi, cierre de la app, disco lleno) dejaba un archivo parcial
con el nombre final que el arranque siguiente asumia completo.

No hay hash conocido y estable de estos artefactos (las URLs de
hand_landmarker/pose_landmarker apuntan a "latest" y pueden cambiar de
contenido; el modelo GGUF de Hugging Face no publica un checksum fijo en la
URL de descarga), asi que la unica verificacion posible es de tamaño contra
el `Content-Length` que informe el servidor - suficiente para distinguir
"parcial" de "completo", no una defensa contra manipulacion (fuera de
alcance: proyecto offline y personal, no hay un atacante realista en este
canal).
"""

import os
import urllib.request
from pathlib import Path


def download_atomically(url, dest_path):
    """Si `dest_path` ya existe, no descarga de nuevo (cache). Si no,
    descarga siempre a `<dest_path>.part` y hace `os.replace()` al terminar
    - el mismo patron atomico que `config_store.py` ya usa - para que un
    parcial nunca ocupe el nombre final. Verifica el tamaño contra
    `Content-Length` cuando el servidor lo informa; si no coincide, borra
    el `.part` y levanta `RuntimeError` con un mensaje accionable. Ante
    cualquier excepcion durante la descarga, borra el `.part` y relanza."""
    dest_path = Path(dest_path)
    if dest_path.exists():
        return dest_path
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    part_path = dest_path.with_name(dest_path.name + ".part")
    try:
        _, headers = urllib.request.urlretrieve(url, part_path)
        expected_size = headers.get("Content-Length") if headers is not None else None
        if expected_size is not None:
            actual_size = part_path.stat().st_size
            if actual_size != int(expected_size):
                raise RuntimeError(
                    f"descarga incompleta de {url}: se esperaban {expected_size} bytes, "
                    f"se recibieron {actual_size} - revisa la conexion e intenta de nuevo"
                )
    except BaseException:
        part_path.unlink(missing_ok=True)
        raise
    os.replace(part_path, dest_path)
    return dest_path
