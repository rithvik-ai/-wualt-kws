"""
Prompted KWS data-collection tool. Runs a local web page that shows each emergency
word, records the speaker saying it (calm + urgent takes), auto-labels by word, and
saves 16 kHz mono WAV into kws_recordings/<word>/ — ready for the retraining pipeline.
Audio never leaves this machine.

    python collect_server.py           # then open http://127.0.0.1:7862

Recordings -> Desktop/audio model/kws_recordings/<key>/<speaker>__<take>__<ts>.wav
Metadata   -> kws_recordings/_manifest.csv
"""
from __future__ import annotations
import csv
import subprocess
import time
from pathlib import Path

import os
import shutil

import imageio_ffmpeg
from flask import Flask, jsonify, request, Response

from tamil_keywords import TAMIL_EMERGENCY_RAW
try:
    from hindi_keywords import HINDI_EMERGENCY_RAW
except Exception:
    HINDI_EMERGENCY_RAW = {}

HERE = Path(__file__).resolve().parent
# Config from env so the same app runs locally and on a server.
#   STORAGE_DIR  -> where recordings + manifest live (a persistent disk on a server)
#   PORT         -> listen port (platforms inject this)
#   LANGS        -> comma list of lexicons to prompt: "ta", "hi", or "ta,hi"
REC = Path(os.environ.get("STORAGE_DIR", str(HERE / "kws_recordings")))
REC.mkdir(parents=True, exist_ok=True)
MANIFEST = REC / "_manifest.csv"
# ffmpeg: prefer a system binary (present in the Docker image); fall back to the
# pip-bundled one for local runs.
FFMPEG = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()
PORT = int(os.environ.get("PORT", "7862"))
LANGS = [x.strip() for x in os.environ.get("LANGS", "ta").split(",") if x.strip()]

_LEX = {"ta": TAMIL_EMERGENCY_RAW, "hi": HINDI_EMERGENCY_RAW}
PROMPTS = []
for lang in LANGS:
    lex = _LEX.get(lang, {})
    for key, (phrases, st, sev, cat) in lex.items():
        native = [p for p in phrases if not p.isascii()]   # script forms only
        if native:
            PROMPTS.append({"key": key, "phrase": native[0], "lang": lang,
                            "gloss": key.split("_", 1)[-1].replace("_", " "),
                            "category": cat or "help"})

