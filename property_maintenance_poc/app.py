from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / "data" / "records.json").read_text())
RUNS = ROOT / "state" / "runs.json"
REVIEWS = ROOT / "state" / "reviews.json"

def now():
    return datetime.now(timezone.utc).isoformat()

def load(path):
    return json.loads(path.read_text()) if path.exists() else []

def save(path, value):
    path.write_text(json.dumps(value, indent=2))

def key_for(payload):
    source = payload.get("message_id") or json.dumps(payload, sort_keys=True)
    return hashlib.sha256(source.encode()).hexdigest()

def find_tenant(email):
    return next((x for x in DATA["tenants"] if x["email"].lower() == email.lower()), None)

def find_lease(lease_id):
    return next((x for x in DATA["leases"] if x["lease_id"] == lease_id), None)

def assess(payload, tenant, lease):
    text = f'{payload.get("subject","")} {payload.get("body","")}'.lower()
    emergency = any(x in text for x in ["fire", "gas leak", "burst pipe", "flooding"])
    plumbing = any(x in text for x in ["water", "leak", "sink", "pipe", "toilet"])
    misuse = any(x in text for x in ["i broke", "misuse", "accidentally damaged"])

    missing = []
    if not tenant: missing.append("tenant match")
    if not lease: missing.append("lease")

    clauses = []
    if lease:
        clauses = [c for c in lease["clauses"] if c["type"] in ("plumbing", "tenant_damage")]

    if missing:
        responsibility, confidence = "undetermined", 0.25
    elif misuse:
        responsibility, confidence = "tenant", 0.76
    elif plumbing and clauses:
        responsibility, confidence = "landlord", 0.88
    else:
        responsibility, confidence = "undetermined", 0.45

    status = "manual_review" if emergency or confidence < 0.80 else "completed"
    return {
        "issue_type": "plumbing" if plumbing else "general_maintenance",
        "severity": "emergency" if emergency else "urgent" if plumbing else "normal",
        "recommended_responsibility": responsibility,
        "confidence": confidence,
        "evidence": [{"clause_id": c["clause_id"], "text": c["text"]} for c in clauses],
        "missing_information": missing,
        "status": status
    }

def process_email(payload):
    for field in ("from", "subject", "body"):
        if field not in payload:
            raise ValueError(f"Missing required field: {field}")

    key = key_for(payload)
    runs = load(RUNS)
    prior = next((r for r in runs if r["idempotency_key"] == key), None)
    if prior:
        return {"duplicate": True, "workflow_run": prior}

    tenant = find_tenant(payload["from"])
    lease = find_lease(tenant["lease_id"]) if tenant else None
    result = assess(payload, tenant, lease)

    run = {
        "run_id": f"run-{len(runs)+1:04d}",
        "idempotency_key": key,
        "created_at": now(),
        "status": result["status"],
        "tenant": tenant,
        "assessment": result
    }
    runs.append(run)
    save(RUNS, runs)

    if result["status"] == "manual_review":
        reviews = load(REVIEWS)
        reviews.append({
            "review_id": f"review-{len(reviews)+1:04d}",
            "run_id": run["run_id"],
            "status": "open",
            "payload": payload,
            "assessment": result
        })
        save(REVIEWS, reviews)

    return {"duplicate": False, "workflow_run": run}

HTML = """<!doctype html><html><body style="font-family:Arial;max-width:850px;margin:40px auto">
<h1>Property Maintenance Triage PoC</h1>
<p>Uses synthetic data. Submit the same message ID twice to test duplicate prevention.</p>
<input id="id" value="graph-msg-1001" style="width:100%;margin:5px"><br>
<input id="from" value="tenant1@example.com" style="width:100%;margin:5px"><br>
<input id="subject" value="Water leaking under kitchen sink" style="width:100%;margin:5px"><br>
<textarea id="body" style="width:100%;height:100px;margin:5px">Water is leaking under the kitchen sink and getting worse.</textarea><br>
<button onclick="go()">Run triage</button><pre id="out"></pre>
<script>
async function go(){
 const p={message_id:id.value,from:document.getElementById('from').value,subject:subject.value,body:body.value};
 const r=await fetch('/triage',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});
 out.textContent=JSON.stringify(await r.json(),null,2);
}
</script></body></html>"""

class Handler(BaseHTTPRequestHandler):
    def reply(self, code, body, content_type="application/json"):
        raw = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/":
            self.reply(200, HTML, "text/html")
        elif self.path == "/runs":
            self.reply(200, json.dumps(load(RUNS), indent=2))
        elif self.path == "/reviews":
            self.reply(200, json.dumps(load(REVIEWS), indent=2))
        else:
            self.reply(404, json.dumps({"error":"not found"}))

    def do_POST(self):
        if self.path != "/triage":
            return self.reply(404, json.dumps({"error":"not found"}))
        try:
            n = int(self.headers.get("Content-Length","0"))
            payload = json.loads(self.rfile.read(n))
            self.reply(200, json.dumps(process_email(payload), indent=2))
        except ValueError as e:
            self.reply(400, json.dumps({"error":str(e)}))
        except Exception as e:
            self.reply(500, json.dumps({"error":str(e)}))

    def log_message(self, *args):
        pass

if __name__ == "__main__":
    print("Running at http://localhost:8000")
    HTTPServer(("localhost",8000), Handler).serve_forever()
