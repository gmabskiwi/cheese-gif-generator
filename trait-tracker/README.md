# NFT Trait Tracker

Live dashboard at [claude.ai/code/artifact/a7204712-723c-4707-b244-5b1f781fff45](https://claude.ai/code/artifact/a7204712-723c-4707-b244-5b1f781fff45)

## System

`traits.json` is the canonical state file. It tracks every image the collection needs with a two-step workflow:
1. **Sent** — artist marks when they send the image
2. **Uploaded** — team checks off when the image is received and verified

Each trait has variants across gender (male/female) and skin tone (white/tanned/brown).

## Adding traits

Drop new traits in chat with Claude, or use the script directly:

```
python add_traits.py "Left Arm: Rolex, Snake Tattoo" "Right Arm: Pinky Ring"
```

This appends rows to `NFT_Trait_Tracker.xlsx` without touching existing data.

## Dashboard workflow

**Artists**: When you finish an image variant, mark it "sent" on the dashboard.

**Team**: When you receive and verify an uploaded image, mark it "uploaded" to turn it green.

The dashboard regenerates from `traits.json` — to update it after marking work, run:

```
python build_dashboard.py
```

This embeds reference images and trait thumbnails as data URIs and publishes to the live link.

## Files

- `traits.json` — canonical state (variants with sent/uploaded flags)
- `NFT_Trait_Tracker.xlsx` — optional spreadsheet for detailed tracking
- `build_dashboard.py` — renders dashboard.html from traits.json
- `add_traits.py` — appends new traits to both files
- `build_tracker.py` — regenerates blank spreadsheet (start-over only)
