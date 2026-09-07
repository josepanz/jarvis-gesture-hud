"""SequenceTracker (Y-07, `openspec/changes/hand-sign-fidelity/WORKPLAN.md`
§5): una secuencia de sellos dispara una accion propia.

Copia la IDEA del proyecto original (NARUTO-HandSignDetection,
`setting/jutsu.csv`): un historial de sellos CONFIRMADOS que se limpia solo
si pasan `config.NARUTO_SEQUENCE_INTERVAL_SECONDS` sin ningun sello nuevo, y
un match exacto contra una tabla fija de secuencias. No copia el codigo ni
el dataset completo (14 jutsu, uno de ellos de 44 sellos, a todas luces un
chiste del autor original, no una secuencia pensada para hacerse a mano) -
3 secuencias representativas, decodificadas de `jutsu.csv` via el kanji de
cada sello (mismo mapeo que `setting/labels.csv`), elegidas por ser cortas y
faciles de probar/verificar en camara real.

Un match consume el historial entero (se limpia) para no competir con la
proxima secuencia. Se chequean las secuencias mas largas primero, para que
una secuencia larga no quede eclipsada por una corta que comparte sufijo -
ninguna de las 3 de abajo comparte sufijo hoy, pero el orden deja el
matching a prueba de futuros agregados a `KNOWN_SEQUENCES`.
"""

import time

from jarvis import config

# jutsu.csv (Fire Style, "Fireball Jutsu"): 巳,寅,申,亥,午,寅.
JUTSU_KATON = "JUTSU_KATON"
# jutsu.csv ("Clone Jutsu"): 未,巳,寅.
JUTSU_BUNSHIN = "JUTSU_BUNSHIN"
# jutsu.csv ("Substitution Jutsu"): 未,亥,丑,戌,巳.
JUTSU_KAWARIMI = "JUTSU_KAWARIMI"

KNOWN_SEQUENCES = {
    JUTSU_BUNSHIN: ("NARUTO_HITSUJI", "NARUTO_MI", "NARUTO_TORA"),
    JUTSU_KAWARIMI: ("NARUTO_HITSUJI", "NARUTO_I", "NARUTO_USHI", "NARUTO_INU", "NARUTO_MI"),
    JUTSU_KATON: ("NARUTO_MI", "NARUTO_TORA", "NARUTO_SARU", "NARUTO_I", "NARUTO_UMA", "NARUTO_TORA"),
}

_SEQUENCES_BY_LENGTH_DESC = sorted(KNOWN_SEQUENCES.items(), key=lambda item: len(item[1]), reverse=True)


class SequenceTracker:
    def __init__(self, sign_interval_seconds=None):
        self._sign_interval_seconds = (
            sign_interval_seconds if sign_interval_seconds is not None else config.NARUTO_SEQUENCE_INTERVAL_SECONDS
        )
        self._history = []
        self._last_seen = None

    def record(self, sign_event, now=None):
        """Registra un sello CONFIRMADO (un evento NARUTO_* ya disparado por
        `HandSignTracker`, no una deteccion cruda de cuadro a cuadro) y
        devuelve el evento de secuencia si se completo una, o None. Se llama
        una vez por evento de sello, no una vez por cuadro."""
        if now is None:
            now = time.time()

        if self._last_seen is not None and now - self._last_seen > self._sign_interval_seconds:
            self._history = []
        self._last_seen = now
        self._history.append(sign_event)

        for sequence_event, signs in _SEQUENCES_BY_LENGTH_DESC:
            n = len(signs)
            if n <= len(self._history) and tuple(self._history[-n:]) == signs:
                self._history = []
                return sequence_event
        return None

    def reset(self):
        self._history = []
        self._last_seen = None
