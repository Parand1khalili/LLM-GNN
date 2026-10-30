"""Fail-closed offline ledger state machine. No network dispatch is implemented.

This in-memory ledger is for offline integration, not crash-durable live billing
protection. A future live bridge must persist an intent atomically before sending.
"""
from dataclasses import dataclass
import hashlib
import json


@dataclass(frozen=True)
class LedgerEntry:
    request_id: str
    payload_sha256: str
    state: str


class OfflineLedger:
    def __init__(self):
        self._entries: dict[str, LedgerEntry] = {}

    def begin(self, request_id: str, payload: dict) -> None:
        if type(request_id) is not str or not request_id:
            raise ValueError("Invalid request ID")
        if request_id in self._entries:
            raise ValueError("Duplicate request: retry is blocked")
        raw = json.dumps(payload, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
        self._entries[request_id] = LedgerEntry(request_id, hashlib.sha256(raw).hexdigest(), "INTENT")

    def settle(self, request_id: str, state: str) -> None:
        entry = self._entries[request_id]
        if entry.state != "INTENT" or state not in {"COMPLETED", "REJECTED", "UNCERTAIN"}:
            raise ValueError("Illegal ledger transition")
        self._entries[request_id] = LedgerEntry(request_id, entry.payload_sha256, state)

    def snapshot(self):
        return [{"request_id": e.request_id, "payload_sha256": e.payload_sha256, "state": e.state}
                for e in self._entries.values()]
