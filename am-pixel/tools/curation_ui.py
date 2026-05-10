#!/usr/bin/env python3.14
"""
tools/curation_ui.py
====================
Flask-based Golden Dataset curation UI.
Run: python tools/curation_ui.py
Then open: http://localhost:5001

Keyboard shortcuts:
  a = Accept    r = Reject    f = Flag for recalibration    n = Next (skip)
"""
from __future__ import annotations
import datetime
import json
import shutil
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

REVIEW_DIR   = PROJECT_ROOT / "data" / "golden_review"
SCORES_PATH  = REVIEW_DIR / "scores.json"
CUR_LOG      = REVIEW_DIR / "curation_log.jsonl"
GOLDEN_DIR   = PROJECT_ROOT / "data" / "golden"
GOLDEN_MAN   = GOLDEN_DIR / "golden_manifest.json"

GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

try:
    from flask import Flask, request, jsonify, send_file, abort
except ImportError:
    sys.exit("ERROR: pip install flask")

app = Flask(__name__)
SESSION_ID = str(uuid.uuid4())[:8]

# ── Data loading ───────────────────────────────────────────────────────────

def load_scores() -> list[dict]:
    if not SCORES_PATH.exists():
        return []
    return json.loads(SCORES_PATH.read_text())

def load_log() -> set[str]:
    """Return set of sprite_ids already decided."""
    decided = set()
    if CUR_LOG.exists():
        for line in CUR_LOG.read_text().splitlines():
            try:
                decided.add(json.loads(line)["sprite_id"])
            except Exception:
                pass
    return decided

def load_golden_manifest() -> list[dict]:
    if GOLDEN_MAN.exists():
        try:
            return json.loads(GOLDEN_MAN.read_text())
        except Exception:
            return []
    return []

# ── Routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return HTML_UI

@app.route("/api/queue")
def api_queue():
    bucket = request.args.get("bucket", "A_autopass")
    scores = load_scores()
    decided = load_log()
    queue = [s for s in scores if s.get("bucket") == bucket and s["sprite_id"] not in decided]
    total = len([s for s in scores if s.get("bucket") == bucket])
    reviewed = total - len(queue)
    return jsonify({"queue": queue, "total": total, "reviewed": reviewed, "remaining": len(queue)})

@app.route("/api/sprite_image")
def api_sprite_image():
    path = request.args.get("path", "")
    p = Path(path)
    if not p.exists() or not p.suffix.lower() == ".png":
        abort(404)
    return send_file(str(p), mimetype="image/png")

