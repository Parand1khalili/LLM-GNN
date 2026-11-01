"""In-process offline fixture reuse only; no live transport or billing guarantee."""
import json

from .audit import PrivateAudit
from .evidence import EvidenceError, validate_result
from .experiment import FIXTURE_VERSION, digest, request_identity
from .inputs import canonical_bytes, verifier_input


class CachedOfflineVerifier:
    offline = True

    def __init__(self, verifier, context, audit):
        if (getattr(verifier, "offline", None) is not True
                or getattr(verifier, "fixture_version", None) != context.get("fixture_version")
                or context.get("fixture_version") != FIXTURE_VERSION or type(audit) is not PrivateAudit):
            raise ValueError("Versioned offline fixture and private audit required")
        self.verifier, self.audit = verifier, audit
        self._context_bytes = canonical_bytes(context)
        self.cache, self.states, self.blind_results = {}, {}, {}
        self.hits = self.dispatches = 0

    def _invoke(self, phase, request, payload, dependency=None):
        context = json.loads(self._context_bytes)
        identity = request_identity(payload, context, blind_response_sha256=dependency)
        if identity in self.cache:
            record = self.audit.read(self.cache[identity])
            if (record["identity"] != identity or record["payload_sha256"] != digest(payload)
                    or record["context"] != context or record["blind_response_sha256"] != dependency):
                raise ValueError("Cached response binding differs")
            self.hits += 1
            return record["raw_response"]
        if identity in self.states:
            raise EvidenceError("TIMEOUT_UNCERTAIN_NO_RETRY" if self.states[identity] in {"INTENT", "UNCERTAIN"}
                                else "VERIFIER_FAILURE_UNCERTAIN")
        self.states[identity] = "INTENT"
        raw = None
        try:
            self.audit.write({"kind": "fixture_cache_intent", "identity": identity,
                              "payload_sha256": digest(payload), "context": context})
            self.dispatches += 1
            raw = json.loads(canonical_bytes(getattr(self.verifier, phase)(request)))
            # Preserve decoded output privately before validation or reuse admission.
            receipt = self.audit.write({"kind": "fixture_cache_response", "identity": identity,
                "payload_sha256": digest(payload), "context": context,
                "blind_response_sha256": dependency, "raw_response": raw})
            validate_result(raw, request.text)
            self.cache[identity] = receipt
            self.states[identity] = "COMPLETED"
            return json.loads(canonical_bytes(raw))
        except Exception as error:
            self.states[identity] = "UNCERTAIN" if isinstance(error, TimeoutError) else "REJECTED"
            self.audit.write({"kind": "fixture_cache_rejection", "identity": identity,
                "state": self.states[identity], "reason": getattr(error, "code", "OFFLINE_FIXTURE_FAILURE")})
            raise

    def blind(self, request):
        payload = verifier_input(request.node_id, request.text, request.neighborhood)
        response = self._invoke("blind", request, payload)
        self.blind_results[digest(payload)] = canonical_bytes(response)
        return response

    def compare(self, request):
        blind = verifier_input(request.node_id, request.text, request.neighborhood)
        raw = self.blind_results.get(digest(blind))
        if raw is None:
            raise ValueError("Blind dependency unavailable")
        response = json.loads(raw)
        if response["abstain"] or response["class_index"] != request.blind_class_index:
            raise ValueError("Blind dependency differs")
        payload = verifier_input(request.node_id, request.text, request.neighborhood,
            candidates=request.historical_candidates, blind_class=request.blind_class_index)
        return self._invoke("compare", request, payload, digest(response))
