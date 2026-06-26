---
name: overseas-video-output-standards
description: "Use this skill when building, reviewing, or generating the overseas video localization workflow output: company product image/material library intake, TikTok competitor decomposition to brand-safe scripts, product-use display rules, scene and on-camera person consistency, SeedDance or other AI-video prompts, shot-to-asset mapping, editing task packs, and compliance checks for maternal/baby products."
---

# Overseas Video Output Standards

## Overview

This skill turns viral-video analysis into a brand-safe, material-aware production workflow. Use it to ensure every script, storyboard, AI-video prompt, and editing task package is grounded in approved company product material instead of improvised product details.

The core logic is:

`competitor structure/rhythm -> audience scenario -> company product facts -> approved assets -> shot task package -> human review`

## Start every task with source grounding

Before writing or reviewing output, identify the target product, target platform, and requested deliverable: script, shot list, SeedDance prompt, editing package, material-library intake, or QA.

Load product and process sources in this priority order when available:

1. Workspace product docs: `01_素材库/产品资料/{产品名}.md`（或联接路径 `海外视频本地化MVP/产品资料/`）
2. Local MVP knowledge fallback: `overseas-loc-mvp/knowledge/products/{产品名}.md`
3. DS223 Obsidian knowledge base: `\\DS223\obsidian知识库\shared-knowledge\products\`
4. Global process/compliance docs, especially `overseas-loc-mvp\knowledge\processes\海外短视频合规禁词.md` and DS223 `shared-knowledge\processes\`

Use competitor/TikTok content only for structure, pacing, hook style, shot rhythm, and audience insight. Do not copy competitor dialogue, claims, logos, product positioning, or product details.

## Load the right reference file

- For product image selection, company material intake, or image-library cleanup, load `references/material-asset-standards.md`.
- For converting a decomposed viral video or base script into a branded shot list, storyboard, SeedDance prompt, or editing task package, load `references/script-to-asset-workflow.md`.
- For product-specific usage, prohibited visuals, and allowed/forbidden claims, load `references/product-rules.md`.
- Before final delivery, load `references/qa-checklist.md`.

For most production tasks, load at least `script-to-asset-workflow.md`, `product-rules.md`, and `qa-checklist.md`.

## Non-negotiable production logic

The story line should usually be:

`scene -> pain -> product as solution -> safe proof/demo -> CTA`

Keep the user and scene first. The product should feel like the answer to a concrete moment, not like a hard advertisement dropped into a random viral template.

Every generated output must preserve:

- Product factuality: product shape, usage steps, accessories, and claims come from approved materials.
- Asset traceability: every product image, scene image, generated clip, and reference image has a source path or status.
- Scene continuity: location, lighting, props, time of day, and family/work/travel context do not drift without a scripted reason.
- Person continuity: if a person appears, age range, role, wardrobe, hair, hands, and relationship to the product remain consistent.
- Compliance: no unsupported medical, guaranteed, superlative, competitor, or restricted platform claims.

## Required output contract

When generating or reviewing a script/shot list/prompt, include these sections unless the user explicitly asks for a lighter answer:

1. `product_sources`: product docs and material folders consulted.
2. `asset_manifest`: approved/reference-only/missing assets with source paths.
3. `shot_asset_map`: each shot mapped to script purpose, visual, asset path/status, and generation/editing method.
4. `scene_continuity`: main scene, allowed transitions, and visual constraints.
5. `character_continuity`: person profile or reason to use product-only/hands-only shots.
6. `claim_guardrails`: allowed claims, forbidden claims, and wording rewrites.
7. `delivery_risks`: blockers, warnings, and what needs human review.

Never say “let the AI infer the product appearance.” If a product detail matters visually, require an approved product reference or mark the asset as missing.

## Updating the standard

Put cross-product workflow rules in this skill. Put single-product facts in the product’s own material/knowledge file, then reference those facts from outputs. When a new product is added, require at minimum: product identity, target audience, allowed scenes, correct usage steps, prohibited visuals, approved claims, forbidden claims, and asset folder paths.
