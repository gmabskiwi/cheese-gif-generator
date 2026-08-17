"""Merge a trait-tracker-update.json (exported by the dashboard's Sync
button) into traits.json.

Usage:
    python ingest_update.py path/to/trait-tracker-update.json

Data-URI images in the update are written out to art/ as PNG files and the
state keeps relative paths; run build_dashboard.py afterwards to publish.
"""
import base64
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "traits.json")
ART = os.path.join(HERE, "art")


def slug(*parts):
    s = "-".join(p.lower() for p in parts)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def materialize(data_uri, filename):
    """Write a data: URI to art/<filename> and return the relative path."""
    header, _, b64 = data_uri.partition(",")
    if not header.startswith("data:image") or not b64:
        raise ValueError("not an image data URI")
    os.makedirs(ART, exist_ok=True)
    relpath = os.path.join("art", filename)
    with open(os.path.join(HERE, relpath), "wb") as fh:
        fh.write(base64.b64decode(b64))
    return relpath


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    with open(sys.argv[1]) as fh:
        update = json.load(fh)
    if update.get("kind") != "trait-tracker-update":
        sys.exit("Not a trait-tracker update file (missing kind marker).")

    try:
        with open(STATE) as fh:
            old = {(t["category"].lower(), t["name"].lower()): t
                   for t in json.load(fh)["traits"]}
    except FileNotFoundError:
        old = {}

    traits = []
    for t in update["traits"]:
        prev = old.get((t["category"].lower(), t["name"].lower()), {})
        prev_imgs = {(v["gender"].lower(), v["skin"].lower()): v.get("image")
                     for v in prev.get("variants", [])}
        # the export nulls out anything unchanged; null means "keep what's on disk"
        ref = t.get("reference")
        if ref and ref.startswith("data:"):
            ref = materialize(ref, slug(t["category"], t["name"]) + "-reference.png")
        elif not ref:
            ref = prev.get("reference")
        variants = []
        for v in t["variants"]:
            img = v.get("image")
            if img and img.startswith("data:"):
                img = materialize(img, slug(t["category"], t["name"], v["gender"], v["skin"]) + ".png")
            elif not img:
                img = prev_imgs.get((v["gender"].lower(), v["skin"].lower()))
            variants.append({"gender": v["gender"], "skin": v["skin"],
                             "sent": bool(v.get("sent")), "uploaded": bool(v.get("uploaded")),
                             "image": img})
        traits.append({"category": t["category"], "name": t["name"],
                       "reference": ref, "variants": variants})

    state = {"updated": datetime.date.today().isoformat(), "traits": traits}
    with open(STATE, "w") as fh:
        json.dump(state, fh, indent=2)
        fh.write("\n")
    total = sum(len(t["variants"]) for t in traits)
    up = sum(1 for t in traits for v in t["variants"] if v["uploaded"])
    print(f"traits.json updated — {len(traits)} trait(s), {up}/{total} uploaded. "
          "Run build_dashboard.py to publish.")


if __name__ == "__main__":
    main()
