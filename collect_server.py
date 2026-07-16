"""
Prompted KWS data-collection tool. Serves a mobile-first web page that shows each
emergency word, records the speaker saying it (calm + urgent takes), auto-labels by
word, and saves 16 kHz mono WAV into <STORAGE_DIR>/<word>/ — ready for retraining.

    python collect_server.py           # local:  http(s)://127.0.0.1:7862
    gunicorn collect_server:app        # server: reads STORAGE_DIR / PORT / LANGS

Recordings -> <STORAGE_DIR>/<key>/<speaker>__<take>__<ts>.wav
Metadata   -> <STORAGE_DIR>/_manifest.csv
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
# ASCII phrases that are English MEANINGS, not pronunciations — skip these when
# choosing the romanized "how to say it" guide (so we show "kaapathunga", not "save me").
_ENGLISH_GLOSS = {
    "help", "help me", "save me", "sos", "please help", "pls help", "please",
    "doctor", "ambulance", "police", "accident", "fire", "fire accident",
    "fire service", "emergency", "earthquake", "cyclone", "help me find",
    "abuse", "violence", "stalking", "harassment", "molest", "rape", "assault", "108",
}
PROMPTS = []
for lang in LANGS:
    lex = _LEX.get(lang, {})
    for key, (phrases, st, sev, cat) in lex.items():
        native = [p for p in phrases if not p.isascii()]        # script form (target)
        roman = [p for p in phrases if p.isascii() and p.lower() not in _ENGLISH_GLOSS]
        if native:
            PROMPTS.append({"key": key, "phrase": native[0], "lang": lang,
                            "roman": roman[0] if roman else "",  # Latin pronunciation
                            "gloss": key.split("_", 1)[-1].replace("_", " "),
                            "category": cat or "help"})

# Optional SHARDING — split the phrase list across N collectors so (e.g.) 3 people
# each record a third. Set SHARD="1of3" / "2of3" / "3of3" per hosted instance.
# Round-robin (every Nth phrase), NOT a contiguous block, so each shard gets a
# balanced mix of languages and categories. Recordings from all shards merge cleanly
# on export (storage is per-phrase folder, and the shards are disjoint).
_TOTAL_PROMPTS = len(PROMPTS)
SHARD_INDEX, SHARD_TOTAL = 0, 1
_SHARD = os.environ.get("SHARD", "").lower().replace(" ", "")
if "of" in _SHARD:
    try:
        _i, _n = (int(x) for x in _SHARD.split("of"))
        if _n > 1 and 1 <= _i <= _n:
            SHARD_INDEX, SHARD_TOTAL = _i - 1, _n
            PROMPTS = [p for i, p in enumerate(PROMPTS) if i % SHARD_TOTAL == SHARD_INDEX]
    except ValueError:
        pass

app = Flask(__name__)

PAGE = r"""<!doctype html><html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#4f46e5">
<title>WUALT Voice · help build a safety device</title>
<style>
:root{
  --bg1:#eef2ff;--bg2:#f8fafc;--card:#fff;--ink:#0f172a;--sub:#64748b;--line:#e6eaf2;
  --primary:#4f46e5;--primary2:#7c6bf5;--calm:#0ea672;--calm-bg:#e7f7f0;
  --urgent:#f43f5e;--urgent-bg:#feecef;--ok:#0ea672;--shadow:0 12px 34px rgba(30,32,80,.10);
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;height:100%}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,system-ui,sans-serif;
  color:var(--ink);background:radial-gradient(120% 90% at 50% -10%,#e9ecff 0%,var(--bg2) 55%);}
.wrap{max-width:460px;margin:0 auto;min-height:100dvh;display:flex;flex-direction:column;
  padding:22px 18px calc(24px + env(safe-area-inset-bottom));}
.brand{display:flex;align-items:center;gap:9px;font-weight:800;font-size:16px;letter-spacing:-.2px}
.dot{width:24px;height:24px;border-radius:8px;background:linear-gradient(135deg,var(--primary),var(--primary2));
  box-shadow:0 4px 12px rgba(79,70,229,.35)}
.screen{display:none;flex:1;flex-direction:column}
.screen.on{display:flex;animation:in .4s cubic-bezier(.2,.7,.2,1)}
@keyframes in{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.card{background:var(--card);border:1px solid var(--line);border-radius:22px;box-shadow:var(--shadow)}
h1{font-size:25px;line-height:1.2;margin:20px 0 6px;letter-spacing:-.5px}
.lede{color:var(--sub);font-size:15px;line-height:1.5;margin:0 0 22px}
label{display:block;font-size:13px;font-weight:600;color:var(--sub);margin:16px 0 8px}
input{width:100%;font-size:16px;padding:14px 15px;border-radius:14px;border:1.5px solid var(--line);
  background:#fbfcff;color:var(--ink);outline:none;transition:border .2s}
input:focus{border-color:var(--primary)}
.chips{display:flex;gap:9px;flex-wrap:wrap}
.chip{font-size:15px;font-weight:600;padding:11px 16px;border-radius:13px;border:1.5px solid var(--line);
  background:#fbfcff;color:var(--ink);cursor:pointer;transition:.15s}
.chip.sel{border-color:var(--primary);background:#eef0ff;color:var(--primary)}
.btn{width:100%;font-size:17px;font-weight:700;padding:16px;border:none;border-radius:16px;cursor:pointer;
  color:#fff;background:linear-gradient(135deg,var(--primary),var(--primary2));
  box-shadow:0 10px 24px rgba(79,70,229,.32);transition:transform .12s,opacity .2s}
.btn:active{transform:scale(.98)}.btn:disabled{opacity:.45;box-shadow:none}
.btn.ghost{background:none;color:var(--sub);box-shadow:none;font-weight:600;font-size:15px;padding:12px}
.note{font-size:12.5px;color:#94a3b8;margin-top:14px;line-height:1.5;text-align:center}
/* recording screen */
.topbar{display:flex;align-items:center;justify-content:space-between;margin-bottom:4px}
.count{font-size:13px;font-weight:700;color:var(--sub)}
.track{height:7px;background:#e9edf6;border-radius:99px;overflow:hidden;margin:8px 0 4px}
.fill{height:100%;width:0;background:linear-gradient(90deg,var(--primary),var(--primary2));
  border-radius:99px;transition:width .4s cubic-bezier(.2,.7,.2,1)}
.wordcard{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;
  text-align:center;padding:10px 6px;gap:6px}
.cat{font-size:11px;font-weight:800;letter-spacing:1px;text-transform:uppercase;color:var(--primary);
  background:#eef0ff;padding:5px 11px;border-radius:99px}
.word{font-size:min(14vw,54px);font-weight:800;line-height:1.15;letter-spacing:-1px;margin:4px 0 2px}
.say{font-size:23px;font-weight:800;color:var(--primary);letter-spacing:.2px}
.say:before{content:"Pronounced: ";font-size:13px;font-weight:600;color:#94a3b8;letter-spacing:.2px}
.mean{font-size:15px;font-weight:700;color:var(--sub);margin-top:4px}
.mean:before{content:"Means: ";font-size:13px;font-weight:600;color:#94a3b8;letter-spacing:.2px}
.take{display:inline-flex;align-items:center;gap:8px;font-size:15px;font-weight:800;
  padding:10px 18px;border-radius:14px;margin-top:14px}
.take.calm{color:var(--calm);background:var(--calm-bg)}
.take.urgent{color:var(--urgent);background:var(--urgent-bg)}
/* record button */
.recwrap{position:relative;width:168px;height:168px;margin:22px auto 6px;display:grid;place-items:center}
.glow{position:absolute;inset:14px;border-radius:50%;background:radial-gradient(closest-side,rgba(244,63,94,.45),transparent);
  opacity:0;transform:scale(1);transition:opacity .15s}
.ring{position:absolute;inset:0;transform:rotate(-90deg)}
.ring-bg{fill:none;stroke:#e9edf6;stroke-width:7}
.ring-fg{fill:none;stroke:var(--urgent);stroke-width:7;stroke-linecap:round;stroke-dasharray:339;stroke-dashoffset:339}
.recbtn{position:relative;width:118px;height:118px;border-radius:50%;border:none;cursor:pointer;
  background:linear-gradient(135deg,var(--primary),var(--primary2));color:#fff;font-size:44px;
  box-shadow:0 14px 30px rgba(79,70,229,.4);transition:transform .12s,background .2s;display:grid;place-items:center}
.recbtn:active{transform:scale(.95)}
.recbtn.live{background:linear-gradient(135deg,var(--urgent),#fb7185);animation:pulse 1.3s ease-in-out infinite}
@keyframes pulse{0%,100%{box-shadow:0 14px 30px rgba(244,63,94,.4)}50%{box-shadow:0 14px 46px rgba(244,63,94,.65)}}
.hint{text-align:center;font-size:13.5px;color:var(--sub);height:20px;margin-top:2px}
.rowbtns{display:flex;gap:10px;margin-top:8px}
.rowbtns .btn.ghost{flex:1;border:1.5px solid var(--line);border-radius:14px}
.toast{position:fixed;left:50%;bottom:calc(26px + env(safe-area-inset-bottom));transform:translate(-50%,20px);
  background:var(--ink);color:#fff;font-size:14px;font-weight:600;padding:11px 18px;border-radius:99px;
  opacity:0;transition:.3s;pointer-events:none;box-shadow:0 8px 24px rgba(0,0,0,.25)}
.toast.show{opacity:1;transform:translate(-50%,0)}
/* done */
.hero-ok{width:96px;height:96px;border-radius:50%;background:var(--calm-bg);color:var(--calm);
  display:grid;place-items:center;font-size:52px;margin:24px auto 8px;animation:pop .5s cubic-bezier(.2,1.4,.4,1)}
@keyframes pop{from{transform:scale(.5);opacity:0}to{transform:scale(1);opacity:1}}
.center{text-align:center}
</style></head><body>
<div class="wrap">
  <div class="brand"><span class="dot"></span> WUALT Voice</div>

  <!-- WELCOME -->
  <section class="screen on" id="s-welcome">
    <h1>Your voice could help<br>protect someone else.</h1>
    <div id="shardnote" style="font-size:13px;font-weight:700;color:var(--primary);
      letter-spacing:.3px;margin:4px 0 0"></div>
    <p class="lede">Record a few emergency phrases to help train Wualt to recognise
      genuine distress across different languages and accents. It takes about 5
      minutes, and your recording stays private and is only used to improve our
      voice detection.</p>
    <div class="card" style="padding:20px">
      <label>Your name or nickname</label>
      <input id="spk" placeholder="e.g. Ravi" autocomplete="off">
      <div id="langwrap"><label>Which language will you speak?</label>
        <div class="chips" id="langchips"></div></div>
      <label>Where are you right now?</label>
      <div class="chips" id="condchips"></div>
    </div>
    <div style="flex:1"></div>
    <button class="btn" onclick="start()">Start recording</button>
    <p class="note">🎙️ Your phone will ask to use the microphone — tap Allow.</p>
  </section>

  <!-- RECORD -->
  <section class="screen" id="s-rec">
    <div class="topbar"><span class="count" id="count">0 / 0</span>
      <span class="count" id="who"></span></div>
    <div class="track"><div class="fill" id="fill"></div></div>
    <div class="wordcard">
      <span class="cat" id="cat">help</span>
      <div class="word" id="word">—</div>
      <div class="say" id="say"></div>
      <div class="mean" id="mean"></div>
      <div class="take calm" id="take">😌 Say it calmly</div>
      <div class="recwrap">
        <div class="glow" id="glow"></div>
        <svg class="ring" viewBox="0 0 120 120"><circle class="ring-bg" cx="60" cy="60" r="54"/>
          <circle class="ring-fg" id="ring" cx="60" cy="60" r="54"/></svg>
        <button class="recbtn" id="recbtn" onclick="toggle()">🎙️</button>
      </div>
      <div class="hint" id="hint">Tap the mic and say the word once. We'll stop recording automatically.</div>
    </div>
    <div class="rowbtns">
      <button class="btn ghost" onclick="redo()">↺ Redo</button>
      <button class="btn ghost" onclick="skip()">Skip ›</button>
    </div>
  </section>

  <!-- BACKGROUND -->
  <section class="screen" id="s-bg">
    <div class="wordcard">
      <span class="cat" style="color:var(--calm);background:var(--calm-bg)">last step</span>
      <div class="word" style="font-size:34px">Just talk normally</div>
      <div class="mean">Read anything or chat for ~15 seconds. This teaches it what is
        <b>not</b> an emergency — it's important.</div>
      <div class="recwrap">
        <div class="glow" id="glow2"></div>
        <svg class="ring" viewBox="0 0 120 120"><circle class="ring-bg" cx="60" cy="60" r="54"/>
          <circle class="ring-fg" id="ring2" cx="60" cy="60" r="54" style="stroke:var(--calm)"/></svg>
        <button class="recbtn" id="bgbtn" onclick="toggleBg()">🎙️</button>
      </div>
      <div class="hint" id="bghint">Tap and keep talking for 15 seconds</div>
    </div>
  </section>

  <!-- DONE -->
  <section class="screen" id="s-done">
    <div style="flex:1"></div>
    <div class="hero-ok">✓</div>
    <h1 class="center">Thank you! 🙌</h1>
    <p class="lede center">You just recorded <b id="donecount">0</b> takes. Every voice
      makes the device better at recognising a real emergency.</p>
    <div style="flex:1"></div>
    <button class="btn" onclick="location.reload()">Record another person</button>
  </section>
</div>

<div class="toast" id="toast"></div>

<script>
const CIRC = 2*Math.PI*54, DUR = 3500, BGDUR = 15000;
let allWords=[], words=[], i=0, take="calm", spk="", cond="quiet", langSel=new Set(), saved=0;
let stream, mediaRec, chunks=[], recording=false, actx, analyser, raf;

function $(id){return document.getElementById(id)}
function show(id){document.querySelectorAll('.screen').forEach(s=>s.classList.remove('on'));$(id).classList.add('on')}
function toast(t){const el=$('toast');el.textContent=t;el.classList.add('show');clearTimeout(el._t);el._t=setTimeout(()=>el.classList.remove('show'),1400)}
function buzz(ms){try{navigator.vibrate&&navigator.vibrate(ms)}catch(e){}}

async function init(){
  const r = await (await fetch('/words')).json();
  allWords = r.words;
  if(r.shards>1){ const h=document.getElementById('shardnote');
    if(h) h.textContent='Set '+r.shard+' of '+r.shards+' · '+r.count+' phrases'; }
  const langs=[...new Set(allWords.map(w=>w.lang))];
  const LN={ta:'தமிழ் Tamil',hi:'हिन्दी Hindi',en:'English'};
  const lc=$('langchips');
  if(langs.length<=1){ langSel=new Set(langs); $('langwrap').style.display='none'; }
  else langs.forEach(l=>{const b=document.createElement('button');b.className='chip';b.textContent=LN[l]||l;
    b.onclick=()=>{b.classList.toggle('sel');b.classList.contains('sel')?langSel.add(l):langSel.delete(l)};lc.appendChild(b)});
  ['quiet','a bit noisy','outdoors'].forEach((c,k)=>{const b=document.createElement('button');
    b.className='chip'+(k==0?' sel':'');b.textContent=c;b.dataset.v=['quiet','noisy','outdoor'][k];
    b.onclick=()=>{document.querySelectorAll('#condchips .chip').forEach(x=>x.classList.remove('sel'));
      b.classList.add('sel');cond=b.dataset.v};$('condchips').appendChild(b)});
}
init();

async function start(){
  spk=($('spk').value.trim())||'anon';
  if(langSel.size===0 && $('langwrap').style.display!=='none'){ toast('Pick a language first'); return; }
  words=allWords.filter(w=>langSel.size===0||langSel.has(w.lang));
  try{ stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:false}}); }
  catch(e){ alert('The microphone is needed to record. Please allow it and try again.'); return; }
  actx=new (window.AudioContext||window.webkitAudioContext)();
  analyser=actx.createAnalyser(); analyser.fftSize=256;
  actx.createMediaStreamSource(stream).connect(analyser);
  $('who').textContent=spk; show('s-rec'); render();
}
function render(){
  if(i>=words.length){ show('s-bg'); return; }
  const w=words[i];
  $('cat').textContent=w.category; $('word').textContent=w.phrase;
  const say=$('say'); if(w.roman){say.textContent=w.roman;say.style.display='block';}else{say.style.display='none';}
  $('mean').textContent=w.gloss.charAt(0).toUpperCase()+w.gloss.slice(1);
  const t=$('take'); const calm=take==='calm';
  t.className='take '+(calm?'calm':'urgent');
  t.textContent=calm?'😌 Say it calmly':'😰 Now say it URGENTLY — like it\'s real';
  const done=i*2+(calm?0:1);
  $('count').textContent=(done+1)+' / '+(words.length*2);
  $('fill').style.width=(done/(words.length*2)*100)+'%';
  resetRing('ring');
}
function meter(el){
  const d=new Uint8Array(analyser.frequencyBinCount);
  (function tick(){ analyser.getByteTimeDomainData(d);
    let s=0; for(let k=0;k<d.length;k++){const v=(d[k]-128)/128;s+=v*v;}
    const lvl=Math.min(1,Math.sqrt(s/d.length)*3.2);
    el.style.opacity=0.2+lvl*0.6; el.style.transform='scale('+(1+lvl*0.55)+')';
    raf=requestAnimationFrame(tick); })();
}
function stopMeter(el){cancelAnimationFrame(raf);el.style.opacity=0;el.style.transform='scale(1)'}
function runRing(id,dur){const r=$(id);r.style.transition='none';r.style.strokeDashoffset=CIRC;
  requestAnimationFrame(()=>{r.style.transition='stroke-dashoffset '+dur+'ms linear';r.style.strokeDashoffset=0})}
function resetRing(id){const r=$(id);r.style.transition='none';r.style.strokeDashoffset=CIRC}

function toggle(){ recording?stop():rec(); }
function rec(){
  chunks=[]; mediaRec=new MediaRecorder(stream); recording=true; buzz(25);
  if(actx.state==='suspended')actx.resume();
  $('recbtn').classList.add('live'); $('recbtn').textContent='■'; $('hint').textContent='Listening…';
  meter($('glow')); runRing('ring',DUR);
  mediaRec.ondataavailable=e=>chunks.push(e.data);
  mediaRec.onstop=()=>upload(new Blob(chunks,{type:'audio/webm'}));
  mediaRec.start(); clearTimeout(window._st); window._st=setTimeout(()=>{if(recording)stop()},DUR);
}
function stop(){ recording=false; buzz(15); clearTimeout(window._st);
  $('recbtn').classList.remove('live'); $('recbtn').textContent='🎙️'; $('hint').textContent='Saving…';
  stopMeter($('glow')); resetRing('ring'); if(mediaRec&&mediaRec.state!=='inactive')mediaRec.stop(); }
async function upload(blob){
  const w=words[i];
  const fd=new FormData(); fd.append('audio',blob,'a.webm');
  fd.append('key',w.key); fd.append('category',w.category);
  fd.append('speaker',spk); fd.append('condition',cond); fd.append('take',take);
  try{ await fetch('/save',{method:'POST',body:fd}); saved++; }catch(e){}
  toast(take==='calm'?'✓ calm take saved':'✓ urgent take saved');
  $('hint').textContent="Tap the mic and say the word once. We'll stop recording automatically.";
  if(take==='calm') take='urgent'; else { take='calm'; i++; }
  render();
}
function redo(){ if(recording)return; if(take==='urgent')take='calm'; else if(i>0){i--;take='urgent';} render(); toast('Redo this take'); }
function skip(){ if(recording)return; take='calm'; i++; render(); }

// background
function toggleBg(){
  if(recording){ recording=false; clearTimeout(window._bt); $('bgbtn').classList.remove('live'); $('bgbtn').textContent='🎙️';
    stopMeter($('glow2')); resetRing('ring2'); mediaRec.stop(); return; }
  chunks=[]; mediaRec=new MediaRecorder(stream); recording=true; buzz(25);
  $('bgbtn').classList.add('live'); $('bgbtn').textContent='■'; $('bghint').textContent='Keep talking…';
  meter($('glow2')); runRing('ring2',BGDUR);
  mediaRec.ondataavailable=e=>chunks.push(e.data);
  mediaRec.onstop=async()=>{ const fd=new FormData(); fd.append('audio',new Blob(chunks,{type:'audio/webm'}),'a.webm');
    fd.append('key','_background'); fd.append('category','_background'); fd.append('speaker',spk);
    fd.append('condition',cond); fd.append('take','conversation');
    try{ await fetch('/save',{method:'POST',body:fd}); saved++; }catch(e){}
    $('donecount').textContent=saved; show('s-done'); buzz([30,60,30]); };
  mediaRec.start(); window._bt=setTimeout(()=>{if(recording)toggleBg()},BGDUR);
}
</script></body></html>"""


@app.route("/")
def index():
    return Response(PAGE, mimetype="text/html")


@app.route("/words")
def words():
    return jsonify({"words": PROMPTS, "shard": SHARD_INDEX + 1, "shards": SHARD_TOTAL,
                    "count": len(PROMPTS), "total": _TOTAL_PROMPTS})


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
    per_phrase = {}
    for d in REC.iterdir():
        if d.is_dir():
            n = len(list(d.glob("*.wav"))) + len(list(d.glob("*.webm")))
            if n:
                per_phrase[d.name] = n
    per_person, recent = {}, []
    if MANIFEST.exists():
        with open(MANIFEST, encoding="utf-8") as m:
            rows = [r for r in csv.DictReader(m)]
        for r in rows:
            spk = r.get("speaker", "anon")
            per_person[spk] = per_person.get(spk, 0) + 1
        for r in reversed(rows[-30:]):          # last 30 entries, newest first
            ts = str(r.get("ts", ""))
            when = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(int(ts) / 1000)) if ts.isdigit() else ts
            recent.append({"person": r.get("speaker"), "phrase": r.get("key"),
                           "take": r.get("take"), "condition": r.get("condition"), "when": when})
    return jsonify({
        "people": len(per_person),
        "recordings": sum(per_phrase.values()),
        "phrases_covered": f"{len(per_phrase)}/{_TOTAL_PROMPTS}",
        "per_person": dict(sorted(per_person.items(), key=lambda x: -x[1])),
        "per_phrase": per_phrase,
        "recent": recent,
    })


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
