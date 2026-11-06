# Liquid Glass revisions

Numbered archives are preserved before loading a modified project in TurboWarp. The first digit stays 0. Patch revisions change behavior; middle-digit revisions change the rendering framework.

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