@app.route("/api/decide", methods=["POST"])
def api_decide():
    data = request.get_json()
    sprite_id  = data.get("sprite_id", "")
    decision   = data.get("decision", "")
    notes      = data.get("notes", "")
    scores_at  = data.get("rubric_scores", {})
    bucket     = data.get("bucket", "")

    if decision not in ("accept", "reject", "flag_recalibration"):
        return jsonify({"error": "invalid decision"}), 400

    # Write to curation log
    entry = {
        "sprite_id":              sprite_id,
        "decision":               decision,
        "notes":                  notes,
        "rubric_scores_at_decision": scores_at,
        "bucket":                 bucket,
        "timestamp":              datetime.datetime.utcnow().isoformat(),
        "session_id":             SESSION_ID,
    }
    with open(CUR_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    # On Accept: copy to golden dir + update manifest
    if decision == "accept":
        source_path = scores_at.get("source_path", "")
        src = Path(source_path) if source_path else None
        if src and src.exists():
            dest = GOLDEN_DIR / src.name
            # Handle collisions
            if dest.exists():
                dest = GOLDEN_DIR / f"{src.stem}_{sprite_id[:6]}{src.suffix}"
            dest.write_bytes(src.read_bytes())  # shutil.copy fails on NTFS/WSL

            manifest = load_golden_manifest()
            manifest.append({
                "sprite_id":         sprite_id,
                "golden_path":       str(dest),
                "source_tier2_path": source_path,
                "rubric_scores":     scores_at,
                "accepted_at":       entry["timestamp"],
                "accepted_by":       "human_curation",
                "notes":             notes,
                "bucket":            bucket,
                "session_id":        SESSION_ID,
            })
            GOLDEN_MAN.write_text(json.dumps(manifest, indent=2))

    return jsonify({"ok": True})

@app.route("/api/stats")
def api_stats():
    scores = load_scores()
    decided = load_log()
    bucket_counts: dict[str, int] = {}
    bucket_remaining: dict[str, int] = {}
    for s in scores:
        b = s.get("bucket", "unknown")
        bucket_counts[b] = bucket_counts.get(b, 0) + 1
        if s["sprite_id"] not in decided:
            bucket_remaining[b] = bucket_remaining.get(b, 0) + 1
    golden_count = len(load_golden_manifest())
    return jsonify({
        "bucket_counts":    bucket_counts,
        "bucket_remaining": bucket_remaining,
        "total_scored":     len(scores),
        "total_decided":    len(decided),
        "golden_accepted":  golden_count,
        "session_id":       SESSION_ID,
    })

# ── HTML UI ────────────────────────────────────────────────────────────────

HTML_UI = """<!DOCTYPE html>
<html>
<head><title>AM Pixel — Golden Dataset Curation</title>
<meta charset="utf-8">
<style>
body{font-family:monospace;background:#1a1a2e;color:#e0e0e0;margin:0;padding:0}
.header{background:#16213e;padding:12px 20px;border-bottom:1px solid #0f3460;display:flex;align-items:center;gap:20px}
.header h1{margin:0;font-size:16px;color:#e94560}
.stats{font-size:12px;color:#a0a0c0}
.main{display:flex;height:calc(100vh - 50px)}
.sidebar{width:200px;background:#16213e;border-right:1px solid #0f3460;padding:12px;flex-shrink:0}
.sidebar h3{margin:0 0 8px;font-size:13px;color:#e94560}
.bucket-btn{display:block;width:100%;text-align:left;background:none;border:1px solid #0f3460;color:#a0a0c0;padding:6px 8px;margin:3px 0;cursor:pointer;font-size:12px;font-family:monospace}
.bucket-btn.active{background:#0f3460;color:#e0e0e0;border-color:#e94560}
.bucket-btn:hover{background:#0f3460}
.content{flex:1;display:flex;flex-direction:column;align-items:center;padding:20px;overflow-y:auto}
.sprite-display{display:flex;gap:20px;align-items:flex-start;margin-bottom:16px}
.sprite-box{text-align:center}
.sprite-box label{display:block;font-size:11px;color:#606080;margin-bottom:4px}
.sprite-img{image-rendering:pixelated;border:1px solid #333;background:repeating-conic-gradient(#252535 0% 25%,#1a1a2e 0% 50%) 0 0/16px 16px}
.rubric{background:#16213e;border:1px solid #0f3460;padding:12px;width:460px;margin-bottom:12px;font-size:12px}
.rubric h3{margin:0 0 8px;font-size:13px}
.score-bar{display:flex;align-items:center;gap:8px;margin:3px 0}
.score-label{width:140px;color:#a0a0c0}
.score-val{width:30px;text-align:right;font-weight:bold}
.bar{height:8px;background:#0f3460;flex:1;border-radius:2px}
.bar-fill{height:100%;border-radius:2px;background:#4caf50}
.bar-fill.warn{background:#ff9800}
.bar-fill.bad{background:#f44336}
.failures{color:#f44336;font-size:11px;margin-top:6px}
.meta{font-size:11px;color:#606080;margin-bottom:12px;text-align:center}
.controls{display:flex;gap:10px;margin-bottom:12px}
btn.act{padding:10px 24px;font-size:14px;font-family:monospace;border:none;cursor:pointer;border-radius:3px;font-weight:bold}
.accept{background:#2e7d32;color:#fff}.accept:hover{background:#43a047}
.reject{background:#c62828;color:#fff}.reject:hover{background:#e53935}
.flag{background:#e65100;color:#fff}.flag:hover{background:#fb8c00}
.skip{background:#37474f;color:#fff}.skip:hover{background:#546e7a}
.notes-row{display:flex;gap:8px;align-items:center;margin-bottom:8px}
.notes-row input{flex:1;background:#16213e;border:1px solid #0f3460;color:#e0e0e0;padding:6px;font-family:monospace;font-size:12px}
.progress{font-size:12px;color:#a0a0c0;margin-bottom:8px}
.anomaly-tag{display:inline-block;background:#4a148c;color:#ce93d8;padding:2px 6px;border-radius:2px;font-size:11px;margin:2px}
.empty{color:#606080;text-align:center;padding:40px}
</style>
</head>
<body>
<div class="header">
  <h1>AM Pixel — Golden Dataset Curation</h1>
  <div class="stats" id="hdr-stats">Loading...</div>
</div>
<div class="main">
  <div class="sidebar">
    <h3>Buckets</h3>
    <button class="bucket-btn active" data-bucket="A_autopass" onclick="selectBucket('A_autopass',this)">A — Autopass (≥85)</button>
    <button class="bucket-btn" data-bucket="B_borderline" onclick="selectBucket('B_borderline',this)">B — Borderline (70-84)</button>
    <button class="bucket-btn" data-bucket="D_anomaly" onclick="selectBucket('D_anomaly',this)">D — Anomaly</button>
    <button class="bucket-btn" data-bucket="C_autoreject" onclick="selectBucket('C_autoreject',this)">C — Autoreject (&lt;70)</button>
    <button class="bucket-btn" data-bucket="E_tileset" onclick="selectBucket('E_tileset',this)">E — Tileset</button>
    <hr style="border-color:#0f3460;margin:12px 0">
    <div id="sidebar-stats" style="font-size:11px;color:#606080"></div>
  </div>
  <div class="content">
    <div class="progress" id="progress">Loading queue...</div>
    <div id="sprite-view"><div class="empty">Run tools/run_triage_scorer.py first to populate review buckets.</div></div>
  </div>
</div>
<script>
let queue = [], idx = 0, currentBucket = 'A_autopass', currentEntry = null;

document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT') return;
  if (e.key === 'a') decide('accept');
  else if (e.key === 'r') decide('reject');
  else if (e.key === 'f') decide('flag_recalibration');
  else if (e.key === 'n') next();
});

async function selectBucket(b, btn) {
  currentBucket = b;
  document.querySelectorAll('.bucket-btn').forEach(x => x.classList.remove('active'));
  btn.classList.add('active');
  await loadQueue();
}

async function loadQueue() {
  const r = await fetch('/api/queue?bucket=' + currentBucket);
  const d = await r.json();
  queue = d.queue; idx = 0;
  document.getElementById('progress').textContent =
    `${d.reviewed} reviewed / ${d.total} total in ${currentBucket} — ${d.remaining} remaining`;
  renderSprite();
  loadStats();
}

async function loadStats() {
  const r = await fetch('/api/stats');
  const d = await r.json();
  document.getElementById('hdr-stats').textContent =
    `Golden: ${d.golden_accepted} accepted | Total scored: ${d.total_scored.toLocaleString()} | Session: ${d.session_id}`;
  let sb = '';
  for (const [b, cnt] of Object.entries(d.bucket_counts)) {
    const rem = d.bucket_remaining[b] || 0;
    sb += `<div>${b}: ${cnt} (${rem} left)</div>`;
  }
  document.getElementById('sidebar-stats').innerHTML = sb;
}

function renderSprite() {
  const view = document.getElementById('sprite-view');
  if (!queue || idx >= queue.length) {
    view.innerHTML = '<div class="empty">Queue empty — all sprites in this bucket reviewed.</div>';
    return;
  }
  const e = queue[idx]; currentEntry = e;
  const score = e.total_score;
  const ss = e.subscores || {};
  const color = score >= 85 ? '' : score >= 70 ? 'warn' : 'bad';
  const failHtml = e.primary_failure_modes && e.primary_failure_modes.length
    ? '<div class="failures">⚠ ' + e.primary_failure_modes.join(', ') + '</div>' : '';
  const anomalyHtml = e.anomaly_reasons
    ? e.anomaly_reasons.map(r => `<span class="anomaly-tag">${r}</span>`).join(' ') : '';
  const imgUrl = `/api/sprite_image?path=${encodeURIComponent(e.source_path)}`;
  view.innerHTML = `
    <div class="meta">${e.sprite_id} &nbsp;|&nbsp; ${e.sheet_dir} &nbsp;|&nbsp; Bucket: <b>${e.bucket}</b></div>
    <div class="sprite-display">
      <div class="sprite-box"><label>Native</label><img class="sprite-img" src="${imgUrl}" style="width:auto;height:auto;max-width:128px;max-height:128px"></div>
      <div class="sprite-box"><label>2× Scale</label><img class="sprite-img" src="${imgUrl}" style="width:auto;height:auto;max-width:256px;max-height:256px;transform:scale(2);transform-origin:top left;margin-bottom:calc(100% + 8px)"></div>
    </div>
    <div class="rubric">
      <h3>Rubric Score: <span style="color:${score>=85?'#4caf50':score>=70?'#ff9800':'#f44336'}">${score}/85</span></h3>
      ${scoreBar('A1 Technical', ss.A1_technical, 25)}
      ${scoreBar('A2 Construction', ss.A2_construction, 25)}
      ${scoreBar('A3 Readability', ss.A3_readability, 20)}
      ${scoreBar('A4 Animation', ss.A4_animation, 15)}
      ${failHtml}
    </div>
    ${anomalyHtml ? '<div style="margin-bottom:10px">' + anomalyHtml + '</div>' : ''}
    <div class="notes-row">
      <label style="font-size:12px;color:#a0a0c0">Notes:</label>
      <input type="text" id="notes" placeholder="Optional notes...">
    </div>
    <div class="controls">
      <button class="act accept" onclick="decide('accept')">✓ Accept (a)</button>
      <button class="act reject" onclick="decide('reject')">✗ Reject (r)</button>
      <button class="act flag" onclick="decide('flag_recalibration')">⚑ Flag (f)</button>
      <button class="act skip" onclick="next()">→ Skip (n)</button>
    </div>`;
}

function scoreBar(label, val, max) {
  const pct = max > 0 ? (val / max * 100) : 0;
  const cls = pct >= 80 ? '' : pct >= 50 ? 'warn' : 'bad';
  return `<div class="score-bar"><span class="score-label">${label}</span><span class="score-val">${val}/${max}</span><div class="bar"><div class="bar-fill ${cls}" style="width:${pct}%"></div></div></div>`;
}

async function decide(decision) {
  if (!currentEntry) return;
  const notes = document.getElementById('notes')?.value || '';
  await fetch('/api/decide', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      sprite_id: currentEntry.sprite_id,
      decision,
      notes,
      rubric_scores: currentEntry,
      bucket: currentBucket,
    })
  });
  next();
}

function next() { idx++; renderSprite(); }

loadQueue();
</script>
</body></html>"""  # noqa: E501


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5001)
    args = parser.parse_args()
    print(f"AM Pixel Curation UI — http://localhost:{args.port}")
    print(f"Session ID: {SESSION_ID}")
    print("Keyboard: a=Accept  r=Reject  f=Flag  n=Skip")
    app.run(host="0.0.0.0", port=args.port, debug=False)
