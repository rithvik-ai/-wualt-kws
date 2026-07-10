# WUALT KWS Collection — Render deploy

A tiny always-on web app: people open the URL, record the emergency words, and
every clip is stored (16 kHz WAV, auto-labeled) on a **persistent disk in the
backend**. No ML, no server admin.

## Deploy on Render (one blueprint)

1. **Put this folder on GitHub** (a fresh repo — this folder only, not the whole
   ML project):
   ```
   cd kws_deploy
   git init && git add . && git commit -m "kws collection server"
   # create an empty repo on github.com, then:
   git remote add origin https://github.com/<you>/wualt-kws.git
   git branch -M main && git push -u origin main
   ```

2. **Render → New + → Blueprint** → connect the repo. Render reads `render.yaml`
   and provisions:
   - the web service (Docker),
   - a **1 GB persistent disk mounted at `/data`** (holds all recordings),
   - `EXPORT_TOKEN` (a generated secret),
   - HTTPS + a stable `https://wualt-kws-collect.onrender.com` URL.

   Click **Apply**. First build ~2–3 min.

3. **Share the URL.** Any phone/laptop, anywhere, opens it and records. Real
   HTTPS = mic works with no warnings.

## Where the data lives
`/data/<word>/<speaker>__<take>__<ts>.wav` + `/data/_manifest.csv`, on the
Render persistent disk. It survives restarts and redeploys.

- **Live counts:** `https://<app>.onrender.com/stats`
- **Download everything** (for retraining):
  `https://<app>.onrender.com/export?token=<EXPORT_TOKEN>`
  (find the token in Render → your service → Environment). Save the zip, unzip
  into `audio model/kws_recordings/`, run `python retrain_kws_real.py`.

## Cost / notes
- **Starter plan (~$7/mo)** is required — it's always-on AND supports the disk.
  The free plan spins down after inactivity and has **no persistent disk**, so
  recordings would be lost.
- Prompts default to Tamil + Hindi (`LANGS=ta,hi`). Set `LANGS=ta` or `hi` in the
  Render Environment tab for one language.
- To grow storage, raise `sizeGB` in `render.yaml` (or the disk size in the
  dashboard).
