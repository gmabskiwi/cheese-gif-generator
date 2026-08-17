"""Render trait-tracker/dashboard.html (interactive) from traits.json.

The page bakes the canonical state in, then layers browser-local edits on
top (checkboxes, uploaded reference images, newly added traits — all kept
in localStorage). The Sync button exports a trait-tracker-update.json the
user drops back in chat; ingest_update.py merges it into traits.json.

Reference images are alpha-cropped (trait layers are mostly empty canvas)
and embedded as data URIs. Output is an HTML fragment for publishing as a
claude.ai Artifact (no <html>/<head>/<body> wrapper).
"""
import base64
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "traits.json")
OUT = os.path.join(HERE, "dashboard.html")

THUMB = 480  # max px for embedded art
PAD = 24     # px padding kept around the alpha-cropped art


def image_data_uri(relpath, crop=False):
    path = os.path.join(HERE, relpath)
    try:
        from PIL import Image
        img = Image.open(path).convert("RGBA")
        if crop:
            bbox = img.split()[3].getbbox()
            if bbox:
                l, t, r, b = bbox
                bbox = (max(0, l - PAD), max(0, t - PAD),
                        min(img.width, r + PAD), min(img.height, b + PAD))
                img = img.crop(bbox)
        img.thumbnail((THUMB, THUMB))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data = buf.getvalue()
    except Exception:
        with open(path, "rb") as fh:
            data = fh.read()
    return "data:image/png;base64," + base64.b64encode(data).decode()


def render():
    with open(STATE) as fh:
        state = json.load(fh)

    baked = {"updated": state["updated"], "traits": []}
    for t in state["traits"]:
        bt = {
            "category": t["category"],
            "name": t["name"],
            "reference": image_data_uri(t["reference"], crop=True) if t.get("reference") else None,
            "variants": [],
        }
        for v in t["variants"]:
            bt["variants"].append({
                "gender": v["gender"], "skin": v["skin"],
                "sent": bool(v.get("sent")), "uploaded": bool(v.get("uploaded")),
                "image": image_data_uri(v["image"], crop=True) if v.get("image") else None,
            })
        baked["traits"].append(bt)

    total = sum(len(t["variants"]) for t in baked["traits"])
    uploaded = sum(1 for t in baked["traits"] for v in t["variants"] if v["uploaded"])

    baked_json = json.dumps(baked).replace("</", "<\\/")

    html = HTML_TEMPLATE.replace("__BAKED__", baked_json)
    with open(OUT, "w") as fh:
        fh.write(html)
    print(f"dashboard.html written — {uploaded}/{total} uploaded (baked state)")


