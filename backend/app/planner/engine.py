"""Consultation planner orchestrator — wires classifier, tree, and templates."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.planner.diagnostic_tree import DIAGNOSTIC_TREES, DiagnosticNode, next_diagnostic_nodes
from app.planner.intent_classifier import Intent, IntentClassification, classify_intent
from app.planner.response_templates import build_consultant_reply, format_diagnostic_question
from app.schemas.consultation import DiagnosticQuestion


@dataclass
class PlannerTurn:
    classification: IntentClassification
    diagnostic_nodes: list[DiagnosticNode]
    questions: list[str]
    diagnostic_questions: list[DiagnosticQuestion]
    reply: str
    ready: bool
    asked_keys: set[str] = field(default_factory=set)


class ConsultationPlanner:
    """Deterministic V2 consultation turn builder."""

    def plan_turn(
        self,
        message: str,
        slots: dict,
        asked: set[str],
        *,
        context_lines: list[str] | None = None,
    ) -> PlannerTurn:
        prior = slots.get("intent")
        classification = classify_intent(
            message, prior_intent=prior, slot_context=slots
        )
        slots["intent"] = classification.intent.value
        slots["intent_confidence"] = classification.confidence

        nodes = next_diagnostic_nodes(
            classification.intent,
            slots,
            asked,
            limit=2 if classification.needs_clarification else 2,
        )

        has_scale = slots.get("target_gpus") is not None or slots.get("compute_pflops") is not None
        has_scenario = slots.get("scenario") is not None or slots.get("workload_type") is not None
        required_pending = [
            n
            for n in DIAGNOSTIC_TREES.get(classification.intent, [])
            if n.required
            and n.question_key not in asked
            and slots.get(n.slot_key) is None
        ]

        ready = has_scale and has_scenario and len(required_pending) == 0

        diagnostic_questions = [
            DiagnosticQuestion(
                slot_key=n.slot_key,
                text=format_diagnostic_question(n),
                engineering_constraint=n.engineering_constraint,
                engineering_purpose=n.engineering_purpose,
            )
            for n in nodes
        ]
        questions = [dq.text for dq in diagnostic_questions]

        reply = build_consultant_reply(
            classification,
            nodes,
            context_lines=context_lines,
            ready=ready,
        )

        new_asked = set(asked)
        for node in nodes:
            new_asked.add(node.question_key)

        return PlannerTurn(
            classification=classification,
            diagnostic_nodes=nodes,
            questions=questions,
            diagnostic_questions=diagnostic_questions,
            reply=reply,
            ready=ready,
            asked_keys=new_asked,
        )
