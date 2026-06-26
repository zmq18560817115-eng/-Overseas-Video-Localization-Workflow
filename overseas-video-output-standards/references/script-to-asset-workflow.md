# Script to Asset Workflow

## Purpose

Use this reference when turning TikTok/competitor decomposition, a base script, or a viral template into a branded overseas short-video package.

The workflow is not “copy the viral video.” It is:

`analyze structure -> choose audience scene -> migrate logic to product -> map every shot to approved material -> generate/edit -> review`

## Phase 1: Separate structure from product facts

From the original/competitor video, extract only:

- Hook type: identity callout, pain contrast, curiosity, demonstration, mistake correction, before/after structure.
- Beat structure: hook, setup, problem, turning point, demo/proof, CTA.
- Rhythm: shot length, subtitle density, speech speed, cuts, zooms, UI overlays.
- Visual roles: face-to-camera, product close-up, hand demo, lifestyle scene, proof/detail insert.
- Emotional logic: anxiety relief, convenience, cost, nighttime stress, travel friction, work routine.

Do not reuse competitor claims, exact wording, product features, brand names, logos, packaging, or unique creative lines.

## Phase 2: Choose the brand scenario

Pick one main audience and one main scene from the product material.

Example scenario fields:

```yaml
product: ""
audience: ""
main_scene: ""
core_pain: ""
product_solution: ""
safe_proof_or_demo: ""
cta_style: ""
```

The product should enter as the solution to the scene, not as a floating ad. A useful mental line is: scene first, pain second, product as the “answer.”

## Phase 3: Write the brand-safe script

Every script must preserve:

- Product facts from product docs or approved material.
- Audience language appropriate to TikTok/Reels/short-form overseas viewers.
- One clear Hook and one clear CTA.
- A natural transition from pain to product demo.
- No unsupported medical, guaranteed, superlative, or competitor comparison claims.

For each claim, mark it as:

- `source_claim`: backed by product docs or approved listing material.
- `visual_demo`: shown visually but not overstated in text.
- `soft_opinion`: personal/creator-style wording that does not claim objective proof.
- `blocked`: not allowed unless the company approves a source.

## Phase 4: Build the shot-to-asset map

For each shot, produce this table or equivalent JSON:

| Field | Required content |
| --- | --- |
| shot_id | Stable shot number |
| time_range | Approximate duration |
| script_role | Hook, pain, setup, demo, proof, CTA, transition |
| dialogue_or_subtitle | Spoken line or subtitle |
| visual_description | What the editor/viewer sees |
| required_asset_type | Product identity, usage step, scene, detail, person, AI b-roll |
| asset_path_or_status | Exact path, generated asset id, missing, or needs review |
| generation_or_edit_method | Real footage, static image, SeedDance, overlay, subtitle, crop |
| prompt_guardrails | Product, scene, person, and claim constraints |
| compliance_note | Claim/visual risks |

Every product-visible shot must include an approved product image or a missing-asset note.

## Phase 5: SeedDance or AI-video prompt rules

When generating video from images or text:

1. Anchor product appearance with approved product identity or usage-step references.
2. State the scene and product relationship explicitly.
3. Keep one consistent person profile if a person appears.
4. Avoid asking the model to invent logos, UI text, accessories, bottle type, or product structure.
5. Use product-only or hands-only shots when identity consistency is not guaranteed.
6. Preserve safe compliance language: the video can demonstrate handling, convenience, and context, but cannot prove medical or guaranteed outcomes.

Prompt fields to include:

```yaml
shot_id: ""
source_refs: []
scene: ""
person_profile: ""
product_constraints: []
action: ""
camera: ""
lighting: ""
negative_constraints: []
duration: ""
```

## Phase 6: Editing task package

A complete editing task package should include:

- Final script and subtitle lines.
- Shot list with time ranges.
- Asset manifest with source paths.
- AI-generation prompts and generated asset IDs/paths.
- Music/SFX/subtitle/overlay notes.
- Compliance notes and human-review blockers.
- Export specs for the target platform.

If an asset is missing, do not silently replace it with a generic stock shot. Mark the missing asset and offer a safer fallback such as product-only tabletop, hands-only demo, or static product card.
