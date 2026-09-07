"""TASK-076 (Fase 8, `openspec/changes/personalization-and-config-ui`,
design.md §5.3, spec.md #8.4): `HotkeyCommand` (atajo de teclado custom) y
`MacroCommand` (secuencia de pasos). Ambos son Commands ordinarios - fluyen
por el mismo `CommandBus`/`CommandHistory`/`FeedbackManager` que cualquier
otra accion, sin capa de ejecucion nueva. `pyautogui.hotkey()` ya soporta
cualquier combinacion de teclas - cero dependencias nuevas.
"""

import time

import pyautogui

from jarvis.actions.keyboard import PressKeyCommand, TypeTextCommand
from jarvis.core.commands import Command, CommandMetadata, CommandResult

_SAFETY_STRICTNESS = ("SAFE", "CONFIRM_REQUIRED", "HOLD_REQUIRED", "DESTRUCTIVE")


class HotkeyCommand(Command):
    def __init__(self, combo):
        self.combo = combo
        self._parts = [p.strip() for p in combo.split("+") if p.strip()]

    @property
    def metadata(self):
        return CommandMetadata(name=f"Hotkey({self.combo})", safety="SAFE")

    def can_execute(self):
        return bool(self._parts)

    def execute(self):
        try:
            pyautogui.hotkey(*self._parts)
            return CommandResult.ok()
        except Exception as exc:
            return CommandResult.failed(error=str(exc), message=f"Hotkey({self.combo}) failed")


class WaitStep:
    """NO es un Command (no ejecuta ninguna accion del SO, `MacroCommand`
    la reconoce por tipo) - solo pausa entre 2 pasos reales de una macro.
    `time.sleep()` bloquea el hilo que corre `CommandBus.dispatch()`,
    aceptable porque una macro es una secuencia corta y deliberada disparada
    por el usuario, no un bucle continuo."""

    def __init__(self, ms):
        self.ms = ms


def build_macro_step(step_data):
    """Traduce UN paso persistido (`{"kind": ..., "value": ...}`, spec.md
    #8.4.2) al objeto real que `MacroCommand` ejecuta - la UNICA traduccion
    entre el JSON de disco y los pasos en memoria (`apply.md` §14: no una
    segunda representacion competidora)."""
    kind = step_data.get("kind")
    value = step_data.get("value")
    if kind == "press-key":
        return PressKeyCommand(value)
    if kind == "type-text":
        return TypeTextCommand(value)
    if kind == "wait-ms":
        return WaitStep(value)
    raise ValueError(f"unknown macro step kind: {kind!r}")


def build_macro_steps(steps_data):
    return [build_macro_step(step) for step in steps_data]


class MacroCommand(Command):
    def __init__(self, name, steps):
        self.name = name
        self.steps = steps

    @property
    def metadata(self):
        # safety = la MAS ESTRICTA entre los pasos (spec.md #8.4.2). Un
        # WaitStep no es un Command y no tiene safety propia - no participa.
        command_steps = [s for s in self.steps if isinstance(s, Command)]
        if not command_steps:
            safety = "SAFE"
        else:
            safety = max(
                (s.metadata.safety for s in command_steps),
                key=_SAFETY_STRICTNESS.index,
            )
        return CommandMetadata(name=f"Macro({self.name})", safety=safety)

    def can_execute(self):
        return bool(self.steps)

    def execute(self):
        try:
            for step in self.steps:
                if isinstance(step, WaitStep):
                    time.sleep(step.ms / 1000.0)
                    continue
                if not step.can_execute():
                    return CommandResult.rejected(message=f"{step.metadata.name} no se puede ejecutar")
                result = step.execute()
                if not result.success:
                    return CommandResult.failed(
                        error=result.error or "paso de macro fallo",
                        message=f"Macro({self.name}) se detuvo en {step.metadata.name}",
                    )
            return CommandResult.ok()
        except Exception as exc:
            return CommandResult.failed(error=str(exc), message=f"Macro({self.name}) failed")
