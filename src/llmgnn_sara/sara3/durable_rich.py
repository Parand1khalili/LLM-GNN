"""Crash-durable Rich Prompt V2 *offline fixture* transport.

Reuse the audited SQLite state machine. This is deliberately NOT a provider
adapter: no credentials, paid calls or model usage can enter this transport.
"""
from .durable_fixture import DurableOfflineFixtureVerifier
from .evidence import EvidenceError
from .experiment import digest, request_identity
from .rich_evidence import rich_verifier_input_v2, validate_rich_result, target_source

EXPERIMENT_VERSION = "sara.rich_v2.synthetic_runner.v1"


class DurableRichOfflineVerifier(DurableOfflineFixtureVerifier):
    """One bounded, immutable synthetic rich-v2 request contract per journal."""

    def __init__(self, verifier, context, audit, *, maximum_calls):
        if (type(context) is not dict or context.get("experiment_version") != EXPERIMENT_VERSION):
            raise ValueError("Versioned rich-v2 experiment context is required")
        super().__init__(verifier, context, audit, maximum_calls=maximum_calls)

    def _validate(self, raw, text):
        return validate_rich_result(raw, (target_source(text),))

    def blind(self, request):
        payload = rich_verifier_input_v2(request.node_id, request.text, request.neighborhood)
        return self._invoke("blind", request, payload)

    def compare(self, request):
        blind = rich_verifier_input_v2(request.node_id, request.text, request.neighborhood)
        identity = request_identity(blind, self.context)
        previous = self._get(identity)
        if previous is None:
            raise ValueError("Persisted rich-v2 blind dependency unavailable")
        raw = self._replay(identity, previous, blind, None, "blind", request.text)
        if (raw["abstain"] or raw["class_index"] != request.blind_class_index):
            raise ValueError("Rich-v2 blind abstained or comparison class differs")
        payload = rich_verifier_input_v2(
            request.node_id, request.text, request.neighborhood,
            candidates=request.historical_candidates, blind_class=request.blind_class_index)
        return self._invoke("compare", request, payload, digest(raw))
