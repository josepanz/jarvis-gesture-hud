"""Y-03 (`openspec/changes/hand-sign-fidelity/WORKPLAN.md`): cablear
HandSignTracker en el loop de camara de run(). Con el tracker mockeado (no
hace falta inferencia real para probar el gate y el dispatch): un evento de
sello llega a `_dispatch_bound_event` por el mismo camino que el resto de los
gestos; con una sola mano en cuadro el tracker no se invoca (gate de costo).
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.hand_tracker import Hand  # noqa: E402
from tests.test_gesture_engine_regression import ne_hand  # noqa: E402
from tests.test_naruto_seal_dispatch import _AppTestCase  # noqa: E402

_FRAME = np.zeros((480, 640, 3), dtype=np.uint8)


class HandSignDispatchTests(_AppTestCase):
    def setUp(self):
        super().setUp()
        self.app.hand_sign_tracker = MagicMock()
        self.app.cap.read.return_value = (True, _FRAME)
        # Una sola iteracion del loop de run(): isOpened() True una vez, False
        # despues (mismo patron que test_main_shutdown.py).
        self.app.cap.isOpened.side_effect = [True, False]

    def _run_one_frame_with_hands(self, hands):
        self.app.tracker.process = MagicMock(return_value=hands)
        self.app.run()

    def test_two_hands_in_frame_invokes_the_tracker_and_dispatches_its_event(self):
        self.app.hand_sign_tracker.process.return_value = ["NARUTO_NE"]  # default: ZOOM_OUT

        self._run_one_frame_with_hands([Hand(ne_hand(), "Left"), Hand(ne_hand(), "Right")])

        self.app.hand_sign_tracker.process.assert_called_once()
        self.mock_mouse_pyautogui.scroll.assert_called()  # ZOOM_OUT via Ctrl+Scroll

    def test_one_hand_in_frame_never_invokes_the_tracker(self):
        self._run_one_frame_with_hands([Hand(ne_hand(), "Right")])

        self.app.hand_sign_tracker.process.assert_not_called()

    def test_no_hands_in_frame_never_invokes_the_tracker(self):
        self._run_one_frame_with_hands([])

        self.app.hand_sign_tracker.process.assert_not_called()


if __name__ == "__main__":
    unittest.main()
