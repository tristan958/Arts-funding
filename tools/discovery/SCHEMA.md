# Opportunity schema (for discovery candidates)

Each candidate in `data/candidates.json` must match the shape of an entry in
`data/funding.json`. Use the controlled vocabularies below so the facets and
saved views on the dashboard work consistently.

```jsonc
{
  "id": "funder-slug-short-title",     // unique, kebab-case
  "title": "Programme name",
  "funder": "Organisation name",
  "type": "grant",                      // see TYPE
  "status": "open",                     // "open" | "closed"
  "deadline": "2026-09-30",             // ISO date, or "Rolling" / "Varies"
  "amount": "Up to R250,000",           // free text; "Varies" if unknown
  "description": "1–3 sentence plain-language summary.",
  "eligibility": "Who can apply.",
  "focus_areas": ["Short", "Tag", "Strings"],   // visible chips on the card
  "disciplines": ["visual-art"],        // see DISCIPLINES (multi)
  "purpose": ["project"],               // see PURPOSE (multi)
  "eligibility_type": ["individual"],   // "individual" | "organisation" | "collective" (multi)
  "org_focus": false,                   // true if specifically for arts ORGANISATIONS
  "tags": ["experimental"],             // see TAGS (multi, free-ish)
  "audiences": [],                      // ["vansa"] when on-mission for contemporary visual art
  "region": "national",                 // see REGION
  "how_to_apply": "Where/how to apply.",
  "url": "https://official-funder-link",
  "date_added": "2026-06-17"            // today
}
```

## Controlled vocabularies

**TYPE** (the funding vehicle): `grant` · `bursary` · `fellowship` · `residency` · `award` · `call` · `tender`

**DISCIPLINES** (the art form): `visual-art` · `performing-arts` · `music` · `film-screen` · `new-media-digital` · `podcast-audio` · `literature` · `craft` · `design` · `interdisciplinary` · `public-art` · `heritage` · `all-disciplines`
> Use `all-disciplines` for funders open to any art form — the dashboard treats it as matching every Art-form filter.

**PURPOSE** (what the money is for): `project` · `capacity-building` · `bursary` · `residency` · `mobility` · `production` · `research` · `commission` · `procurement`
> `capacity-building` = organisational development: governance/board training, strategy, fundraising capacity, M&E, scaling, sustainability.

**REGION**: `national` · `gauteng` · `western-cape` · `kwazulu-natal` · `africa` · `international`

**TAGS** (free, but prefer reuse): `experimental` · `site-specific` · `spatial` · `socially-engaged` · `research-based` · `public-space` · `interdisciplinary` · `immersive-xr` · `documentary` · `narrative-change` · `community` · `rural` · `youth` · `women` · `international-exchange` · `organisational-development` · `sustainability` · `photography` · `nomination-only` · `sa-only`
> The **Experimental & spatial** saved view matches any of: `experimental, site-specific, spatial, socially-engaged, research-based, public-space, interdisciplinary`.

## Saved-view triggers (so candidates surface in the right lens)
- **VANSA (org)** → `audiences` includes `vansa` **AND** (`eligibility_type` includes `organisation` **OR** `purpose` includes `capacity-building`). This lens is for funding **VANSA itself** can apply for — core/project funding open to arts organisations, plus organisational capacity building. Still tag on-mission *individual*-artist visual-art opportunities with `vansa` (they're useful to members and surface in search/facets) — they just won't appear in this org-scoped view unless an organisation is also eligible.
- **New media & podcast** → `disciplines` includes `new-media-digital`, `podcast-audio`, or `film-screen`
- **Capacity building** → `purpose` includes `capacity-building`
- **Experimental & spatial** → see the tag set above
- **Residencies & fellowships** → `type` is `residency`/`fellowship`, **or** `purpose` includes `residency` or `mobility` (residencies, fellowships and similar place-/programme-based or exchange opportunities, across all disciplines)
