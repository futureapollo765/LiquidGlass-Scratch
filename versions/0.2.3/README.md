# Liquid Glass for Scratch

An editable Scratch 3 renderer for rounded rectangles, capsules and circles, with adjustable refraction, smooth geometry transitions, local glass connections and centered, axis-aligned drag deformation. Every component is configured through one `Glass …` custom block. The project uses standard Scratch blocks and the Pen extension; Python is only the build tool.

**Scratch editor compatibility (0.2.3)**

Version 0.2.3 repairs an internal list ID that caused the current vanilla Scratch palette to disappear or stack at the upper left. Blockly reserves `_field` and `_connection` inside block IDs; Scratch uses variable/list IDs for palette reporters. The old generated list ID `l_field` therefore triggered an exception. The list is still named `field`; only its internal ID and eight references change. The renderer, custom block inputs, native-editor customizations, comments, and saved data remain intact.

The builder now creates a safe ID when a generated storage ID contains either reserved substring, and the archive validator rejects those IDs. `tools/repair_editor_ids.py` repairs existing `.sb3`/`.sprite3` archives without rebuilding their programs. See [the source investigation](research/SCRATCH_EDITOR_COMPATIBILITY.md). For an already broken Scratch tab, refresh the editor before importing the corrected archive to clear its failed palette state.

**Open the demo**

1. Open `LiquidGlass_Studio.sb3` in TurboWarp Desktop and click the green flag.
2. Drag any of the three shapes. Move their edges close together to see a connecting neck, then separate them again.
3. Press `1`, `2` or `3` to change the main component to a rounded rectangle, capsule or circle. Press `Space` to expand/collapse it.
4. Press `P` to compare the centered pull on all three shapes at the same motion speed. The circle becomes an ellipse, while the rectangle and capsule lengthen and become thinner across the movement direction. Press `P` again to stop the motion and watch them settle.
5. Press `E` for effect sliders. Use `B` to switch between the reference photo and a calibration grid; the grid makes refraction and symmetric pulling easier to see.

| Control | Action |
| --- | --- |
| Drag | Move a component with symmetric X/Y deformation; diagonal motion combines both axes without rotation or shear. Release to let it settle. |
| `1` / `2` / `3` | Main component: rounded rectangle / capsule / circle. |
| `Space` | Expand or collapse the main component. |
| `M` | Toggle automatic movement of the neighboring circle. Turn it off for manual positioning. |
| `P` | Toggle a synchronized pull demonstration on all three components. Enabling it turns off `M` movement; turn it off before manual positioning. |
| `B` | Switch the shared background. |
| `Q` | Cycle pixel steps 1, 2 and 3. Step 1 is finest; larger steps are faster. |
| `E` | Show/hide the effect sliders. Step 4 is also available through the Quality slider or custom block. |
| `R` | Reset component positions and settings. |

**The one-block interface**

Select the **Liquid Glass** sprite and open **My Blocks**. Use this block for creation, updates, animation targets and hiding:

```text
Glass (id) x (x) y (y) width (width) height (height)
  shape (shape) radius (radius)
  reflection (reflection) distortion (distortion) edge (edge)
  highlight (highlight) light (light) tint (tint)
  join (join) group (group) transition (transition)
  spring (spring) damping (damping) pull (pull) drag (drag) quality (quality)
```

This is one Scratch custom block; the line breaks above make its inputs easier to read. In **LiquidGlass_Studio.sb3**, select the **Liquid Glass** sprite and its **Code** tab. The green-flag script is the first script at the upper left of the workspace. Its forever loop contains **three visible, filled-in `Glass` calls**, following `LG demo targets`. Edit those calls directly. Duplicate a call and change its ID to configure another component without editing the geometry, physics or rendering helpers. Variables and reporter blocks can be plugged into the inputs normally.

The Studio loop is `LG demo targets → Glass 1 → Glass 2 → Glass 3 → LG advance → LG render → wait 0`. `LG demo targets` supplies the keyboard-controlled dimensions and positions. The separate `LG demo` helper is retained for validation convenience; it is not the place you need to edit.

