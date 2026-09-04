"""TASK-074 (Fase 8, `openspec/changes/personalization-and-config-ui`,
design.md §5.2, spec.md #8.6): persistencia generica de bindings en disco -
un JSON versionado por fuera del repo/directorio de instalacion. Este
modulo solo sabe leer/escribir un dict de forma segura; el SIGNIFICADO del
contenido (perfiles, gesture_bindings, custom_shortcuts, macros) lo define
`jarvis.core.profiles` (TASK-075) - separacion deliberada entre "como se
guarda" y "que se guarda".
"""

import json
import os
import time
from pathlib import Path

CONFIG_DIR = Path.home() / ".jarvis-gesture-hud"
CONFIG_FILE = CONFIG_DIR / "bindings.json"


def load_bindings(path=CONFIG_FILE):
    """{} (los defaults de codigo aplican) si el archivo no existe o esta
    corrupto - nunca lanza. Un archivo corrupto se preserva APARTE
    (renombrado con un sufijo de timestamp), nunca se sobreescribe
    silenciosamente en la siguiente escritura (spec.md #8.6: "never
    silently clobber a corrupt file")."""
    path = Path(path)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        _preserve_corrupt_file(path)
        return {}
    return data if isinstance(data, dict) else {}


def _preserve_corrupt_file(path):
    backup = path.with_name(f"{path.name}.bak-{int(time.time())}")
    try:
        path.rename(backup)
    except OSError:
        pass  # si ni el rename anda, seguimos con defaults - nunca bloquea el arranque


def save_bindings(data, path=CONFIG_FILE):
    """Escritura atomica: escribe a un archivo temporal en el MISMO
    directorio y luego `os.replace()` - un crash a mitad de escritura no
    puede corromper el archivo bueno anterior (rename es atomico dentro del
    mismo filesystem)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)
