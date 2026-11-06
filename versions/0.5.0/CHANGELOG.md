# Liquid Glass revisions

Numbered archives are preserved before loading a modified project in TurboWarp. The first digit stays 0. Patch revisions include fixes and compatibility changes; middle-digit revisions change the rendering framework.

## 0.5.0 — layered menus and adjustable glass material

- Open a submenu from the chosen row, with its previous panel visible behind it. Child panels have their own animated bounds, labels and hit area. The header reverses the transition; choosing a leaf still sends its complete action path.
- Give each public component four additional inputs: tint color, transparency, brightness and blur radius. The renderer samples the refracted background for blur and keeps foreground labels sharp. Radius zero and a fully transparent coat recover the original optics.
- Apply different frosted defaults to the menu, button, sidebar and raw Glass examples. Studio's **Options → Menu finish** switches between Frosted, Clear and Smoked through the editable menu call.

## 0.4.1 — uniform control highlights

- Draw hover, pressed and selected highlights once across the entire control. Scratch's initial Pen point no longer produces a brighter disk at the start of the button or menu-row highlight.
- Each menu row uses one active highlight tone. A selected option keeps its checkmark while the pointer hovers over it.

## 0.4.0 — interactive UI components

- Add separate `Menu`, `Button` and `Background` custom blocks to Studio and the reusable sprite. The green flag shows one editable call for each control. **G** switches to the previous raw Glass demo.
- Add nested menu paths, a compact launcher or persistent panel, pagination, outside dismissal, header dragging, fixed-button hover/press/pull and noninteractive sidebar captions.
- Draw user-supplied labels and row indicators on changed frames. Capture short clicks during a render and send successful activations to other sprites via **UI activated**.
- Demonstrate switching the background and rendering detail through actual controls. Preserve the latest 0.3.0 native save as an input and clear the rebuildable field buffers after UI frames.

## 0.3.0 — stop the glass from flashing between frames

- Keep the displayed frame intact while Scratch calculates the next frame. Collect the original shaded strokes first, then restore and repaint only the affected background strips. The frame loop no longer issues `erase all` or stamps a full-stage costume over the glass.
- Skip painting entirely when every visible slot, optical setting, quality and background are unchanged. Invalidate incomplete work on reset.
- Preserve the three native `Glass` examples, component inputs, geometry, optics, current demo settings and the customized Stage backdrop from the latest native save. Apply the same fix to the standalone sprite.

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