An `id` selects one of eight persistent component slots. Calling the same ID again updates its target and settings; it does not create a duplicate. New slots appear at their initial size and position. Existing visible slots animate toward new targets. Use another ID for another component.

| Input | Meaning and accepted values | Example |
| --- | --- | --- |
| `id` | Slot 1–8; rounded and clamped to this range. | `1` |
| `x` | Target center x in Scratch stage coordinates. | `-70` |
| `y` | Target center y in Scratch stage coordinates. | `10` |
| `width` | Full width in stage pixels, 8–440. For a circle this is its **diameter**. | `156` |
| `height` | Full height, 8–300. Ignored for a circle, whose height becomes its width. | `96` |
| `shape` | `1` or `rounded rectangle`; `2` or `capsule`; `3` or `circle`; `0` or `hidden` to remove the slot from rendering and hit testing. | `1` |
| `radius` | Rounded-rectangle corner radius in pixels, clamped to 0…half the smaller dimension. Capsule and circle radii are calculated automatically. | `24` |
| `reflection` | EffOnly edge-refraction profile, 0–1. Sets how far the refracting band extends into the shape as a fraction of its half-thickness. | `0.5` |
| `distortion` | Refraction multiplier, −3…3. `0` disables displacement; negative values reverse its direction. | `1` |
| `edge` | Highlight rim thickness, 0–6 pixels. `0` removes the rim. Rendering resolution also affects visible edge softness. | `1` |
| `highlight` | Rim brightness multiplier, 0–3. | `1` |
| `light` | Highlight-axis angle in degrees from the positive x direction. The highlight has opposing lobes. | `-30` |
| `tint` | Amount of the fixed pale blue-white tint, 0–0.75. `0` leaves the sampled background untinted. | `0.05` |
| `join` | Nominal connecting distance in pixels, 0–60. `0` disables this component's connections. Direction and bounds gates reduce the effective reach near some corners. | `30` |
| `group` | Components with the same nonzero value can merge. `0` isolates a component. Both participants must have a positive `join`. | `1` |
| `transition` | Approximate settling time for width/height/radius, 0–3 seconds. Positive values enable spring movement; `0` snaps geometry and position and clears movement velocity. | `0.45` |
| `spring` | Position response rate, 1–40; higher values follow the target more quickly. This is a response parameter, not a frequency in Hz. | `18` |
| `damping` | Spring damping, 0.1–2. Lower values bounce more; values around 1 settle with little overshoot. | `0.85` |
| `pull` | Strength of centered, velocity-driven X/Y stretch and cross-squeeze, 0–2. `0` lets the existing deformation relax to zero. Use a positive `transition` for drag-generated pulling. | `0.9` |
| `drag` | `1` enables grabbing; `0` disables it. The grab offset is preserved. | `1` |
| `quality` | Pixel step 1–4, rounded. Smaller is finer and slower. The smallest active component value sets the shared rendering grid. | `2` |

For a 96-pixel circle, use `width=96`, `shape=3`; changing the radius input does not alter that circle. For a 176×44 capsule, use those full dimensions and `shape=2`; its end radius is 22. A rounded rectangle with the same dimensions and `radius=10` has visibly smaller corner curves.

A useful initial call is:

```text
Glass (1) x (-70) y (10) width (156) height (96)
  shape (1) radius (24)
  reflection (0.5) distortion (1) edge (1)
  highlight (1) light (-30) tint (0.05)
  join (30) group (1) transition (0.45)
  spring (18) damping (0.85) pull (0.9) drag (1) quality (2)
```

To expand it, call `Glass` again with `id=1`, `width=238`, `height=146`, `shape=1` and the desired other settings. To turn it into a circle, call the same ID with `width=96`, `shape=3`. Hiding with `shape=0` is immediate; showing a hidden slot starts at its newly supplied geometry.

**Import into another Scratch project**

`LiquidGlass_Component.sprite3` is a clean reusable component. It contains the renderer, its custom blocks, local state, background costumes and matching RGB lists, plus **one visible example `Glass` call**. The Studio keyboard scripts and demo helpers are excluded.

