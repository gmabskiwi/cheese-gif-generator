# NFT Trait Tracker

Live dashboard at [claude.ai/code/artifact/a7204712-723c-4707-b244-5b1f781fff45](https://claude.ai/code/artifact/a7204712-723c-4707-b244-5b1f781fff45)

## Using the dashboard

Everything happens on the page itself:

- **Add trait** — name it, pick which versions are needed (male/female ×
  white/tanned/brown), optionally attach a reference image.
- **Upload image** on any trait card sets or replaces its reference art.
  Full-canvas trait layers are auto-cropped to the artwork.
- Tap **sent** when the artist sends a version, **uploaded** when the team
  has it in the collection (uploading implies sent). Fully uploaded traits
  turn green.

Changes save instantly in that person's browser. To publish them for
everyone at the same link, hit **Sync changes** — it downloads
`trait-tracker-update.json` — and drop that file in chat with Claude.

## Behind the scenes

`traits.json` is the canonical state; reference images live in `art/`.

- `build_dashboard.py` — renders `dashboard.html` from `traits.json`
  (references embedded as cropped data URIs) for publishing.
- `ingest_update.py` — merges a synced `trait-tracker-update.json` into
  `traits.json`, writing any newly uploaded images out to `art/`:

  ```
  python ingest_update.py trait-tracker-update.json
  python build_dashboard.py
  ```

- `NFT_Trait_Tracker.xlsx` + `add_traits.py` + `build_tracker.py` — the
  optional spreadsheet version of the tracker (append traits with
  `python add_traits.py "Left Arm: Rolex"`).

You can also just tell Claude what changed ("tiger claw female tanned is
uploaded") — same result, no file needed.
