"""Opt-in, receipt-verified continuation of the frozen Expanded Atlas batch.

Only an L1_QUOTE_NOT_FOUND comparison whose saved response passes exact-first
diagnostics can be skipped. It stays REJECTED. No retries, ledger rewrites,
semantic L2 approval, GT access, or changes to the default Gateway behavior.
"""
from contextlib import closing
import hashlib

from .evidence import EXACT_FIRST, EvidenceError
from .experiment import digest
from .gapgpt_live import DurableGapGPTVerifier, strict_envelope, wire_for
from .rich_evidence import rich_verifier_input_v2

VERSION = "sara.expanded_atlas.settled_compare_continuation.v1"
_REJECTION = "L1_QUOTE_NOT_FOUND"


class ExpandedAtlasResumeVerifier(DurableGapGPTVerifier):
    """Explicit opt-in for *only* the Atlas batch's verified settled rejection."""

    def _rejected_compare(self, identity, row, payload, wire, dependency, text):
        if (row[:4] != (digest(payload), dependency, "compare", "REJECTED")
                or type(row[4]) is not str):
            raise ValueError("Rejected comparison binding mismatch")
        record = self.audit.read(row[4])
        expected = {
            "kind": "gapgpt_gateway_response",
            "identity": identity,
            "context_sha256": self.context_digest,
            "payload_sha256": digest(payload),
            "dependency": dependency,
            "wire_sha256": hashlib.sha256(wire).hexdigest(),
            "reject_code": _REJECTION,
        }
        if any(record.get(k) != v for k, v in expected.items()):
            raise ValueError("Rejected comparison receipt mismatch")
        if type(record.get("raw_hex")) is not str:
            raise ValueError("Rejected comparison raw response missing")
        try:
            raw = bytes.fromhex(record["raw_hex"])
        except ValueError:
            raise ValueError("Rejected comparison invalid raw encoding") from None
        if hashlib.sha256(raw).hexdigest() != record.get("response_sha256"):
            raise ValueError("Rejected comparison raw hash mismatch")

        # Independently reproduce the original L1 failure. A normal malformed
        # response or incompatible provider envelope MUST NOT permit resumption.
        token = EXACT_FIRST.set(False)
        try:
            try:
                strict_envelope(record.get("http_status"), raw, self.config, self.key, text)
            except EvidenceError as exc:
                if exc.code != _REJECTION:
                    raise ValueError("Saved rejection no longer reproduces") from None
            else:
                raise ValueError("Saved rejection unexpectedly passes historical L1")
        finally:
            EXACT_FIRST.reset(token)

        # Diagnostic only: prove the same response passes literal source-first
        # checking AND the rest of the strict provider envelope, including usage.
        token = EXACT_FIRST.set(True)
        try:
            strict_envelope(record.get("http_status"), raw, self.config, self.key, text)
        finally:
            EXACT_FIRST.reset(token)

    def verify_saved_batch(self, pairs, selected):
        """Read and validate EVERY persisted intent before any further send."""
        if (self.context.get("router") != "r1_v1"
                or self.context.get("budget") != 37
                or self.context.get("cohort") != "sensitivity"
                or self.context.get("selected") != list(selected)
                or len(selected) != 37 or len(set(selected)) != 37):
            raise ValueError("Expanded Atlas continuation scope mismatch")
        by_node = {pair.node_id: pair for pair in pairs}
        if not set(selected) <= set(by_node):
            raise ValueError("Expanded Atlas missing target")
        with closing(self._connection()) as db:
            self._verify_binding(db)
            stored = list(db.execute(
                "SELECT identity,node_id,phase,state FROM intents"))
        seen = {}
        for identity, node, phase, state in stored:
            if (node not in selected or phase not in ("blind", "compare")
                    or (node, phase) in seen or state == "UNCERTAIN"):
                raise ValueError("Unexpected or uncertain saved intent")
            seen[(node, phase)] = identity

        expected = set()
        for node in selected:
            pair = by_node[node]
            bp = rich_verifier_input_v2(node, pair.text, pair.neighborhood)
            bw = wire_for(bp, self.config)
            bi = self._identity("blind", bp, bw, None)
            if (node, "blind") not in seen:
                if (node, "compare") in seen:
                    raise ValueError("Comparison without saved blind")
                continue
            if seen[(node, "blind")] != bi:
                raise ValueError("Saved blind identity mismatch")
            br = self._get(bi)
            if br is None:
                raise ValueError("Saved blind receipt missing")
            blind = self._completed(bi, br, bp, bw, None, "blind", pair.text)
            expected.add((node, "blind"))
            if (node, "compare") not in seen:
                continue
            if blind["abstain"]:
                raise ValueError("Comparison exists after abstaining blind")
            candidates = tuple(sorted({
                pair.b1.class_index, pair.narrative_v0.class_index}))
            cp = rich_verifier_input_v2(
                node, pair.text, pair.neighborhood,
                candidates=candidates, blind_class=blind["class_index"])
            cw = wire_for(cp, self.config)
            dep = digest(blind)
            ci = self._identity("compare", cp, cw, dep)
            if seen[(node, "compare")] != ci:
                raise ValueError("Saved comparison identity/dependency mismatch")
            cr = self._get(ci)
            if cr is None:
                raise ValueError("Saved comparison receipt missing")
            if cr[3] == "COMPLETED":
                self._completed(ci, cr, cp, cw, dep, "compare", pair.text)
            elif cr[3] == "REJECTED":
                self._rejected_compare(ci, cr, cp, cw, dep, pair.text)
            else:
                raise ValueError("Unsettled comparison")
            expected.add((node, "compare"))
        if set(seen) != expected:
            raise ValueError("Extra saved intents or missing dependencies")
        self._approved_pairs = tuple(pairs)
        self._approved_selected = tuple(selected)
        # This is strictly a post-verification liveness decision; no saved
        # REJECTED row or scientific result is promoted to COMPLETED.
        self.halted = False

    def _invoke(self, phase, request, payload, dependency=None):
        wire = wire_for(payload, self.config)
        identity = self._identity(phase, payload, wire, dependency)
        row = self._get(identity)
        if row is not None and row[3] == "REJECTED":
            if phase != "compare":
                raise ValueError("Rejected blind cannot be continued")
            self._rejected_compare(
                identity, row, payload, wire, dependency, request.text)
            raise EvidenceError(_REJECTION)
        try:
            return super()._invoke(phase, request, payload, dependency)
        except EvidenceError as exc:
            # The parent fail-closes on any rejected send. Only after the
            # exact persisted L1 failure is revalidated may independent nodes
            # continue. Anything uncertain, non-L1, or corrupted stays blocked.
            if (phase == "compare" and exc.code == _REJECTION
                    and self.halted and hasattr(self, "_approved_pairs")):
                self.verify_saved_batch(
                    self._approved_pairs, self._approved_selected)
            raise