1. Choose **Upload Sprite** and import `LiquidGlass_Component.sprite3`.
2. Select the imported **Liquid Glass** sprite and its **Code** tab. Find the green-flag script at the upper left. It already contains `LG initialize`, a filled-in `Glass (1)` call, then the rendering loop shown below.
3. **Edit the inputs of that visible `Glass` call.** Duplicate the call with IDs 2–8 for more components. Keep these initial calls before the forever loop. No helper definitions need editing.
4. Add later calls for an existing ID when your UI needs a new target. The optional guide sprite belongs to the full Studio `.sb3` and is not required by the component.

```text
when green flag clicked
  LG initialize
  Glass (...)       // component 1: fill all inputs
  Glass (...)       // component 2, if needed
  forever
    LG advance
    LG render
    wait (0) seconds
```

The comments in this example are explanatory text, not additional Scratch blocks. `LG initialize` must run before the first `Glass` call and resets all eight slots. Do not call it every frame. The components retain their configuration between calls, so an unchanged `Glass` call does not have to run every frame.

For normal drag behavior, issue position targets at setup or when they change. Reissuing a call with fixed x/y values every frame replaces the position saved by dragging, so the component will return to those fixed coordinates after release. The Studio demo can update every frame because its position inputs are variables that the drag handler also updates.

Scratch custom blocks belong to their sprite. Place component calls in the **Liquid Glass** sprite. Other sprites can broadcast an application event such as `open menu`; an event handler in **Liquid Glass** then calls the same `Glass` block with the new dimensions and settings. Use one renderer sprite for the scene, with its eight slots, rather than importing multiple competing renderer copies.

**How the effects work**

The optical profile follows `LiquidGlassRenderer_EffOnly.sb3`: refraction increases quadratically toward the border, using the equivalent of `distortion × max(0, reflection × halfThickness − depth)² / 10`. Background samples are displaced along the merged contour normal. Reflection 0.5, edge 1 and light −30 preserve the reference's default control values. Additional inputs control displacement strength, rim brightness and tint. Sample coordinates are clamped to avoid wrapping into the next image row.

The shape family follows the signed-distance formulas in V1.7 and V7. A capsule uses the rounded-rectangle formula with its radius set to half the shorter dimension; a circle is the equal-width/height case. Interpolating dimensions and corner radius gives a continuous expandable-menu transition.

Connections use a compact polynomial smooth union with four smooth position gates at the pair bounds. Blending stays active through overlapping sides and corners: it never depends on an individual shape's normal, which can change abruptly inside the shape. This removes the sharp rectangle/circle junctions. Smoothing fades continuously near coincident centers, and resting connections stay inside the original overall bounds. Remote surfaces outside the compact blend remain exact; nearby shoulders can change locally to make the join smooth.

Starting in `0.2.0`, each eligible connection group is blended as a whole, in stable ascending component-ID order. The distance field and all optical properties use the same smooth weights. This avoids switching between competing pairs when three or more shapes overlap. Group `0`, or a component with `join=0`, remains isolated. Light's opposing highlight lobes are blended using doubled-angle components, so equivalent angles such as 0° and 180° retain the same appearance.

The shader also fades the refraction displacement where opposing field gradients cancel. A near-zero gradient can no longer be normalized into a full-strength, unstable texture offset. Ordinary border gradients retain the EffOnly profile.

Pulling uses separate, centered transforms on the **stage X and Y axes**: `x′ = scaleX × x`, `y′ = scaleY × y`. There are no off-diagonal terms. Rectangular sides stay horizontal/vertical, circles become axis-aligned ellipses, and capsules do not rotate or shear during diagonal dragging. The configured width, height and radius remain unchanged; inverse coordinate sampling and transformed normals make the contour, rim and refraction follow the deformation.

Pure horizontal movement stretches X and reciprocally squeezes Y; pure vertical movement does the reverse. When both directions move, cross-squeeze fades smoothly so the two stretch channels combine instead of cancelling. Equal diagonal motion activates both axes. The stretch cap is 1.65 per axis, and `pull` controls the response strength. Pure-axis pulling preserves continuous area; combined diagonal stretching intentionally does not impose that restriction. The spring and pull smoothing let the shape recover after release.

