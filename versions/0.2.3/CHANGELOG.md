# Liquid Glass revisions

Numbered archives are preserved before loading a modified project in TurboWarp. The first digit stays 0. Patch revisions include fixes and compatibility changes; middle-digit revisions change the rendering framework.

## 0.2.3 — vanilla Scratch palette compatibility

- Reproduce the missing palette in vanilla Scratch and identify the first error: generated list ID `l_field` contains Blockly's reserved `_field` marker.
- Rename only the internal ID and its eight references; preserve the visible list name, all algorithms, native-editor customizations, comments, assets, and saved state.
- Repair both Studio and reusable component archives; keep the prior version intact.
- Prevent reserved `_field` and `_connection` markers in future generated storage IDs and catch them during structural validation.
- Live editor and runtime verification are recorded under this version's validation directory.

## 0.2.2 — pre-repair checkpoint

- Preserve the root state before applying the editor-ID repair; no fixed archive was loaded from this checkpoint.
- The size guard found a newer native save with spring/damping edits and rebuilt frame buffers. Version 0.2.3 preserves those edits and cleans the buffers before repair.

## 0.2.1 — saved-data cleanup

- Preserve all programs and current native-editor customizations; no Scratch blocks or required data changed.
- Empty only eight saved frame buffers that are rebuilt before shading.
- Reduce `project.json` from 8,452,882 to 3,231,258 bytes (61.8% smaller).
- Preserve both RGB backgrounds, fixed eight-slot caches, component state, assets and the pre-cleanup input.
- Add an external archive cleanup tool for future saved exports. All 42 runtime/import checks and structural validation pass.

## 0.2.0 — verified group blending framework

- Blend all eligible components in a connection group, with shared continuous geometry and material weights, replacing the winning-pair method.
- Preserve the axis-aligned drag correction from 0.1.1 and its visible green-flag examples.
- Keep position-gated smooth joins and low-gradient refraction stabilization.
- 42 runtime/import checks passed on the source and native-editor saved copy; native save/reopen retained all 12 custom blocks. The green-flag loop and running joining/expanded scenes were inspected in TurboWarp.

## 0.1.1 — axis-aligned pulling and initial join fixes

- Remove diagonal rotation/shear. Horizontal and vertical deformation channels combine while keeping rectangle edges level, ellipses axis-aligned and capsule ends symmetric.
- Remove the normal-dependent connection gate that caused sharp overlap corners.
- Attenuate refraction where merged gradients cancel, removing unstable full-strength offsets in the join interior.
- 36 interpreter/compiler/import checks passed. Opened and rendered in the dedicated TurboWarp verification window.

## 0.1.0 — progress checkpoint

- Preserve the work present when versioned file management was requested: centered directional pull and the initial position-gated join/shading changes.
- This checkpoint predates the axis-aligned diagonal-pull correction.
- Older unnumbered snapshots remain historical diagnostics; they are not retroactively presented as tested releases.
