# NFT Trait Tracker

One spreadsheet (`NFT_Trait_Tracker.xlsx`) tracks every image the collection
needs: one row per trait, six versions across (male & female × white, tanned,
brown skin).

## Adding work

Drop the new traits in chat with Claude in any loose format, e.g.

> left arm: rolex, snake tattoo — right arm: pinky ring

Claude appends them to the canonical file and sends the updated sheet back.
The same append can be run by hand:

```
python add_traits.py "Left Arm: Rolex, Snake Tattoo" "Right Arm: Pinky Ring"
```

Appending never touches pasted art, checkmarks, or formatting — it only fills
the next empty pre-formatted rows.

## Checking work off

In the sheet itself: paste the art onto its slot (normal paste, then drag it
over the cell) and pick ✓ in the small box beside it. The slot turns green,
the trait's DONE counter climbs, and the header stats update.

**If the sheet has been edited since Claude last saw it, attach the current
copy when dropping new traits** so the additions land in the live version,
not a stale one.

`build_tracker.py` regenerates a blank tracker from scratch (styling,
formulas, empty rows) — only for starting over, since a rebuild has no
knowledge of pasted art.
