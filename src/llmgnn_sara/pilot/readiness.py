"""Offline execution-safety rehearsal. No transport or credential loading."""
import hashlib
import json
import sqlite3
from contextlib import closing

from .protocol import _safe_path
from pathlib import Path

CONTRACT = {
    "version": "sara.pilot.execution.draft.v1", "status": "OFFLINE_ONLY_NOT_AUTHORIZED",
    "cohort": [637, 1243, 130, 682, 2396, 653],
    "schema_recommendation": "LEGACY_UNCHANGED_PENDING_APPROVAL",
    "provider": None, "endpoint": None, "model": None, "model_revision": None,
    "generation_settings": None, "privacy_retention": None, "credentials_source": None,
    "maximum_calls": 12, "input_token_cap": 16384, "output_token_cap": 512,
    "token_count_method": None, "spending_budget": None, "prices": None,
}


def assert_live_ready(contract):
    raise ValueError("Live execution disabled; unresolved settings and separate authorization required")


CONTRACT["sealed_bundle_sha256"] = "29fa95c7d34f5826b628509e6bad2baced83ac986ebfbc7cadc4bb36d4c31b41"
CONTRACT["financial_approval"] = "UNRESOLVED"
CONTRACT["schema"] = "LEGACY"

def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

CONTRACT_BYTES = encoded(CONTRACT)
CONTRACT_SHA256 = hashlib.sha256(CONTRACT_BYTES).hexdigest()

