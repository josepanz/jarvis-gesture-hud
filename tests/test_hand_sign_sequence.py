"""Y-07 (`openspec/changes/hand-sign-fidelity/WORKPLAN.md` §5): tests de
SequenceTracker - historial + timeout + match de secuencia -> accion.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis import config  # noqa: E402
from jarvis.hand_sign_sequence import (  # noqa: E402
    JUTSU_BUNSHIN,
    JUTSU_KATON,
    JUTSU_KAWARIMI,
    KNOWN_SEQUENCES,
    SequenceTracker,
)


class SequenceTrackerTests(unittest.TestCase):
    def setUp(self):
        self.tracker = SequenceTracker()
        self.t = 0.0

    def _feed(self, sign_event):
        result = self.tracker.record(sign_event, now=self.t)
        self.t += 0.5
        return result

    def test_completing_a_known_sequence_returns_its_event(self):
        signs = KNOWN_SEQUENCES[JUTSU_BUNSHIN]
        results = [self._feed(s) for s in signs]
        self.assertEqual(results, [None, None, JUTSU_BUNSHIN])

    def test_completing_the_fireball_sequence_returns_its_event(self):
        signs = KNOWN_SEQUENCES[JUTSU_KATON]
        results = [self._feed(s) for s in signs]
        self.assertEqual(results[-1], JUTSU_KATON)
        self.assertEqual(results[:-1], [None] * (len(signs) - 1))

    def test_an_incomplete_sequence_never_fires(self):
        signs = KNOWN_SEQUENCES[JUTSU_KAWARIMI]
        results = [self._feed(s) for s in signs[:-1]]  # falta el ultimo sello
        self.assertTrue(all(r is None for r in results))

    def test_a_wrong_sign_in_the_middle_breaks_the_sequence(self):
        signs = KNOWN_SEQUENCES[JUTSU_BUNSHIN]
        self._feed(signs[0])
        self._feed("NARUTO_TATSU")  # sello equivocado, no sigue la secuencia
        result = self._feed(signs[2])
        self.assertIsNone(result)  # el historial ahora es [..., TATSU, TORA], no matchea

    def test_matching_consumes_the_history_so_it_does_not_immediately_rematch(self):
        signs = KNOWN_SEQUENCES[JUTSU_BUNSHIN]
        for s in signs:
            self._feed(s)
        # Sin repetir toda la secuencia, no puede volver a completarse de
        # inmediato (el historial se limpio tras el primer match).
        result = self._feed(signs[-1])
        self.assertIsNone(result)

    def test_timeout_clears_the_history_mid_sequence(self):
        signs = KNOWN_SEQUENCES[JUTSU_BUNSHIN]
        self._feed(signs[0])
        self._feed(signs[1])
        self.t += config.NARUTO_SEQUENCE_INTERVAL_SECONDS + 0.1  # pasa el timeout sin ningun sello
        result = self._feed(signs[2])  # el historial se limpio - esto es un historial nuevo de 1 sello
        self.assertIsNone(result)

    def test_no_timeout_within_the_interval_keeps_progress(self):
        signs = KNOWN_SEQUENCES[JUTSU_BUNSHIN]
        self.tracker.record(signs[0], now=0.0)
        gap = config.NARUTO_SEQUENCE_INTERVAL_SECONDS - 0.1  # dentro del intervalo
        self.tracker.record(signs[1], now=gap)
        result = self.tracker.record(signs[2], now=2 * gap)
        self.assertEqual(result, JUTSU_BUNSHIN)

    def test_reset_clears_history_and_timeout_state(self):
        signs = KNOWN_SEQUENCES[JUTSU_BUNSHIN]
        self._feed(signs[0])
        self._feed(signs[1])
        self.tracker.reset()
        result = self._feed(signs[2])
        self.assertIsNone(result)  # el progreso de antes del reset no cuenta

    def test_longer_sequences_are_preferred_over_a_shared_suffix(self):
        # Escenario sintetico (KNOWN_SEQUENCES real no comparte sufijos hoy):
        # "AB" y "XAB" - completar XAB no debe devolver la mas corta "AB".
        fake_sequences = {"SHORT": ("A", "B"), "LONG": ("X", "A", "B")}
        with patch(
            "jarvis.hand_sign_sequence._SEQUENCES_BY_LENGTH_DESC",
            sorted(fake_sequences.items(), key=lambda item: len(item[1]), reverse=True),
        ):
            tracker = SequenceTracker()
            tracker.record("X", now=0.0)
            tracker.record("A", now=0.1)
            result = tracker.record("B", now=0.2)
        self.assertEqual(result, "LONG")


if __name__ == "__main__":
    unittest.main()
