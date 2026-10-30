"""Persistent intent cap for future reviewed execution; never sends a request."""
import hashlib
from pathlib import Path
import sqlite3
from contextlib import closing

from .protocol import _encoded, _safe_path, _inspect_keys, _SHA
from ..io.frozen import reject_gt


class DurablePilotLedger:
    def __init__(self, path, manifest_sha256):
        if type(manifest_sha256) is not str or not _SHA.fullmatch(manifest_sha256):
            raise ValueError("Pilot manifest pin required")
        self.path = _safe_path(Path(path))
        if self.path.suffix not in (".sqlite", ".db"):
            raise ValueError("Dedicated SQLite ledger path required")
        existed = self.path.exists()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            if not existed:
                db.execute("CREATE TABLE seal (sha TEXT NOT NULL)")
                db.execute("INSERT INTO seal VALUES (?)", (manifest_sha256,))
                db.execute("CREATE TABLE calls (id TEXT PRIMARY KEY, payload_sha TEXT UNIQUE NOT NULL, state TEXT NOT NULL)")
            try:
                row = db.execute("SELECT sha FROM seal").fetchall()
            except sqlite3.DatabaseError:
                raise ValueError("Not a SARA pilot ledger") from None
            if row != [(manifest_sha256,)]:
                raise ValueError("Ledger belongs to another pilot seal")

    def begin(self, request_id, payload):
        if type(request_id) is not str or not request_id:
            raise ValueError("Request identity required")
        reject_gt(payload)
        _inspect_keys(payload, blind=False)
        digest = hashlib.sha256(_encoded(payload)).hexdigest()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT count(*) FROM calls").fetchone()[0] >= 12:
                raise ValueError("Twelve-call intent budget exhausted")
            try:
                db.execute("INSERT INTO calls VALUES (?, ?, 'INTENT')", (request_id, digest))
            except sqlite3.IntegrityError:
                raise ValueError("Duplicate identity/payload; retry blocked") from None

    def settle(self, request_id, state):
        if state not in ("COMPLETED", "REJECTED", "UNCERTAIN"):
            raise ValueError("Invalid terminal state")
        with closing(sqlite3.connect(self.path)) as db, db:
            changed = db.execute("UPDATE calls SET state=? WHERE id=? AND state='INTENT'",
                                 (state, request_id)).rowcount
            if changed != 1:
                raise ValueError("Unknown intent or terminal state rewrite")

    def snapshot(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            return [{"request_id": row[0], "payload_sha256": row[1], "state": row[2]}
                    for row in db.execute("SELECT id,payload_sha,state FROM calls ORDER BY rowid")]
