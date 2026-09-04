"""TASK-067 (Fase 6, `openspec/changes/personalization-and-config-ui/design.md`
§6.2): primer primitivo TEMPORAL/multi-frame de este codebase - los gestos
existentes son de estado en un solo frame (curvatura de dedos) o de hold
simple (sostener N segundos). `ImpulseDetector` reconoce un patron distinto:
una distancia que BAJA de un umbral de contacto y despues SUBE por encima de
un umbral de release, dentro de una ventana de tiempo corta - un "snap" o
"aplauso" (acercamiento rapido + separacion rapida), no un pinch/hold
sostenido (que ya es dueño de los gestos PINCH_*/RIGHT_CLICK existentes).

Reutilizado tal cual por Sukuna (Fase 6, `gestures.py`) y por Clap (Fase 7) -
`design.md` pide explicitamente NO reimplementarlo por gesto."""


class ImpulseDetector:
    """`update(distance, now)` devuelve True exactamente una vez por impulso
    completo (baja de `contact_threshold` y luego sube de `release_threshold`
    dentro de `max_window_seconds` desde el primer contacto).

    Maquina de 3 estados en vez de solo un timestamp: una distancia que se
    queda por debajo de `contact_threshold` mas alla de `max_window_seconds`
    (un pinch/hold sostenido, no un snap) pasa a "expired" - deja de poder
    disparar, y SOLO vuelve a "idle" (elegible para un impulso nuevo) cuando
    la distancia finalmente sube por encima de `release_threshold`. Sin este
    tercer estado, un hold sostenido que eventualmente se suelta dispararia
    igual (bug real detectado al razonar el caso, no solo un detalle
    academico - ver test_temporal_gesture.py)."""

    def __init__(self, contact_threshold, release_threshold, max_window_seconds):
        self.contact_threshold = contact_threshold
        self.release_threshold = release_threshold
        self.max_window_seconds = max_window_seconds
        self._state = "idle"  # idle -> armed -> (dispara, vuelve a idle) | armed -> expired -> idle (sin disparar)
        self._contact_time = None

    def update(self, distance, now):
        if self._state == "armed" and now - self._contact_time > self.max_window_seconds:
            self._state = "expired"

        if self._state == "idle":
            if distance < self.contact_threshold:
                self._state = "armed"
                self._contact_time = now
            return False

        if self._state == "armed":
            if distance > self.release_threshold:
                self._state = "idle"
                self._contact_time = None
                return True
            return False

        # expired: esperando que la distancia suba de release_threshold para
        # recien ahi volver a estar elegible - no dispara nunca desde aca.
        if distance > self.release_threshold:
            self._state = "idle"
            self._contact_time = None
        return False
