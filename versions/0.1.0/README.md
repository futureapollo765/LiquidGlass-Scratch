# Liquid Glass for Scratch

An editable Scratch 3 renderer for rounded rectangles, capsules and circles, with adjustable refraction, smooth geometry transitions, local glass connections and centered, symmetric drag deformation. Every component is configured through one `Glass …` custom block. The project uses standard Scratch blocks and the Pen extension; Python is only the build tool.

**Open the demo**

1. Open `LiquidGlass_Studio.sb3` in TurboWarp Desktop and click the green flag.
2. Drag any of the three shapes. Move their edges close together to see a connecting neck, then separate them again.
3. Press `1`, `2` or `3` to change the main component to a rounded rectangle, capsule or circle. Press `Space` to expand/collapse it.
4. Press `P` to compare the centered pull on all three shapes at the same motion speed. The circle becomes an ellipse, while the rectangle and capsule lengthen and become thinner across the movement direction. Press `P` again to stop the motion and watch them settle.
5. Press `E` for effect sliders. Use `B` to switch between the reference photo and a calibration grid; the grid makes refraction and symmetric pulling easier to see.

| Control | Action |
| --- | --- |
| Drag | Move a component while both ends stretch equally and its cross-section becomes thinner; release to let it settle. |
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
| `pull` | Strength of centered, velocity-driven stretch and reciprocal sideways squeeze, 0–2. `0` lets the existing deformation relax to zero. Use a positive `transition` for drag-generated pulling. | `0.9` |
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

Connections adapt the polynomial smooth union used by the reference projects. A directional gate confines blending to facing surfaces; four smooth bounds gates stop a resting pair's union from extending beyond its original overall bounds. Coincident centers bypass blending, and original remote border arcs stay unchanged. The entire connected result is shaded as one field, so the join does not retain internal glass rims. A smooth connection also blends the two components' material settings continuously; outside a smooth connection, the nearest component supplies the material.

Pulling uses a centered directional transform of the whole shape. In coordinates along and across the motion, the forward mapping is `s′ = stretch × s` and `t′ = t / stretch`, where `stretch = 1 + amplitude / axialExtent` and is capped at 1.65. Opposite sides deform equally around the component's current center: a circle becomes an exact ellipse, a rectangle becomes longer and thinner as a whole, and both ends of a capsule elongate equally. There is no front-to-back taper.

The configured width, height and corner radius remain unchanged. The renderer applies the inverse coordinate mapping to the contour and the inverse-transpose mapping to its normals, so the rim and background refraction follow the pulled geometry together. Stretch and reciprocal compression preserve continuous area; the transform's Jacobian determinant is 1. Velocity smoothing and damped movement let the deformation recover after release. Pixel rasterization and anti-aliasing introduce small discrete area differences.

**Practical limits**

- The current background is a static 480×360 RGB image paired with a matching costume: the source photo or the calibration grid. The renderer does not capture arbitrary live sprites, pen drawings or video behind it. Replacing only a costume or stage backdrop does not update the refraction data; a new background needs matching RGB data as well.
- Pen is one shared canvas. Each render clears it and stamps the background, so coordinate other pen drawing with this renderer. Ordinary foreground sprites can sit above the glass, but they are not included in its sampled background.
- Rendered shapes are clipped by the 480×360 stage. The demo drag area is x −220…220 and y −150…125; large shapes can still extend offscreen. Programmatic target positions use the supplied x/y values.
- Eight slots are available. Rendering cost increases with covered area, active components and connections. TurboWarp's compiler is recommended; native Scratch execution is slower. Pixel steps 2–3 are useful for interaction, while step 1 is best for detailed inspection. Results depend on the machine and scene; no fixed frame rate is promised.
- Resting connections preserve overall pair bounds. During pulling, conservative deformation bounds permit the intentional contour stretch. An unusual overlap where a surface normal is exactly perpendicular to the line between centers can retain an existing union corner. The algorithm is an Apple-inspired Scratch implementation, not Apple's proprietary Liquid Glass shader or a claim of identical behavior.

**Files and reproducibility**

| File | Purpose |
| --- | --- |
| `LiquidGlass_Studio.sb3` | Complete editable demo. |
| `LiquidGlass_Component.sprite3` | Clean importable renderer with one editable setup call; no Studio keyboard scripts or demo helpers. |
| `EditorVerified.sb3` | Earlier Studio snapshot saved and reopened through the native TurboWarp editor; see the version scope below. |
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

**Verification status**

The current build contains the revised symmetric pull and the new `P` demonstration. Verification is being refreshed for this revision. Previous results described below establish the earlier build's behavior and must not be read as a completed check of the revised pull.

Before this revision, Studio and the clean component passed 29 automated checks in the Scratch interpreter and TurboWarp compiler, including component import, the green-flag scheduler, shape transitions, bounded connections, material blending and simulated pointer interaction. These are **headless VM checks**, distinct from visual observations. See the artifact hashes in `research/runtime_validation.json` and the harness description in `tools/README.md` to identify the tested build.

The earlier build was also opened in the native TurboWarp editor, where the green-flag stack and three direct `Glass` calls were visible. Its shape modes (`1`/`2`/`3`) and `Space` expansion were visually checked, and its `EditorVerified.sb3` save was reopened successfully. Procedure preservation, archive validation and four additional runtime checks passed for that saved snapshot. The new symmetric-pull build still needs its own native save/reopen and visual drag checks; the earlier snapshot is not the current revised deliverable. See `research/native_editor_structure.json`, `research/native_editor_verified_validation.json` and `research/native_editor_runtime.json` for the earlier artifact hashes.

The independent geometry tests and notes are in `tools/check_geometry.py`, `research/geometry_validation.json` and `research/GEOMETRY_OBSERVATIONS.md`. Pull-specific results need to match the revised centered transform before they can be used to validate this version.

Invalid intermediate editor-save snapshots are isolated in `research/diagnostics/` with an explanatory note. They are not deliverables.

The block format and custom-block wiring are based on the primary [Scratch SB3 serializer/deserializer](https://github.com/scratchfoundation/scratch-vm/blob/develop/src/serialization/sb3.js), [custom procedure primitives](https://github.com/scratchfoundation/scratch-vm/blob/develop/src/blocks/scratch3_procedures.js) and [native Pen extension](https://github.com/scratchfoundation/scratch-vm/blob/develop/src/extensions/scratch3_pen/index.js), together with the supplied project blocks. The finished archives contain standard Scratch data and assets, with no JavaScript runtime, custom shader or external extension.
