# Liquid Glass revisions

Numbered archives are preserved before loading a modified project in TurboWarp. The first digit stays 0. Patch revisions include fixes and compatibility changes; middle-digit revisions change the rendering framework.

## 0.7.3 — adjustable submenu timings

- Add one `submenu curve` input to **Menu** for four durations in seconds, ordered as open travel, open growth, Back travel, and Back growth. `inherit` uses the Menu’s opening settings for both directions. Dismissing the whole menu uses its universal close settings.

## 0.7.2 — match submenu opening and return timing

- Opening a submenu and folding it into its calling row use the same two settings on the Menu block: **open travel** for position and **open growth** for size. The shared title and chevron stay attached when the motion reverses.
- Dismissing the entire menu still uses **close travel** and **close growth**, including when nested panels are visible. The public blocks, example timings and previous release are preserved.
- Keep the title and chevron visible throughout the fold at standard Scratch resolution. The renderer uses bitmap samples for subpixel lettering so small vector samples cannot disappear during scaling.

## 0.7.1 — menu highlight placement, drag release and dimmed text

- Shift the expanded row highlight one local pixel left and give it two extra pixels of clearance at the top and bottom. The source capsule uses the same geometry when it grows into a submenu.
- Buttons and menu launchers show hover and press with motion; inner highlights are reserved for open menus. The optical rim and its public controls are unchanged.
- Apply the menu spring to anchored pulls, stretching and release. The first release frame retains the previous visible pose, and a reversed drag never shrinks the held button. Button exposes its own bounce setting; the Studio example matches the saved menu's 0.25.
- Keep the returning submenu title and chevron under the same spring until they settle, even after the panel has folded away. Apply opacity to the combined lettering so its joints do not brighten.
- Retain the author's last 0.7.0 editor save, including the menu placement and timings, alongside a separate copy of 0.7.0 as originally released.

## 0.7.0 — EffOnly refraction and spring-driven menus

- Restore the EffOnly quadratic rim displacement across Glass, Menu, Button, Background and nested panels. Rounded corners and merged shapes use a continuous direction field, and fractional backdrop coordinates interpolate between adjacent samples. At a two-pixel inset on the reference calibration rim, the UI displacement increases from 19.1 to 144.4 stage pixels.
- The five new Menu inputs control opening travel and growth, closing travel and growth, and bounce. Position and size carry their velocity through a reversal. The root launcher leads with travel by default.
- A submenu grows directly out of its selected row. The row label and its right-hand chevron move into the header together. The chevron turns down by 90 degrees and retraces that turn when the header is clicked.
- A pressed button or menu follows the drag gradually on each axis. Its stretch persists through direction changes, including when the pointer crosses the original press point. Release returns it to its resting dimensions and anchor.

## 0.6.0 — anchored motion, attached lettering and continuous pane optics

- Buttons and menus follow the pointer temporarily during a press and spring back on release. Their labels, icons and highlights move and stretch with the body.
- Root menus and submenus travel toward their destination before they finish growing. The Menu block accepts four directional corners, the existing bottom-center layout, or a custom expanded center in stage coordinates.
- Smooth rounded-corner refraction and separate the parent’s dimming from the light sampled by the foreground pane. This removes the hard cuts visible in the Clear submenu.
- Start from the native 0.5.0 editor save with its 34 × 34 circle launcher. Share identical rows in the calibration image so both exports retain room under Scratch’s size limit.

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
