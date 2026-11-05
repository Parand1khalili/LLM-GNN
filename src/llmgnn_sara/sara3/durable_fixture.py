"""Crash-durable, offline-only fixture replay for the existing routing pipeline.

Intent is persisted before a fixture call; only independently L1-valid completed
responses can be replayed. Unknown/failed attempts are NEVER automatically retried.
This does not implement or authorize live transport, model calls, or training.
"""
import json
import os
import stat
from contextlib import closing
import sqlite3

from .audit import PrivateAudit
from .evidence import EvidenceError, validate_result
from .experiment import FIXTURE_VERSION, digest, request_identity
from .inputs import canonical_bytes, verifier_input

VERSION = "sara.offline.fixture.journal.v1"
_STATES = frozenset(("UNCERTAIN", "REJECTED", "COMPLETED"))


class DurableOfflineFixtureVerifier:
    """Offline fixture with private, bound SQLite intents and audit receipts.

    Each unique effective request is attempted at most once, across processes.
    An ambiguous crash leaves UNCERTAIN and requires manual reconciliation.
    This deliberately prioritizes no duplicate dispatch over automatic liveness.
    """
    offline = True

    def __init__(self, verifier, context, audit, *, maximum_calls):
        if (getattr(verifier, "offline", None) is not True
                or getattr(verifier, "fixture_version", None) != context.get("fixture_version")
                or context.get("fixture_version") != FIXTURE_VERSION
                or context.get("mode") != "OFFLINE_SYNTHETIC_ONLY"
                or type(audit) is not PrivateAudit
                or type(maximum_calls) is not int or maximum_calls < 1):
            raise ValueError("Only explicitly budgeted offline fixtures are supported")
        if any(value is not None for value in context.get("model_settings", {}).values()):
            raise ValueError("Provider configuration is forbidden in offline fixture journal")
        self._journal_version = VERSION
        self.verifier, self.audit = verifier, audit
        self.context = json.loads(canonical_bytes(context))
        self.context_digest = digest(self.context)
        self.maximum_calls = maximum_calls
        self.path = audit.root / "fixture_journal.sqlite"
        if self.path.is_symlink() or self.path.parent != audit.root:
            raise ValueError("Unsafe journal path")
        self.dispatches = self.hits = 0
        self._open_database()

    def _connection(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.execute("PRAGMA synchronous=FULL")
        return db

    def _open_database(self):
        existed = self.path.exists()
        if existed and os.name != "nt" and stat.S_IMODE(self.path.stat().st_mode) != 0o600:
            raise ValueError("Existing fixture journal permissions are unsafe")
        with closing(self._connection()) as db:
            with db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("CREATE TABLE IF NOT EXISTS binding (id INTEGER PRIMARY KEY CHECK(id=1), version TEXT NOT NULL, context_hash TEXT NOT NULL, call_limit INTEGER NOT NULL)")
                db.execute("CREATE TABLE IF NOT EXISTS intents (identity TEXT PRIMARY KEY, payload_hash TEXT NOT NULL, dependency TEXT, phase TEXT NOT NULL, state TEXT NOT NULL, receipt TEXT, node_id INTEGER NOT NULL, UNIQUE(node_id,phase))")
                expected = (self._journal_version, self.context_digest, self.maximum_calls)
                old = db.execute("SELECT version,context_hash,call_limit FROM binding WHERE id=1").fetchone()
                if old is None:
                    if existed or db.execute("SELECT count(*) FROM intents").fetchone()[0]:
                        raise ValueError("Unbound existing fixture journal")
                    db.execute("INSERT INTO binding VALUES(1,?,?,?)", expected)
                elif old != expected:
                    raise ValueError("Fixture journal bound to another protocol or budget")
        if not existed and os.name != "nt":
            # The parent PrivateAudit directory is already restricted to 0700.
            os.chmod(self.path, 0o600)

    def _verify_binding(self, db):
        if db.execute("SELECT version,context_hash,call_limit FROM binding WHERE id=1").fetchall() != [
                (self._journal_version, self.context_digest, self.maximum_calls)]:
            raise ValueError("Fixture journal binding mismatch")

    def _get(self, identity):
        if self.path.is_symlink():
            raise ValueError("Unsafe journal path")
        with closing(self._connection()) as db:
            self._verify_binding(db)
            return db.execute("SELECT payload_hash,dependency,phase,state,receipt FROM intents WHERE identity=?", (identity,)).fetchone()

    def _budget_accepts_new_intent(self, existing_count):
        """Subclass hook called under the SQLite write lock."""
        return None

    def _reserve(self, identity, payload_hash, dependency, phase, node_id):
        if self.path.is_symlink():
            raise ValueError("Unsafe journal path")
        with closing(self._connection()) as db:
            with db:
                db.execute("BEGIN IMMEDIATE")
                self._verify_binding(db)
                if db.execute("SELECT 1 FROM intents WHERE identity=? OR (node_id=? AND phase=?)",
                              (identity, node_id, phase)).fetchone():
                    raise EvidenceError("TIMEOUT_UNCERTAIN_NO_RETRY")
                count = db.execute("SELECT count(*) FROM intents").fetchone()[0]
                if count >= self.maximum_calls:
                    raise ValueError("Offline fixture dispatch budget exhausted")
                self._budget_accepts_new_intent(count)
                # UNKNOWN from the instant this row commits, even if process dies before send.
                db.execute("INSERT INTO intents VALUES(?,?,?,?,?,NULL,?)",
                           (identity, payload_hash, dependency, phase, "UNCERTAIN", node_id))

    def _settle(self, identity, state, receipt):
        if state not in {"REJECTED", "COMPLETED"} or not isinstance(receipt, str):
            raise ValueError("Invalid journal settlement")
        with closing(self._connection()) as db:
            with db:
                db.execute("BEGIN IMMEDIATE")
                self._verify_binding(db)
                if db.execute("UPDATE intents SET state=?, receipt=? WHERE identity=? AND state='UNCERTAIN'",
                              (state, receipt, identity)).rowcount != 1:
                    raise ValueError("Illegal terminal transition")

    def _validate(self, raw, text):
        """Legacy default; prospective rich-v2 subclass overrides this validator."""
        return validate_result(raw, text)

    def _replay(self, identity, row, payload, dependency, phase, text):
        payload_hash, saved_dep, saved_phase, state, receipt = row
        if (payload_hash, saved_dep, saved_phase) != (digest(payload), dependency, phase):
            raise ValueError("Fixture request identity binding mismatch")
        if state != "COMPLETED":
            if state not in _STATES:
                raise ValueError("Unknown fixture journal state")
            raise EvidenceError("TIMEOUT_UNCERTAIN_NO_RETRY" if state == "UNCERTAIN"
                                else "VERIFIER_FAILURE_UNCERTAIN")
        if not receipt:
            raise ValueError("Missing completed fixture receipt")
        record = self.audit.read(receipt)
        if (record.get("kind") != "durable_fixture_response"
                or record.get("identity") != identity
                or record.get("payload_sha256") != payload_hash
                or record.get("context_sha256") != self.context_digest
                or record.get("blind_response_sha256") != dependency):
            raise ValueError("Fixture audit binding mismatch")
        raw = record.get("raw_response")
        self._validate(raw, text)
        return json.loads(canonical_bytes(raw))

    def _invoke(self, phase, request, payload, dependency=None):
        identity = request_identity(payload, self.context, blind_response_sha256=dependency)
        row = self._get(identity)
        if row is not None:
            result = self._replay(identity, row, payload, dependency, phase, request.text)
            self.hits += 1
            return result
        self._reserve(identity, digest(payload), dependency, phase, request.node_id)
        # Any crash or pre-dispatch audit failure after reservation remains UNCERTAIN.
        intent = {"kind": "durable_fixture_intent", "identity": identity,
                  "payload_sha256": digest(payload), "context_sha256": self.context_digest,
                  "blind_response_sha256": dependency}
        intent_sha = self.audit.write(intent)
        if self.audit.read(intent_sha) != intent:
            raise ValueError("Unreadable fixture intent")
        self.dispatches += 1
        try:
            raw = json.loads(canonical_bytes(getattr(self.verifier, phase)(request)))
        except Exception:
            # Cannot prove dispatch didn't happen, so keep UNCERTAIN on any exception.
            raise
        receipt = self.audit.write({"kind": "durable_fixture_response", "identity": identity,
                                    "payload_sha256": digest(payload),
                                    "context_sha256": self.context_digest,
                                    "blind_response_sha256": dependency,
                                    "raw_response": raw})
        try:
            self._validate(raw, request.text)
        except (EvidenceError, ValueError, TypeError):
            self._settle(identity, "REJECTED", receipt)
            raise
        self._settle(identity, "COMPLETED", receipt)
        return json.loads(canonical_bytes(raw))

    def blind(self, request):
        payload = verifier_input(request.node_id, request.text, request.neighborhood)
        return self._invoke("blind", request, payload)

    def compare(self, request):
        blind = verifier_input(request.node_id, request.text, request.neighborhood)
        blind_identity = request_identity(blind, self.context)
        previous = self._get(blind_identity)
        if previous is None:
            raise ValueError("Persisted blind dependency unavailable")
        raw = self._replay(blind_identity, previous, blind, None, "blind", request.text)
        if raw["abstain"] or raw["class_index"] != request.blind_class_index:
            raise ValueError("Persisted blind is abstaining or has a different class")
        payload = verifier_input(request.node_id, request.text, request.neighborhood,
                                  candidates=request.historical_candidates,
                                  blind_class=request.blind_class_index)
        return self._invoke("compare", request, payload, digest(raw))

    @property
    def cache(self):
        """Only completed, receipt-bound entries (for offline run accounting)."""
        with closing(self._connection()) as db:
            self._verify_binding(db)
            return {identity: receipt for identity, receipt in db.execute(
                "SELECT identity,receipt FROM intents WHERE state='COMPLETED'")}

    @property
    def states(self):
        with closing(self._connection()) as db:
            self._verify_binding(db)
            return {identity: state for identity, state in db.execute(
                "SELECT identity,state FROM intents")}

    def snapshot(self):
        with closing(self._connection()) as db:
            self._verify_binding(db)
            return [dict(identity=i, state=s) for i, s in db.execute(
                "SELECT identity,state FROM intents ORDER BY identity")]
