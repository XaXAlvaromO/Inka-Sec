"""Los tres formatos de reto y cómo se califican. Siempre en el servidor.

- quick: un escenario y una decisión (el formato original).
- steps: escenario por pasos. Cada paso tiene una opción segura; cada opción trae su consecuencia.
- signals: "encuentra las señales". Un correo o mensaje dividido en fragmentos; la persona marca
  los sospechosos. Puntaje = señales encontradas menos marcas equivocadas, sobre el total de señales.

El trabajador nunca recibe qué opción es segura ni qué fragmento es sospechoso antes de responder.
"""
from __future__ import annotations

from app.models.challenge import Challenge

KINDS = ("quick", "steps", "signals")
KIND_LABEL = {"quick": "Reto rápido", "steps": "Escenario por pasos", "signals": "Encuentra las señales"}
FIELDS = ("from", "subject", "body", "link", "attachment")


class InvalidAnswer(Exception): ...


def kind_of(ch: Challenge) -> str:
    return ch.kind if ch.kind in KINDS else "quick"


def steps_of(ch: Challenge) -> list[dict]:
    return list((ch.content or {}).get("steps", []))


def segments_of(ch: Challenge) -> list[dict]:
    return list((ch.content or {}).get("segments", []))


def public_view(ch: Challenge) -> dict:
    """Lo que el trabajador ve antes de responder: sin respuestas."""
    kind = kind_of(ch)
    view = {"id": ch.id, "title": ch.title, "topic": ch.topic, "kind": kind, "kind_label": KIND_LABEL[kind],
            "description": ch.scenario, "options": [], "steps": [], "segments": []}
    if kind == "quick":
        view["options"] = list(ch.options)
    elif kind == "steps":
        view["steps"] = [{"prompt": s["prompt"], "options": [o["text"] for o in s["options"]]} for s in steps_of(ch)]
    else:
        view["segments"] = [{"field": s["field"], "text": s["text"]} for s in segments_of(ch)]
    return view


def check_step(ch: Challenge, step: int, choice: int) -> dict:
    """Consecuencia de una decisión en un paso (sin guardar nada): la persona la ve antes de seguir."""
    steps = steps_of(ch)
    if kind_of(ch) != "steps" or not 0 <= step < len(steps):
        raise InvalidAnswer("Paso fuera de rango")
    options = steps[step]["options"]
    if not 0 <= choice < len(options):
        raise InvalidAnswer("Opción fuera de rango")
    safe_index = next(i for i, o in enumerate(options) if o.get("safe"))
    return {"step": step, "choice": choice, "safe": bool(options[choice].get("safe")), "safe_index": safe_index,
            "feedback": options[choice].get("feedback", ""), "safe_feedback": options[safe_index].get("feedback", "")}


def grade(ch: Challenge, *, choice: int | None = None, choices: list[int] | None = None,
          marked: list[int] | None = None) -> dict:
    """Devuelve el detalle para el trabajador, más is_correct y score (0-100) para guardar."""
    kind = kind_of(ch)
    if kind == "quick":
        if choice is None or not 0 <= choice < len(ch.options):
            raise InvalidAnswer("Opción fuera de rango")
        correct = choice == ch.correct_index
        return {"kind": kind, "is_correct": correct, "score": 100 if correct else 0,
                "selected_index": choice, "correct_index": ch.correct_index, "feedback": ch.feedback}

    if kind == "steps":
        steps = steps_of(ch)
        if choices is None or len(choices) != len(steps):
            raise InvalidAnswer("Responde todos los pasos")
        detail = [check_step(ch, i, c) for i, c in enumerate(choices)]
        safe = sum(d["safe"] for d in detail)
        return {"kind": kind, "is_correct": safe == len(steps), "score": round(safe * 100 / len(steps)),
                "selected_index": safe, "safe_steps": safe, "total_steps": len(steps), "steps": detail,
                "feedback": ch.feedback}

    segments = segments_of(ch)
    picked = set(marked or [])
    if any(not 0 <= i < len(segments) for i in picked):
        raise InvalidAnswer("Fragmento fuera de rango")
    suspicious = {i for i, s in enumerate(segments) if s.get("suspicious")}
    found, false_marks = picked & suspicious, picked - suspicious
    score = round(max(0, len(found) - len(false_marks)) * 100 / len(suspicious)) if suspicious else 0
    detail = [{"index": i, "field": s["field"], "text": s["text"], "suspicious": bool(s.get("suspicious")),
               "marked": i in picked, "explanation": s.get("explanation", "")} for i, s in enumerate(segments)]
    return {"kind": kind, "is_correct": found == suspicious and not false_marks, "score": score,
            "selected_index": len(found), "found": len(found), "total_signals": len(suspicious),
            "false_marks": len(false_marks), "segments": detail, "feedback": ch.feedback}