**Practical limits**

- The current background is a static 480×360 RGB image paired with a matching costume: the source photo or the calibration grid. The renderer does not capture arbitrary live sprites, pen drawings or video behind it. Replacing only a costume or stage backdrop does not update the refraction data; a new background needs matching RGB data as well.
- Pen is one shared canvas. Each render clears it and stamps the background, so coordinate other pen drawing with this renderer. Ordinary foreground sprites can sit above the glass, but they are not included in its sampled background.
- Rendered shapes are clipped by the 480×360 stage. The demo drag area is x −220…220 and y −150…125; large shapes can still extend offscreen. Programmatic target positions use the supplied x/y values.
- Eight slots are available. Rendering cost increases with covered area, active components and connections. TurboWarp's compiler is recommended; native Scratch execution is slower. Pixel steps 2–3 are useful for interaction, while step 1 is best for detailed inspection. Results depend on the machine and scene; no fixed frame rate is promised.
- Resting connections preserve overall group bounds. During pulling, conservative deformation bounds permit the intentional contour stretch. Multiple-component blending follows stable ID order; changing ID order can slightly change a multiway join. The algorithm is an Apple-inspired Scratch implementation, not Apple's proprietary Liquid Glass shader or a claim of identical behavior.

**Keep project.json below the Scratch upload limit**

