"""Flask receiver: save raw bytes first, then decode."""

import base64
import hashlib
import json
import os
import shutil
import socket
import tempfile
import threading
from pathlib import Path

from flask import Flask, jsonify, request
from werkzeug.serving import make_server

from services.http_status import HttpStatus
from src.dupe import dupe_fingerprint


class Receiver:
    HOST = "127.0.0.1"
    # Docker sets BIND_HOST=0.0.0.0 so published ports are reachable from the Mac.
    BIND_HOST = os.environ.get("BIND_HOST", "127.0.0.1")
    PATH = "/v1/events"

    def __init__(self, out_dir):
        self.out = Path(out_dir)
        self.seq = 0
        self.port = None
        self.url = None
        self._server = None
        self._temp_out = False
        self.app = Flask(__name__)
        self.app.add_url_rule(self.PATH, "receive", self.receive, methods=["POST"])
        self.app.add_url_rule(self.PATH, "list_events", self.list_events, methods=["GET"])

    def disconnect(self):
        """Turn the receiver off (and delete temp folder if we created one)."""
        if self._server is not None:
            self._server.shutdown()
            self._server = None
        if self._temp_out and self.out.exists():
            shutil.rmtree(self.out, ignore_errors=True)

    def _find_stored_duplicate(self, event):
        """Return the first stored row with the same body fingerprint, or None."""
        key = dupe_fingerprint(event)
        for row in self._stored_rows():
            stored = row.get("event")
            if stored is not None and dupe_fingerprint(stored) == key:
                return row
        return None

    def receive(self):
        body = request.get_data()
        self.seq = self.seq + 1

        raw_path = self.out / "raw" / (str(self.seq).zfill(6) + ".b64")
        raw_path.write_bytes(body)

        receipt = {
            "seq": self.seq,
            "sha256": hashlib.sha256(body).hexdigest(),
        }

        try:
            text = base64.b64decode(body).decode("utf-8")
            event = json.loads(text)
            allow_redeploy = bool(
                request.headers.get("Idempotency-Key")
                or request.headers.get("X-Replay")
            )
            prior = None if allow_redeploy else self._find_stored_duplicate(event)
            if prior is not None:
                receipt["decode_status"] = "duplicate"
                receipt["blocked"] = True
                receipt["duplicate_of_seq"] = prior.get("seq")
                receipt["duplicate_of_case_id"] = prior.get("case_id")
                with (self.out / "receipts.jsonl").open("a", encoding="utf-8") as f:
                    f.write(json.dumps(receipt) + "\n")
                return jsonify(receipt), HttpStatus.CONFLICT

            receipt["decode_status"] = "ok"
            row = {"seq": self.seq, "event": event}
            case_id = request.headers.get("X-Case-Id")
            if case_id:
                row["case_id"] = case_id
            kept_headers = {}
            for name in ("Idempotency-Key", "X-Retry-Count", "X-Replay", "X-Delivery", "X-Case-Id"):
                value = request.headers.get(name)
                if value:
                    kept_headers[name] = value
            if kept_headers:
                row["headers"] = kept_headers
            with (self.out / "events.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
        except Exception:
            receipt["decode_status"] = "error"

        with (self.out / "receipts.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(receipt) + "\n")

        return jsonify(receipt), HttpStatus.ACCEPTED

    def _stored_rows(self):
        """Load decoded rows previously saved by POST."""
        path = self.out / "events.jsonl"
        if not path.exists():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def list_events(self):
        """GET stored events (optional ?case_id= filter) — data after it went through the API."""
        rows = self._stored_rows()
        case_id = request.args.get("case_id")
        if case_id:
            rows = [row for row in rows if row.get("case_id") == case_id]
        return jsonify({"events": rows}), HttpStatus.OK

    def start(self, port=8765, blocking=False):
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / "raw").mkdir(exist_ok=True)

        # continue sequence if files already exist
        existing = list((self.out / "raw").glob("*.b64"))
        self.seq = len(existing)

        self.port = port
        self.url = "http://" + self.HOST + ":" + str(port) + self.PATH

        server = make_server(self.BIND_HOST, port, self.app)
        if blocking:
            print("Listening " + self.url)
            server.serve_forever()
            return server

        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        return server


def find_free_port():
    """Ask the OS for any free port on this computer."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def connect(out_dir=None, port=None):
    """
    Turn the receiver on and return it ready to use.

    If out_dir is omitted, uses a temp folder (deleted on disconnect).
    If port is omitted, picks a free port.
    """
    temp_out = out_dir is None
    if temp_out:
        out_dir = tempfile.mkdtemp(prefix="receiver-")

    receiver = Receiver(out_dir)
    receiver._temp_out = temp_out

    if port is None:
        port = find_free_port()

    try:
        receiver._server = receiver.start(port)
    except OSError:
        port = find_free_port()
        receiver._server = receiver.start(port)

    return receiver