app = Flask(__name__)

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WUALT KWS Collection</title><style>
body{font-family:system-ui,Segoe UI,Arial;max-width:640px;margin:0 auto;padding:18px;background:#0f1420;color:#e8ecf3}
h1{font-size:20px;color:#7fb2ff}.card{background:#182236;border-radius:14px;padding:22px;margin:14px 0}
input,select,button{font-size:16px;padding:10px;border-radius:9px;border:1px solid #33415e;background:#0f1420;color:#e8ecf3}
button{cursor:pointer;background:#2d5bd7;border:none;font-weight:600}button:disabled{opacity:.4}
.rec{background:#d7392d}.big{font-size:44px;font-weight:700;margin:6px 0;color:#fff}
.gloss{color:#9fb0cf}.take{font-size:15px;letter-spacing:.5px;text-transform:uppercase;margin:10px 0}
.calm{color:#7fd6a0}.urgent{color:#ff9a6b}.bar{height:8px;background:#26314a;border-radius:6px;overflow:hidden;margin:10px 0}
.fill{height:100%;background:#2d5bd7;width:0%}.small{font-size:13px;color:#8394b3}.ok{color:#7fd6a0}
</style></head><body>
<h1>WUALT — emergency word collection</h1>
<div class="card" id="setup">
  <div>Your name / ID <input id="spk" placeholder="e.g. ravi" style="width:60%"></div>
  <div style="margin-top:10px">Environment
    <select id="cond"><option>quiet</option><option>noisy</option><option>outdoor</option></select></div>
  <div style="margin-top:14px"><button onclick="start()">Start recording session</button></div>
  <div class="small" style="margin-top:8px">Mic permission will be requested. Each word: one CALM take, one URGENT take.</div>
</div>
<div class="card" id="rec" style="display:none">
  <div class="small"><span id="prog">0/0</span> &middot; speaker <b id="spkn"></b></div>
  <div class="bar"><div class="fill" id="fill"></div></div>
  <div class="big" id="word">—</div>
  <div class="gloss" id="gloss"></div>
  <div class="take" id="take"></div>
  <div style="margin-top:10px">
    <button id="recbtn" onclick="toggle()">● Record</button>
    <button id="redo" onclick="redo()" disabled>Redo last</button>
  </div>
  <div class="small ok" id="status" style="margin-top:10px"></div>
</div>
<div class="card" id="bg" style="display:none">
  <div class="big">Background</div>
  <div class="gloss">Now just talk normally / read anything for ~15 seconds (this teaches it what is NOT an emergency).</div>
  <div style="margin-top:12px"><button id="bgbtn" onclick="toggleBg()">● Record background</button></div>
  <div class="small ok" id="bgstatus" style="margin-top:10px"></div>
</div>
<div class="card" id="done" style="display:none"><div class="big ok">✓ Done — thank you!</div>
  <div class="gloss">Recordings saved. Hand the device to the next person and press Start again.</div>
  <button onclick="location.reload()" style="margin-top:12px">Next person</button></div>
<script>
let words=[], i=0, take="calm", spk="", cond="", mediaRec, chunks=[], stream, recording=false, lastKey="";
async function start(){
  spk=document.getElementById('spk').value.trim()||'anon';
  cond=document.getElementById('cond').value;
  try{ stream=await navigator.mediaDevices.getUserMedia({audio:true}); }
  catch(e){ alert('Microphone permission needed: '+e); return; }
  words=await (await fetch('/words')).json();
  document.getElementById('setup').style.display='none';
  document.getElementById('rec').style.display='block';
  document.getElementById('spkn').textContent=spk;
  show();
}
function show(){
  if(i>=words.length){ document.getElementById('rec').style.display='none'; document.getElementById('bg').style.display='block'; return; }
  const w=words[i];
  document.getElementById('word').textContent=w.phrase;
  document.getElementById('gloss').textContent='(“'+w.gloss+'” · '+w.category+')';
  const t=document.getElementById('take');
  t.textContent = take==='calm' ? 'Say it CALMLY' : 'Say it URGENTLY — like a real emergency';
  t.className='take '+(take==='calm'?'calm':'urgent');
  document.getElementById('prog').textContent=(i*2+(take==='urgent'?1:0))+'/'+(words.length*2);
  document.getElementById('fill').style.width=((i*2+(take==='urgent'?1:0))/(words.length*2)*100)+'%';
}
function toggle(){ recording?stop():rec(); }
function rec(){
  chunks=[]; mediaRec=new MediaRecorder(stream); recording=true;
  document.getElementById('recbtn').textContent='■ Stop'; document.getElementById('recbtn').classList.add('rec');
  mediaRec.ondataavailable=e=>chunks.push(e.data);
  mediaRec.onstop=()=>upload(new Blob(chunks,{type:'audio/webm'}));
  mediaRec.start();
  setTimeout(()=>{ if(recording) stop(); }, 3500); // auto-stop safety
}
function stop(){ recording=false; document.getElementById('recbtn').textContent='● Record';
  document.getElementById('recbtn').classList.remove('rec'); if(mediaRec&&mediaRec.state!=='inactive')mediaRec.stop(); }
async function upload(blob){
  const w=words[i]; lastKey=w.key;
  const fd=new FormData(); fd.append('audio',blob,'a.webm');
  fd.append('key',w.key); fd.append('category',w.category);
  fd.append('speaker',spk); fd.append('condition',cond); fd.append('take',take);
  document.getElementById('status').textContent='saving…';
  await fetch('/save',{method:'POST',body:fd});
  document.getElementById('status').textContent='✓ saved '+w.phrase+' ('+take+')';
  document.getElementById('redo').disabled=false;
  if(take==='calm'){ take='urgent'; } else { take='calm'; i++; }
  show();
}
function redo(){ if(take==='urgent'){take='calm';} else {take='urgent'; i--;} show();
  document.getElementById('status').textContent='redo — record again'; }
async function toggleBg(){
  const b=document.getElementById('bgbtn');
  if(recording){ recording=false; b.textContent='● Record background'; b.classList.remove('rec'); mediaRec.stop(); return; }
  chunks=[]; mediaRec=new MediaRecorder(stream); recording=true; b.textContent='■ Stop'; b.classList.add('rec');
  mediaRec.ondataavailable=e=>chunks.push(e.data);
  mediaRec.onstop=async()=>{ const fd=new FormData(); fd.append('audio',new Blob(chunks,{type:'audio/webm'}),'a.webm');
    fd.append('key','_background'); fd.append('category','_background'); fd.append('speaker',spk);
    fd.append('condition',cond); fd.append('take','conversation');
    await fetch('/save',{method:'POST',body:fd});
    document.getElementById('bg').style.display='none'; document.getElementById('done').style.display='block'; };
  mediaRec.start(); setTimeout(()=>{ if(recording) toggleBg(); }, 15000);
}
</script></body></html>"""


@app.route("/")
def index():
    return Response(PAGE, mimetype="text/html")


@app.route("/words")
def words():
    return jsonify(PROMPTS)


@app.route("/save", methods=["POST"])
def save():
    f = request.files["audio"]
    key = request.form.get("key", "unknown")
    speaker = "".join(c for c in request.form.get("speaker", "anon") if c.isalnum()) or "anon"
    cond = request.form.get("condition", "quiet")
    take = request.form.get("take", "calm")
    category = request.form.get("category", "")
    folder = REC / key
    folder.mkdir(exist_ok=True)
    ts = int(time.time() * 1000)
    raw = folder / f"{speaker}__{take}__{ts}.webm"
    f.save(str(raw))
    wav = raw.with_suffix(".wav")
    try:
        subprocess.run([FFMPEG, "-y", "-i", str(raw), "-ar", "16000", "-ac", "1", str(wav)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        raw.unlink(missing_ok=True)
        out = wav.name
    except Exception:
        out = raw.name                      # keep webm if conversion fails
    new = not MANIFEST.exists()
    with open(MANIFEST, "a", newline="", encoding="utf-8") as m:
        w = csv.writer(m)
        if new:
            w.writerow(["speaker", "key", "category", "condition", "take", "file", "ts"])
        w.writerow([speaker, key, category, cond, take, out, ts])
    return jsonify({"ok": True, "file": out})


@app.route("/stats")
def stats():
    counts = {}
    for d in REC.iterdir():
        if d.is_dir():
            counts[d.name] = len(list(d.glob("*.wav")))
    return jsonify({"total_wavs": sum(counts.values()), "per_word": counts})


@app.route("/export")
def export():
    """Download all recordings + manifest as a zip. Token-gated: set EXPORT_TOKEN
    in the environment, then GET /export?token=<that>. Disabled if unset."""
    import io
    import zipfile
    token = os.environ.get("EXPORT_TOKEN")
    if not token or request.args.get("token") != token:
        return Response("forbidden", status=403)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in REC.rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(REC))
    buf.seek(0)
    return Response(buf.read(), mimetype="application/zip",
                    headers={"Content-Disposition": "attachment; filename=kws_recordings.zip"})


if __name__ == "__main__":
    print(f"KWS collection -> {REC}")
    cert, key = HERE / "kws_cert.pem", HERE / "kws_key.pem"
    if cert.exists() and key.exists():
        # HTTPS on the LAN so phones can use the mic (browsers require a secure
        # origin for getUserMedia). Phones on the same wifi open
        # https://<this-machine's-IP>:7862 and accept the self-signed-cert warning.
        print(f"HTTPS mode: open https://127.0.0.1:{PORT} here, or "
              f"https://<LAN-IP>:{PORT} from a phone on the same wifi")
        app.run(host="0.0.0.0", port=PORT, debug=False,
                ssl_context=(str(cert), str(key)))
    else:
        print(f"HTTP localhost-only: http://127.0.0.1:{PORT} (run make_cert.py for phone access)")
        app.run(host="127.0.0.1", port=PORT, debug=False)