Scratch documents a 5 MB `project.json` limit in its [official help center](https://mitscratch.freshdesk.com/en/support/solutions/articles/4000156781-how-do-i-reduce-or-check-my-project-s-size-).

Version `0.2.1` is a data-only cleanup of the latest native editor save. Its `project.json` is **3,231,258 bytes**, down from **8,452,882 bytes**. Only the saved contents of eight per-frame lists were emptied: `field`, `pixelBand`, `pixelDistortion`, `pixelEdge`, `pixelHighlight`, `pixelLightX`, `pixelLightY`, and `pixelTint`. Every list definition, Scratch block, scalar variable, component setting, fixed eight-slot cache, RGB lookup list and asset was preserved from that input.

These buffers are cleared and rebuilt by the existing initialization/rendering code. The RGB lists are required background data and are intentionally retained. The fixed eight-slot caches must not be emptied: Scratch's `replace item` does not allocate missing slots.

Running the renderer fills the buffers again. The existing **Stop → R → Save** workflow clears them without adding any blocks; **R also resets the demo/component state to its existing defaults**. For a cleanup that preserves every saved setting, use the export tool below instead.

 If a later exported project grows too large, clean the saved export without changing any Scratch scripts:

```sh
python3 tools/compact_project.py saved-project.sb3 saved-project-clean.sb3
```

The tool preserves its input and refuses to overwrite an existing output unless `--overwrite` is explicitly supplied. It only clears the eight named frame buffers, checks that the existing initialization/render procedures clear them, verifies that all other project data and assets are unchanged, and rejects an output whose JSON still reaches 5,000,000 bytes.

For `0.2.1`, the exact starting editor save and cleanup report are preserved with the numbered version. Reproduce this data-only cleanup with `compact_project.py`; `build_renderer.py` remains the original block generator and would recreate its original demo configuration rather than retain later native-editor edits.

**Files and reproducibility**

| File | Purpose |
| --- | --- |
| `LiquidGlass_Studio.sb3` | Complete editable demo. |
| `LiquidGlass_Component.sprite3` | Clean importable renderer with one editable setup call; no Studio keyboard scripts or demo helpers. |
| `EditorVerified.sb3` | Historical native-editor snapshot from before numbered releases; not the latest renderer. |
| `versions/` | Preserved numbered projects, components, build source, documentation and SHA-256 manifests. |
| `VERSION` / `CHANGELOG.md` | Latest build number and revision history. |
| `LiquidGlass_Studio.project.json` | Unzipped project data for inspection. |
| `build_renderer.py` | Rebuilds native Scratch blocks and archives from the EffOnly source. |
| `tools/validate_sb3.py` | Checks archive assets, block links, variables, lists and procedure signatures. |
| `tools/vm_harness.cjs` | Loads and executes blocks with the real VM bundled in TurboWarp Desktop. |
| `tools/check_geometry.py` | Independent numerical checks of the pull, shapes and bounded connections. |
| `research/REFERENCE_ANALYSIS.md` | Analysis of the supplied V1.7, V5 and V7 projects. |
| `research/GEOMETRY_OBSERVATIONS.md` | Numerical geometry results and their limits. |

The original `.sb3` files are not modified. Rebuilding requires the source path declared at the top of `build_renderer.py`; running the finished `.sb3` or `.sprite3` does not require Python or access to the originals.

```sh
python3 build_renderer.py
python3 tools/validate_sb3.py LiquidGlass_Studio.sb3
python3 tools/check_geometry.py
node tools/vm_harness.cjs LiquidGlass_Studio.sb3 2
```

**Versioned updates**

Every build now preserves a new directory under `versions/` **before it is opened in TurboWarp**. Open the numbered `.sb3` for an unambiguous window title. The unversioned root `.sb3` and `.sprite3` remain convenient copies of the latest build. Existing numbered files are never overwritten.

- Ordinary updates increment the last digit, such as `0.1.0 → 0.1.1`.
- Major framework changes increment the middle digit and reset the last digit, such as `0.1.1 → 0.2.0`.
- The first digit remains `0` under your control.

`python3 build_renderer.py` builds and snapshots the next patch. `python3 build_renderer.py --minor` builds and snapshots the next framework revision. Each snapshot contains both Scratch artifacts, the generated project JSON, build source, documentation and a hash manifest. Native editor saves used for verification are stored separately from these preserved source archives.

**Verification status**

`0.2.1` passed all 42 runtime/import checks after clearing the saved buffers. The buffers regenerate with matching, finite data. Structural validation passed without warnings. An exact comparison verifies that only the eight saved list-content arrays changed; all other JSON data and all asset bytes match the latest native editor input.

`0.1.1` passed 36 headless runtime/import checks in the Scratch interpreter and TurboWarp compiler. These include pure-axis and diagonal deformation, axis-aligned ellipse normals, level rectangle/capsule sides, pointer interaction, recovery, joins, and refraction stability. The numbered build was also opened and rendered through its visible green-flag loop in TurboWarp Desktop. Automated pointer gestures can occur between rendered frames, so they are supplemented by sustained pointer tests in the VM and the user's live visual feedback.

The `0.2.0` group-blending framework passed **42 runtime/import checks** on both the generated source and the copy saved by TurboWarp Desktop. Native save/reopen preserved all 12 custom procedure definitions and all nonprimitive opcode counts, with clean archive, reference and Boolean-socket validation. Four additional native-copy smoke checks passed. The visible green-flag loop, running two-shape joining and expanded multi-shape scene were inspected on stage. See `versions/0.2.0/validation/summary.json` for the tested hashes and `versions/0.2.0/EditorVerified_0.2.0.sb3` for the native editor output. Earlier root `native_editor_*.json` reports refer to the historical unnumbered snapshot.

Independent geometry audits cover tangent continuity at mixed-shape joins, exact remote-edge behavior, bounded connections, axis-aligned pulling and multiway material continuity. See `research/geometry_validation.json`, `research/grazing_boundary_audit.json`, and `research/nary_blend_audit.json`. Headless tests verify the actual block calculations; native TurboWarp checks verify loading, editable scripts and on-stage rendering.

Invalid intermediate editor-save snapshots are isolated in `research/diagnostics/` with an explanatory note. They are not deliverables.

The block format and custom-block wiring are based on the primary [Scratch SB3 serializer/deserializer](https://github.com/scratchfoundation/scratch-vm/blob/develop/src/serialization/sb3.js), [custom procedure primitives](https://github.com/scratchfoundation/scratch-vm/blob/develop/src/blocks/scratch3_procedures.js) and [native Pen extension](https://github.com/scratchfoundation/scratch-vm/blob/develop/src/extensions/scratch3_pen/index.js), together with the supplied project blocks. The finished archives contain standard Scratch data and assets, with no JavaScript runtime, custom shader or external extension.