class ReadinessLedger:
    """Offline-only sealed reservations. Never migrates an earlier database."""
    def __init__(self, path, contract_sha256=CONTRACT_SHA256):
        if contract_sha256 != CONTRACT_SHA256 or encoded(CONTRACT) != CONTRACT_BYTES:
            raise ValueError("Unverified contract")
        self.pin = contract_sha256
        self.path = _safe_path(Path(path))
        if self.path.suffix not in (".sqlite", ".db"):
            raise ValueError("Dedicated database required")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("PRAGMA synchronous=FULL")
            tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if not tables:
                db.execute("CREATE TABLE contract (sha TEXT PRIMARY KEY)")
                db.execute("INSERT INTO contract VALUES (?)", (self.pin,))
                db.execute("CREATE TABLE intents (id TEXT PRIMARY KEY, contract_sha TEXT, request_sha TEXT UNIQUE, state TEXT, input_cap INTEGER, output_cap INTEGER, raw_sha TEXT, audit_sha TEXT)")
            self._verify(db)

    def _verify(self, db):
        if db.execute("SELECT sha FROM contract").fetchall() != [(self.pin,)]:
            raise ValueError("Wrong database contract")
        if db.execute("SELECT count(*) FROM intents WHERE contract_sha != ?",(self.pin,)).fetchone()[0]:
            raise ValueError("Intent contract mismatch")

    def _payload(self, payload):
        from ..io.frozen import reject_gt
        from ..sara3.inputs import RESPONSE_SCHEMA, verifier_input
        reject_gt(payload)
        if (payload.get("node_id") not in CONTRACT["cohort"] or payload.get("phase") not in ("blind","compare")
                or payload.get("response_schema") != RESPONSE_SCHEMA
                or payload.get("instructions") != verifier_input(payload.get("node_id"),payload.get("target",{}).get("text",""), **({"candidates":payload.get("historical_candidates",()),"blind_class":payload.get("blind_class_index")} if payload.get("phase")=="compare" else {}))["instructions"]):
            raise ValueError("Wrong cohort/schema/protocol")
        return hashlib.sha256(encoded(payload)).hexdigest()

    def reserve(self, identity, payload, input_cap, output_cap, context_sha256=CONTRACT_SHA256):
        if context_sha256 != self.pin or type(identity) is not str or not identity:
            raise ValueError("Identity/context mismatch")
        if any(type(v) is not int or v <= 0 for v in (input_cap,output_cap)) or input_cap>16384 or output_cap>512:
            raise ValueError("Token reservation exceeded")
        request_sha=self._payload(payload)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            self._verify(db)
            count, inputs, outputs=db.execute("SELECT count(*),coalesce(sum(input_cap),0),coalesce(sum(output_cap),0) FROM intents").fetchone()
            if count>=12 or inputs+input_cap>12*16384 or outputs+output_cap>12*512:
                raise ValueError("Reservation exhausted")
            try: db.execute("INSERT INTO intents VALUES (?,?,?,?,?,?,NULL,NULL)",(identity,self.pin,request_sha,"PENDING",input_cap,output_cap))
            except sqlite3.IntegrityError: raise ValueError("Duplicate intent; retry blocked") from None

    def mark_dispatched(self, identity, payload):
        self._transition(identity,payload,"PENDING","UNCERTAIN",None,None)

    def settle(self, identity, payload, raw_response, audit, *, rejection_reason=None):
        from ..sara3.evidence import validate_result
        from ..sara3.audit import PrivateAudit
        if type(raw_response) is not bytes or type(audit) is not PrivateAudit:
            raise ValueError("Raw bytes and private audit required")
        # Check bindings before writing audit; no terminal-state rewrites.
        self._check(identity,payload,"UNCERTAIN")
        raw_sha=hashlib.sha256(raw_response).hexdigest()
        state="REJECTED"
        reason="MALFORMED_JSON"
        try:
            def unique(items):
                result={}
                for k,v in items:
                    if k in result: raise ValueError("Duplicate key")
                    result[k]=v
                return result
            response=json.loads(raw_response,object_pairs_hook=unique)
            validate_result(response,payload["target"]["text"])
            state,reason="COMPLETED","L1_PASS_L2_NOT_ASSESSED"
        except (ValueError,TypeError,UnicodeError) as error:
            reason=getattr(error,"code","MALFORMED_JSON_OR_SCHEMA")
        if rejection_reason is not None:
            if rejection_reason not in {"BODY_LIMIT", "SECRET_ECHO_REDACTED", "HTTP_REJECTION_NO_RETRY",
                                        "TRUNCATED_OR_NONFINAL", "INVALID_ENVELOPE_OR_USAGE"}:
                raise ValueError("Unknown protocol rejection")
            state,reason="REJECTED",rejection_reason
        receipt=audit.write({"kind":"readiness_response","raw_hex":raw_response.hex(),"raw_sha256":raw_sha,
            "contract_sha256":self.pin,"request_sha256":self._payload(payload),"reason":reason})
        record=audit.read(receipt)
        if record["raw_sha256"]!=raw_sha or bytes.fromhex(record["raw_hex"])!=raw_response:
            raise ValueError("Audit readback failed")
        self._transition(identity,payload,"UNCERTAIN",state,raw_sha,receipt)
        return {"state":state,"reason":reason,"l2_status":"NOT_ASSESSED","accepted_label":None}

    def _check(self, identity, payload, previous):
        with closing(sqlite3.connect(self.path)) as db:
            self._verify(db)
            if db.execute("SELECT request_sha,state FROM intents WHERE id=?",(identity,)).fetchone() != (self._payload(payload),previous):
                raise ValueError("Wrong request/state; no retry")

    def _transition(self, identity, payload, previous, state, raw_sha, audit_sha):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            self._verify(db)
            changed=db.execute("UPDATE intents SET state=?,raw_sha=?,audit_sha=? WHERE id=? AND contract_sha=? AND request_sha=? AND state=?",
                (state,raw_sha,audit_sha,identity,self.pin,self._payload(payload),previous)).rowcount
            if changed!=1: raise ValueError("Wrong request/state; no retry")

    def snapshot(self):
        with closing(sqlite3.connect(self.path)) as db:
            self._verify(db)
            return db.execute("SELECT * FROM intents ORDER BY id").fetchall()
