"""Render trait-tracker/dashboard.html from traits.json.

Variant images: set a variant's "image" to a path (relative to this folder,
e.g. "art/tiger-claw-female-white.png") and it is embedded as a thumbnail.
The output is an HTML fragment for publishing as a claude.ai Artifact
(no <html>/<head>/<body> wrapper).
"""
import base64
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "traits.json")
OUT = os.path.join(HERE, "dashboard.html")

THUMB = 480  # max px for embedded art


def image_data_uri(relpath):
    path = os.path.join(HERE, relpath)
    try:
        from PIL import Image
        img = Image.open(path)
        img.thumbnail((THUMB, THUMB))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data = buf.getvalue()
    except Exception:
        with open(path, "rb") as fh:
            data = fh.read()
    return "data:image/png;base64," + base64.b64encode(data).decode()


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render():
    with open(STATE) as fh:
        state = json.load(fh)

    traits = state["traits"]
    all_variants = [v for t in traits for v in t["variants"]]
    uploaded = sum(1 for v in all_variants if v["uploaded"])
    sent = sum(1 for v in all_variants if v["sent"])
    total = len(all_variants)
    pct = round(100 * uploaded / total) if total else 0

    skin_tones = {"White": "#F3D8C2", "Tanned": "#D9A468", "Brown": "#8D5B35"}

    cards = []
    for t in traits:
        t_uploaded = sum(1 for v in t["variants"] if v["uploaded"])
        t_total = len(t["variants"])
        tiles = []
        for v in t["variants"]:
            alt = f'{esc(v["gender"])} {esc(v["skin"])}'
            if v["uploaded"] and v.get("image"):
                art = f'<div class="art"><img src="{image_data_uri(v["image"])}" alt="{alt}"></div>'
            elif v["uploaded"]:
                art = '<div class="art"><span>uploaded</span></div>'
            else:
                art = ''
            cls = "tile done" if v["uploaded"] else "tile"
            sent_check = '<span class="check sent" data-status="sent">✓ sent</span>' if v["sent"] else '<span class="check todo" data-status="sent">sent</span>'
            uploaded_check = '<span class="check ok" data-status="uploaded">✓ uploaded</span>' if v["uploaded"] else '<span class="check todo" data-status="uploaded">uploaded</span>'
            tone = skin_tones.get(v["skin"], "#999999")
            tiles.append(
                f'<div class="{cls}">'
                f'<div class="badges"><span class="badge gender">{esc(v["gender"])}</span>'
                f'<span class="badge skin"><i style="background:{tone}"></i>{esc(v["skin"])}</span></div>'
                f'<div class="checks">{sent_check}{uploaded_check}</div>'
                f'{art}</div>')
        if t.get("reference"):
            ref = (f'<figure class="ref"><figcaption>Reference</figcaption>'
                   f'<img src="{image_data_uri(t["reference"])}" alt="{esc(t["name"])} reference">'
                   f'</figure>')
        else:
            ref = ('<figure class="ref empty"><figcaption>Reference</figcaption>'
                   '<div class="ref-slot"><span>no reference art yet</span></div></figure>')
        complete = ' complete' if t_uploaded == t_total else ''
        cards.append(f'''
    <section class="card{complete}">
      <header class="card-head">
        <div class="card-id">
          <span class="cat">{esc(t["category"])}</span>
          <h2>{esc(t["name"])}</h2>
        </div>
        <span class="count">{t_uploaded}<em>/</em>{t_total}</span>
      </header>
      <div class="card-body">
        {ref}
        <div class="tiles">{"".join(tiles)}</div>
      </div>
    </section>''')

    html = f'''<title>Trait Tracker</title>
<style>
  :root {{
    --ink: #0E1116; --panel: #141922; --card: #12161D; --line: #242C38;
    --text: #F2F5F9; --muted: #8C95A4; --amber: #FFB525;
    --ok: #3DDC97; --todo: #F87171;
    --mono: ui-monospace, "SF Mono", "Cascadia Mono", Menlo, Consolas, monospace;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    background: var(--ink); color: var(--text); margin: 0;
    font: 16px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    -webkit-font-smoothing: antialiased;
  }}
  .wrap {{ max-width: 1060px; margin: 0 auto; padding: 44px 24px 72px; }}

  .eyebrow {{
    font: 700 11px/1 var(--mono); letter-spacing: .22em; color: var(--amber);
    text-transform: uppercase; margin: 0 0 12px;
  }}
  h1 {{
    font-size: clamp(34px, 6vw, 52px); font-weight: 800; letter-spacing: -.02em;
    line-height: 1.02; margin: 0 0 10px; text-wrap: balance;
  }}
  .sub {{ color: var(--muted); margin: 0 0 30px; max-width: 56ch; }}

  .stats {{
    display: grid; grid-template-columns: repeat(4, minmax(110px, 1fr)) 2fr;
    gap: 10px; margin-bottom: 40px;
  }}
  .stat {{
    background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
    padding: 14px 16px 12px;
  }}
  .stat b {{
    display: block; font-size: 30px; font-weight: 800; line-height: 1.1;
    font-variant-numeric: tabular-nums;
  }}
  .stat span {{
    font: 700 10px/1 var(--mono); letter-spacing: .16em; color: var(--muted);
    text-transform: uppercase;
  }}
  .stat.done b {{ color: var(--ok); }}
  .stat.todo b {{ color: var(--todo); }}
  .stat.pct b {{ color: var(--amber); }}
  .stat.bar {{ display: flex; flex-direction: column; justify-content: center; gap: 10px; }}
  .track {{ height: 10px; background: var(--line); border-radius: 5px; overflow: hidden; }}
  .fill {{ height: 100%; background: var(--amber); border-radius: 5px; }}

  .card {{
    background: var(--card); border: 1px solid var(--line); border-radius: 14px;
    padding: 22px 22px 24px; margin-bottom: 18px;
  }}
  .card.complete {{ border-color: color-mix(in srgb, var(--ok) 45%, var(--line)); }}
  .card-head {{
    display: flex; align-items: baseline; justify-content: space-between;
    gap: 16px; margin-bottom: 16px;
  }}
  .cat {{
    display: inline-block; font: 700 10px/1 var(--mono); letter-spacing: .18em;
    text-transform: uppercase; color: var(--amber);
    border: 1px solid color-mix(in srgb, var(--amber) 45%, transparent);
    border-radius: 4px; padding: 4px 7px; margin-bottom: 8px;
  }}
  .card-id h2 {{ margin: 0; font-size: 23px; font-weight: 800; letter-spacing: -.01em; }}
  .count {{
    font: 800 22px/1 var(--mono); font-variant-numeric: tabular-nums; white-space: nowrap;
  }}
  .count em {{ font-style: normal; color: var(--muted); padding: 0 2px; }}
  .card.complete .count {{ color: var(--ok); }}

  .card-body {{ display: flex; gap: 18px; align-items: flex-start; }}
  .ref {{ margin: 0; flex: 0 0 200px; display: flex; flex-direction: column; gap: 8px; }}
  .ref figcaption {{
    font: 700 10px/1 var(--mono); letter-spacing: .18em; text-transform: uppercase;
    color: var(--amber);
  }}
  .ref img, .ref-slot {{
    width: 100%; aspect-ratio: 1; border-radius: 10px; object-fit: cover;
    background: var(--panel);
    border: 1px solid color-mix(in srgb, var(--amber) 40%, var(--line));
  }}
  .ref.empty .ref-slot {{
    border-style: dashed; display: flex; align-items: center; justify-content: center;
  }}
  .ref-slot span {{ font: 500 11px/1.4 var(--mono); color: var(--muted); text-align: center;
    padding: 0 14px; }}

  .tiles {{
    flex: 1; display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 12px;
  }}
  .tile {{
    display: flex; flex-direction: column; gap: 9px;
    background: var(--panel); border: 1px solid var(--line); border-radius: 11px;
    padding: 10px;
  }}
  .tile.done {{ border-color: color-mix(in srgb, var(--ok) 55%, var(--line)); }}
  .badges {{ display: flex; align-items: center; gap: 5px; flex-wrap: wrap; }}
  .checks {{ display: flex; gap: 8px; }}
  .check {{
    font: 800 9px/1 var(--mono); letter-spacing: .12em; border-radius: 3px;
    padding: 4px 6px; flex: none; cursor: pointer;
  }}
  .check.ok {{ background: var(--ok); color: var(--ink); }}
  .check.sent {{ background: color-mix(in srgb, var(--amber) 35%, transparent); color: var(--amber); }}
  .check.todo {{ background: color-mix(in srgb, var(--todo) 18%, transparent); color: var(--todo); }}
  .badge {{
    font: 800 10px/1 var(--mono); letter-spacing: .1em; text-transform: uppercase;
    border-radius: 4px; padding: 5px 7px;
  }}
  .badge.gender {{ background: #2A3240; color: var(--text); }}
  .badge.skin {{
    background: #1C222C; color: var(--text);
    display: inline-flex; align-items: center; gap: 5px;
  }}
  .badge.skin i {{
    width: 10px; height: 10px; border-radius: 50%; display: inline-block;
    border: 1px solid #00000055;
  }}
  .art {{
    aspect-ratio: 1; border-radius: 7px; overflow: hidden;
    background: var(--card); border: 1px solid var(--line);
    display: flex; align-items: center; justify-content: center;
  }}
  .art img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .art.empty {{ border: 1px dashed #334052; }}
  .art.empty span {{ font: 500 11px/1 var(--mono); color: var(--muted); letter-spacing: .06em; }}
  .chip {{
    font: 800 9px/1 var(--mono); letter-spacing: .12em; border-radius: 3px;
    padding: 4px 6px; flex: none; margin-left: auto;
  }}
  .chip.ok {{ background: var(--ok); color: var(--ink); }}
  .chip.todo {{ background: color-mix(in srgb, var(--todo) 18%, transparent); color: var(--todo); }}

  footer {{
    margin-top: 44px; padding-top: 18px; border-top: 1px solid var(--line);
    color: var(--muted); font: 500 12px/1.6 var(--mono);
  }}
  @media (max-width: 640px) {{
    .stats {{ grid-template-columns: repeat(2, 1fr); }}
    .stat.bar {{ grid-column: 1 / -1; }}
    .card-body {{ flex-direction: column; }}
    .ref {{ flex-basis: auto; width: 100%; max-width: 260px; }}
  }}
</style>
<div class="wrap">
  <p class="eyebrow">NFT Collection · Art Progress</p>
  <h1>Trait Tracker</h1>
  <p class="sub">Every image the collection needs and where it stands. Finished versions
  light up green — anything marked <strong>needed</strong> is open work.</p>

  <div class="stats">
    <div class="stat done"><b>{uploaded}</b><span>Uploaded</span></div>
    <div class="stat todo"><b>{sent - uploaded}</b><span>Pending</span></div>
    <div class="stat"><b>{total}</b><span>Total</span></div>
    <div class="stat pct"><b>{pct}%</b><span>Complete</span></div>
    <div class="stat bar">
      <span>Progress</span>
      <div class="track"><div class="fill" style="width:{pct}%"></div></div>
    </div>
  </div>
{"".join(cards)}
  <footer>Updated {esc(state["updated"])} · to add traits or check work off, drop it in
  chat with Claude — this page updates at the same link.</footer>
</div>
'''
    with open(OUT, "w") as fh:
        fh.write(html)
    print(f"dashboard.html written — {uploaded}/{total} uploaded ({pct}%)")


if __name__ == "__main__":
    render()