HTML_TEMPLATE = r'''<title>Trait Tracker</title>
<style>
  :root {
    --ink: #0E1116; --panel: #141922; --card: #12161D; --line: #242C38;
    --text: #F2F5F9; --muted: #8C95A4; --amber: #FFB525;
    --ok: #3DDC97; --todo: #F87171;
    --mono: ui-monospace, "SF Mono", "Cascadia Mono", Menlo, Consolas, monospace;
  }
  * { box-sizing: border-box; }
  body {
    background: var(--ink); color: var(--text); margin: 0;
    font: 16px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  .wrap { max-width: 1060px; margin: 0 auto; padding: 44px 24px 72px; }

  .eyebrow {
    font: 700 11px/1 var(--mono); letter-spacing: .22em; color: var(--amber);
    text-transform: uppercase; margin: 0 0 12px;
  }
  h1 {
    font-size: clamp(34px, 6vw, 52px); font-weight: 800; letter-spacing: -.02em;
    line-height: 1.02; margin: 0 0 10px; text-wrap: balance;
  }
  .sub { color: var(--muted); margin: 0 0 22px; max-width: 60ch; }

  .toolbar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 26px; }
  .btn {
    font: 800 12px/1 var(--mono); letter-spacing: .1em; text-transform: uppercase;
    background: var(--amber); color: var(--ink); border: 0; border-radius: 8px;
    padding: 12px 16px; cursor: pointer;
  }
  .btn.ghost { background: transparent; color: var(--amber); border: 1px solid color-mix(in srgb, var(--amber) 55%, transparent); }
  .btn:focus-visible, .check:focus-visible, .ref-up:focus-visible { outline: 2px solid var(--amber); outline-offset: 2px; }
  .unsynced { font: 600 11px/1.4 var(--mono); color: var(--muted); display: none; }
  .unsynced.on { display: inline-flex; align-items: center; gap: 7px; }
  .unsynced i { width: 8px; height: 8px; border-radius: 50%; background: var(--amber); display: inline-block; }

  .form {
    display: none; background: var(--panel); border: 1px solid var(--line);
    border-radius: 14px; padding: 20px; margin-bottom: 26px;
  }
  .form.open { display: block; }
  .form h3 { margin: 0 0 14px; font-size: 15px; }
  .frow { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }
  .frow input[type=text] {
    flex: 1; min-width: 160px; background: var(--card); border: 1px solid var(--line);
    border-radius: 8px; color: var(--text); font: 500 14px/1 inherit; padding: 12px;
  }
  .flabel { font: 700 10px/1 var(--mono); letter-spacing: .16em; text-transform: uppercase;
    color: var(--muted); display: block; margin-bottom: 8px; }
  .vgrid { display: grid; grid-template-columns: repeat(3, minmax(110px, 160px)); gap: 8px; margin-bottom: 14px; }
  .vopt {
    display: flex; align-items: center; gap: 8px; background: var(--card);
    border: 1px solid var(--line); border-radius: 8px; padding: 9px 10px;
    font: 600 12px/1 var(--mono); cursor: pointer; user-select: none;
  }
  .vopt input { accent-color: var(--amber); margin: 0; }
  .fref { margin-bottom: 16px; }
  .fref input { color: var(--muted); font: 500 12px/1 var(--mono); }

  .stats {
    display: grid; grid-template-columns: repeat(4, minmax(110px, 1fr)) 2fr;
    gap: 10px; margin-bottom: 40px;
  }
  .stat {
    background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
    padding: 14px 16px 12px;
  }
  .stat b {
    display: block; font-size: 30px; font-weight: 800; line-height: 1.1;
    font-variant-numeric: tabular-nums;
  }
  .stat span {
    font: 700 10px/1 var(--mono); letter-spacing: .16em; color: var(--muted);
    text-transform: uppercase;
  }
  .stat.done b { color: var(--ok); }
  .stat.todo b { color: var(--todo); }
  .stat.pct b { color: var(--amber); }
  .stat.bar { display: flex; flex-direction: column; justify-content: center; gap: 10px; }
  .track { height: 10px; background: var(--line); border-radius: 5px; overflow: hidden; }
  .fill { height: 100%; background: var(--amber); border-radius: 5px; }

  .card {
    background: var(--card); border: 1px solid var(--line); border-radius: 14px;
    padding: 22px 22px 24px; margin-bottom: 18px;
  }
  .card.complete { border-color: color-mix(in srgb, var(--ok) 45%, var(--line)); }
  .card-head {
    display: flex; align-items: baseline; justify-content: space-between;
    gap: 16px; margin-bottom: 16px;
  }
  .cat {
    display: inline-block; font: 700 10px/1 var(--mono); letter-spacing: .18em;
    text-transform: uppercase; color: var(--amber);
    border: 1px solid color-mix(in srgb, var(--amber) 45%, transparent);
    border-radius: 4px; padding: 4px 7px; margin-bottom: 8px;
  }
  .card-id h2 { margin: 0; font-size: 23px; font-weight: 800; letter-spacing: -.01em; }
  .count {
    font: 800 22px/1 var(--mono); font-variant-numeric: tabular-nums; white-space: nowrap;
  }
  .count em { font-style: normal; color: var(--muted); padding: 0 2px; }
  .card.complete .count { color: var(--ok); }

  .card-body { display: flex; gap: 18px; align-items: flex-start; }
  .ref { margin: 0; flex: 0 0 190px; display: flex; flex-direction: column; gap: 8px; }
  .ref figcaption {
    font: 700 10px/1 var(--mono); letter-spacing: .18em; text-transform: uppercase;
    color: var(--amber);
  }
  .ref img, .ref-slot {
    width: 100%; aspect-ratio: 1; border-radius: 10px; object-fit: contain;
    background: var(--panel);
    border: 1px solid color-mix(in srgb, var(--amber) 40%, var(--line));
  }
  .ref-slot {
    border-style: dashed; display: flex; align-items: center; justify-content: center;
  }
  .ref-slot span { font: 500 11px/1.4 var(--mono); color: var(--muted); text-align: center;
    padding: 0 14px; }
  .ref-up {
    font: 700 10px/1 var(--mono); letter-spacing: .12em; text-transform: uppercase;
    color: var(--muted); background: none; border: 1px dashed var(--line);
    border-radius: 6px; padding: 8px; cursor: pointer;
  }
  .ref-up:hover { color: var(--amber); border-color: var(--amber); }

  .tiles {
    flex: 1; display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
    gap: 12px;
  }
  .tile {
    display: flex; flex-direction: column; gap: 10px;
    background: var(--panel); border: 1px solid var(--line); border-radius: 11px;
    padding: 10px;
  }
  .tile.done { border-color: color-mix(in srgb, var(--ok) 55%, var(--line)); }
  .badges { display: flex; align-items: center; gap: 5px; flex-wrap: wrap; }
  .badge {
    font: 800 10px/1 var(--mono); letter-spacing: .1em; text-transform: uppercase;
    border-radius: 4px; padding: 5px 7px;
  }
  .badge.gender { background: #2A3240; color: var(--text); }
  .badge.skin {
    background: #1C222C; color: var(--text);
    display: inline-flex; align-items: center; gap: 5px;
  }
  .badge.skin i {
    width: 10px; height: 10px; border-radius: 50%; display: inline-block;
    border: 1px solid #00000055;
  }
  .checks { display: flex; gap: 8px; }
  .check {
    font: 800 10px/1 var(--mono); letter-spacing: .1em; text-transform: uppercase;
    border-radius: 5px; padding: 8px 6px; flex: 1; cursor: pointer; border: 1px solid var(--line);
    background: var(--card); color: var(--muted); text-align: center; white-space: nowrap;
  }
  .check.sent.on { background: color-mix(in srgb, var(--amber) 22%, transparent); color: var(--amber);
    border-color: color-mix(in srgb, var(--amber) 55%, transparent); }
  .check.up.on { background: var(--ok); color: var(--ink); border-color: var(--ok); }
  .art { border-radius: 7px; overflow: hidden; background: var(--card); border: 1px solid var(--line); }
  .art img { width: 100%; display: block; }

  dialog {
    background: var(--panel); color: var(--text); border: 1px solid var(--line);
    border-radius: 14px; padding: 22px; max-width: 520px; width: 90vw;
  }
  dialog::backdrop { background: #000A; }
  dialog textarea {
    width: 100%; height: 180px; background: var(--card); color: var(--text);
    border: 1px solid var(--line); border-radius: 8px; font: 500 11px/1.5 var(--mono); padding: 10px;
  }

  footer {
    margin-top: 44px; padding-top: 18px; border-top: 1px solid var(--line);
    color: var(--muted); font: 500 12px/1.6 var(--mono);
  }
  @media (max-width: 640px) {
    .stats { grid-template-columns: repeat(2, 1fr); }
    .stat.bar { grid-column: 1 / -1; }
    .card-body { flex-direction: column; }
    .ref { flex-basis: auto; width: 100%; max-width: 240px; }
    .vgrid { grid-template-columns: repeat(2, 1fr); }
  }
</style>
<div class="wrap">
  <p class="eyebrow">NFT Collection · Art Progress</p>
  <h1>Trait Tracker</h1>
  <p class="sub">Tap <strong>sent</strong> when the art goes out, <strong>uploaded</strong> when
  it's in the collection. Add traits and reference images right here, then hit
  <strong>Sync</strong> to publish your changes for the whole team.</p>

  <div class="toolbar">
    <button class="btn" id="addBtn" type="button">+ Add trait</button>
    <button class="btn ghost" id="syncBtn" type="button">Sync changes</button>
    <span class="unsynced" id="unsynced"><i></i>changes saved on this device — sync to publish</span>
  </div>

  <form class="form" id="addForm">
    <h3>New trait</h3>
    <div class="frow">
      <input type="text" id="fCat" placeholder="Category (e.g. Left Arm)" list="catList" required>
      <input type="text" id="fName" placeholder="Trait name (e.g. Rolex)" required>
      <datalist id="catList"></datalist>
    </div>
    <span class="flabel">Versions needed</span>
    <div class="vgrid" id="vGrid"></div>
    <div class="fref">
      <span class="flabel">Reference image (optional)</span>
      <input type="file" id="fRef" accept="image/*">
    </div>
    <div class="frow">
      <button class="btn" type="submit">Add to tracker</button>
      <button class="btn ghost" type="button" id="cancelAdd">Cancel</button>
    </div>
  </form>

  <div class="stats" id="stats"></div>
  <div id="cards"></div>

  <footer>Checkbox and image changes save instantly on this device.
  <strong>Sync</strong> downloads a small update file — drop it in chat with
  Claude and this page updates at the same link for everyone.</footer>
</div>

<dialog id="syncDlg">
  <h3 style="margin:0 0 10px">Sync your changes</h3>
  <p style="color:var(--muted);font-size:13px;margin:0 0 12px">Copy this update and
  paste it in chat with Claude — the page then refreshes at this same link
  for everyone.</p>
  <textarea id="syncText" readonly></textarea>
  <div style="display:flex;gap:10px;margin-top:12px;align-items:center">
    <button class="btn" id="copyBtn" type="button">Copy update</button>
    <button class="btn ghost" id="closeDlg" type="button">Close</button>
    <span id="copiedNote" style="display:none;color:var(--ok);font:700 11px/1 var(--mono)">copied ✓</span>
  </div>
</dialog>

<script>
(function () {
  "use strict";
  var BAKED = __BAKED__;
  var KEY = "trait-tracker-v1";
  var GENDERS = ["Male", "Female"];
  var SKINS = ["White", "Tanned", "Brown"];
  var TONES = { White: "#F3D8C2", Tanned: "#D9A468", Brown: "#8D5B35" };

  function loadOverlay() {
    try {
      var o = JSON.parse(localStorage.getItem(KEY) || "{}");
      return { variants: o.variants || {}, refs: o.refs || {}, added: o.added || [] };
    } catch (e) { return { variants: {}, refs: {}, added: [] }; }
  }
  var overlay = loadOverlay();

  function saveOverlay() {
    try { localStorage.setItem(KEY, JSON.stringify(overlay)); }
    catch (e) { alert("Couldn't save locally (storage full). Sync your changes now so nothing is lost."); }
  }
  function tid(t) { return (t.category + "|" + t.name).toLowerCase(); }
  function vid(t, v) { return tid(t) + "|" + (v.gender + "|" + v.skin).toLowerCase(); }
  function hasLocal() {
    return overlay.added.length > 0 || Object.keys(overlay.refs).length > 0 ||
      Object.keys(overlay.variants).length > 0;
  }

  function merged() {
    var traits = BAKED.traits.map(function (t) {
      return {
        category: t.category, name: t.name, reference: t.reference,
        variants: t.variants.map(function (v) {
          return { gender: v.gender, skin: v.skin, sent: v.sent, uploaded: v.uploaded, image: v.image };
        })
      };
    });
    var ids = {};
    traits.forEach(function (t) { ids[tid(t)] = true; });
    overlay.added.forEach(function (t) { if (!ids[tid(t)]) { traits.push(t); ids[tid(t)] = true; } });
    traits.forEach(function (t) {
      if (overlay.refs[tid(t)]) t.reference = overlay.refs[tid(t)];
      t.variants.forEach(function (v) {
        var o = overlay.variants[vid(t, v)];
        if (o) { v.sent = !!o.sent; v.uploaded = !!o.uploaded; }
      });
    });
    return traits;
  }

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function render() {
    var traits = merged();
    var all = [], sent = 0, up = 0;
    traits.forEach(function (t) { t.variants.forEach(function (v) { all.push(v); if (v.sent) sent++; if (v.uploaded) up++; }); });
    var total = all.length;
    var pct = total ? Math.round(100 * up / total) : 0;

    var stats = document.getElementById("stats");
    stats.innerHTML = "";
    [["done", up, "Uploaded"], ["todo", Math.max(0, sent - up), "Sent · Pending"],
     ["", total, "Total"], ["pct", pct + "%", "Complete"]].forEach(function (s) {
      var d = el("div", "stat" + (s[0] ? " " + s[0] : ""));
      d.appendChild(el("b", null, String(s[1])));
      d.appendChild(el("span", null, s[2]));
      stats.appendChild(d);
    });
    var bar = el("div", "stat bar");
    bar.appendChild(el("span", null, "Progress"));
    var track = el("div", "track"), fill = el("div", "fill");
    fill.style.width = pct + "%";
    track.appendChild(fill); bar.appendChild(track); stats.appendChild(bar);

    var cats = {};
    var dl = document.getElementById("catList");
    dl.innerHTML = "";
    traits.forEach(function (t) {
      if (!cats[t.category]) { cats[t.category] = true;
        var o = document.createElement("option"); o.value = t.category; dl.appendChild(o); }
    });

    var cards = document.getElementById("cards");
    cards.innerHTML = "";
    traits.forEach(function (t) {
      var tUp = t.variants.filter(function (v) { return v.uploaded; }).length;
      var card = el("section", "card" + (tUp === t.variants.length && t.variants.length ? " complete" : ""));

      var head = el("header", "card-head");
      var id = el("div", "card-id");
      id.appendChild(el("span", "cat", t.category));
      var h2 = el("h2", null, t.name);
      id.appendChild(h2); head.appendChild(id);
      var count = el("span", "count");
      count.appendChild(document.createTextNode(String(tUp)));
      count.appendChild(el("em", null, "/"));
      count.appendChild(document.createTextNode(String(t.variants.length)));
      head.appendChild(count);
      card.appendChild(head);

      var body = el("div", "card-body");

      var fig = el("figure", "ref");
      fig.appendChild(el("figcaption", null, "Reference"));
      if (t.reference) {
        var img = document.createElement("img");
        img.src = t.reference; img.alt = t.name + " reference";
        fig.appendChild(img);
      } else {
        var slot = el("div", "ref-slot");
        slot.appendChild(el("span", null, "no reference art yet"));
        fig.appendChild(slot);
      }
      var upBtn = el("button", "ref-up", t.reference ? "replace image" : "upload image");
      upBtn.type = "button";
      upBtn.addEventListener("click", function () {
        pickImage(function (dataUri) {
          overlay.refs[tid(t)] = dataUri;
          var local = overlay.added.find(function (a) { return tid(a) === tid(t); });
          if (local) local.reference = dataUri;
          saveOverlay(); render();
        });
      });
      fig.appendChild(upBtn);
      body.appendChild(fig);

      var tiles = el("div", "tiles");
      t.variants.forEach(function (v) {
        var tile = el("div", "tile" + (v.uploaded ? " done" : ""));
        var badges = el("div", "badges");
        badges.appendChild(el("span", "badge gender", v.gender));
        var skin = el("span", "badge skin");
        var dot = document.createElement("i");
        dot.style.background = TONES[v.skin] || "#999";
        skin.appendChild(dot);
        skin.appendChild(document.createTextNode(v.skin));
        badges.appendChild(skin);
        tile.appendChild(badges);

        var checks = el("div", "checks");
        var bSent = el("button", "check sent" + (v.sent ? " on" : ""), (v.sent ? "✓ " : "") + "sent");
        var bUp = el("button", "check up" + (v.uploaded ? " on" : ""), (v.uploaded ? "✓ " : "") + "uploaded");
        bSent.type = bUp.type = "button";
        bSent.addEventListener("click", function () {
          var o = overlay.variants[vid(t, v)] || { sent: v.sent, uploaded: v.uploaded };
          o.sent = !v.sent;
          if (!o.sent) o.uploaded = false;
          overlay.variants[vid(t, v)] = o; saveOverlay(); render();
        });
        bUp.addEventListener("click", function () {
          var o = overlay.variants[vid(t, v)] || { sent: v.sent, uploaded: v.uploaded };
          o.uploaded = !v.uploaded;
          if (o.uploaded) o.sent = true;
          overlay.variants[vid(t, v)] = o; saveOverlay(); render();
        });
        checks.appendChild(bSent); checks.appendChild(bUp);
        tile.appendChild(checks);

        if (v.image) {
          var art = el("div", "art");
          var ai = document.createElement("img");
          ai.src = v.image; ai.alt = t.name + " " + v.gender + " " + v.skin;
          art.appendChild(ai); tile.appendChild(art);
        }
        tiles.appendChild(tile);
      });
      body.appendChild(tiles);
      card.appendChild(body);
      cards.appendChild(card);
    });

    document.getElementById("unsynced").className = "unsynced" + (hasLocal() ? " on" : "");
  }

  // ---- image picking: alpha-crop trait layers, downscale, return data URI
  function pickImage(cb) {
    var input = document.createElement("input");
    input.type = "file"; input.accept = "image/*";
    input.addEventListener("change", function () {
      if (input.files && input.files[0]) fileToDataUri(input.files[0], cb);
    });
    input.click();
  }
  function fileToDataUri(file, cb) {
    var img = new Image();
    var url = URL.createObjectURL(file);
    img.onload = function () {
      URL.revokeObjectURL(url);
      var c = document.createElement("canvas");
      c.width = img.naturalWidth; c.height = img.naturalHeight;
      var ctx = c.getContext("2d");
      ctx.drawImage(img, 0, 0);
      var box = alphaBBox(ctx, c.width, c.height) || { x: 0, y: 0, w: c.width, h: c.height };
      var scale = Math.min(1, 480 / Math.max(box.w, box.h));
      var out = document.createElement("canvas");
      out.width = Math.max(1, Math.round(box.w * scale));
      out.height = Math.max(1, Math.round(box.h * scale));
      out.getContext("2d").drawImage(img, box.x, box.y, box.w, box.h, 0, 0, out.width, out.height);
      cb(out.toDataURL("image/png"));
    };
    img.onerror = function () { URL.revokeObjectURL(url); alert("Couldn't read that image."); };
    img.src = url;
  }
  function alphaBBox(ctx, w, h) {
    try {
      var d = ctx.getImageData(0, 0, w, h).data;
      var minX = w, minY = h, maxX = -1, maxY = -1;
      for (var y = 0; y < h; y++) {
        for (var x = 0; x < w; x++) {
          if (d[(y * w + x) * 4 + 3] > 8) {
            if (x < minX) minX = x; if (x > maxX) maxX = x;
            if (y < minY) minY = y; if (y > maxY) maxY = y;
          }
        }
      }
      if (maxX < 0) return null;
      var pad = 24;
      minX = Math.max(0, minX - pad); minY = Math.max(0, minY - pad);
      maxX = Math.min(w - 1, maxX + pad); maxY = Math.min(h - 1, maxY + pad);
      // a layer with no transparency crops to the full frame — keep it
      if (maxX - minX >= w - 2 && maxY - minY >= h - 2) return null;
      return { x: minX, y: minY, w: maxX - minX + 1, h: maxY - minY + 1 };
    } catch (e) { return null; }
  }

  // ---- add-trait form
  var addForm = document.getElementById("addForm");
  var vGrid = document.getElementById("vGrid");
  GENDERS.forEach(function (g) {
    SKINS.forEach(function (s) {
      var lab = el("label", "vopt");
      var cb = document.createElement("input");
      cb.type = "checkbox"; cb.checked = true;
      cb.dataset.gender = g; cb.dataset.skin = s;
      lab.appendChild(cb);
      lab.appendChild(document.createTextNode(g + " · " + s));
      vGrid.appendChild(lab);
    });
  });
  document.getElementById("addBtn").addEventListener("click", function () {
    addForm.classList.toggle("open");
  });
  document.getElementById("cancelAdd").addEventListener("click", function () {
    addForm.classList.remove("open");
  });
  addForm.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var cat = document.getElementById("fCat").value.trim();
    var name = document.getElementById("fName").value.trim();
    if (!cat || !name) return;
    var variants = [];
    vGrid.querySelectorAll("input:checked").forEach(function (cb) {
      variants.push({ gender: cb.dataset.gender, skin: cb.dataset.skin, sent: false, uploaded: false, image: null });
    });
    if (!variants.length) { alert("Pick at least one version."); return; }
    var trait = { category: cat, name: name, reference: null, variants: variants };
    var exists = merged().some(function (t) { return tid(t) === tid(trait); });
    if (exists) { alert('"' + cat + " · " + name + '" is already on the tracker.'); return; }
    var finish = function () {
      overlay.added.push(trait); saveOverlay();
      addForm.reset();
      vGrid.querySelectorAll("input").forEach(function (cb) { cb.checked = true; });
      addForm.classList.remove("open");
      render();
    };
    var f = document.getElementById("fRef");
    if (f.files && f.files[0]) fileToDataUri(f.files[0], function (uri) { trait.reference = uri; finish(); });
    else finish();
  });

  // ---- sync: export merged state as copyable JSON for Claude to bake in.
  // Unchanged baked images are exported as null (ingest_update.py keeps the
  // previous file) so the payload stays small enough to paste in chat.
  var syncDlg = document.getElementById("syncDlg");
  var copiedNote = document.getElementById("copiedNote");
  document.getElementById("closeDlg").addEventListener("click", function () { syncDlg.close(); });
  document.getElementById("copyBtn").addEventListener("click", function () {
    var ta = document.getElementById("syncText");
    ta.select();
    var shown = function () { copiedNote.style.display = "inline"; };
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(ta.value).then(shown, function () {
          if (document.execCommand("copy")) shown();
        });
      } else if (document.execCommand("copy")) shown();
    } catch (e) { try { if (document.execCommand("copy")) shown(); } catch (e2) {} }
  });
  function updatePayload() {
    var bakedRefs = {}, bakedImgs = {};
    BAKED.traits.forEach(function (t) {
      bakedRefs[tid(t)] = t.reference;
      t.variants.forEach(function (v) { bakedImgs[tid(t) + "|" + (v.gender + "|" + v.skin).toLowerCase()] = v.image; });
    });
    var traits = merged().map(function (t) {
      return {
        category: t.category, name: t.name,
        reference: t.reference === bakedRefs[tid(t)] ? null : t.reference,
        variants: t.variants.map(function (v) {
          var k = tid(t) + "|" + (v.gender + "|" + v.skin).toLowerCase();
          return { gender: v.gender, skin: v.skin, sent: v.sent, uploaded: v.uploaded,
                   image: v.image === bakedImgs[k] ? null : v.image };
        })
      };
    });
    return JSON.stringify({ kind: "trait-tracker-update",
      exported: new Date().toISOString().slice(0, 10), traits: traits });
  }
  document.getElementById("syncBtn").addEventListener("click", function () {
    copiedNote.style.display = "none";
    document.getElementById("syncText").value = updatePayload();
    syncDlg.showModal();
  });

  render();
})();
</script>
'''


if __name__ == "__main__":
    render()
