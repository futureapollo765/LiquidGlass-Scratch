# Liquid Glass for Scratch

An editable Scratch 3 UI kit with a glass menu, button and sidebar background. Each control has its own custom block on the **Liquid Glass** sprite. They use the same `Glass` renderer for refraction, shape transitions, connections and axis-aligned pulling. The projects run with standard Scratch blocks and the Pen extension.

**Run the UI demo**

Open Studio and click the green flag. The circular **…** launcher opens **Options**. Choose **Background → Grid** to change the wallpaper. **Switch background** toggles it directly. Press and pull either control to feel it follow your pointer, then release to watch it settle back to its configured position. Press **G** to switch between the UI and the original three-shape renderer demo.

In **0.7.4**, hold **Switch background**, **Options**, or an open menu panel. Drag right to stretch it, move halfway back for a smaller stretch, then return to where you pressed. The control settles to its original pressed size without a release. Keep dragging left and it stretches left. The same works vertically and diagonally, even when the press starts near an edge.

In **0.7.3**, the last input on **Menu**, `submenu curve`, accepts four comma-separated durations in seconds. Their order is **open travel, open growth, Back travel, Back growth**. For example, `0.4,0.6,0.8,0.3` opens a submenu with 0.4 s of travel and 0.6 s of growth. Clicking its header folds it back with 0.8 s of travel and 0.3 s of shrinkage. The default, `inherit`, uses the Menu’s open travel and open growth in both directions. Clicking outside or choosing a leaf minimizes the whole menu using its universal close settings.

In **0.7.2**, a submenu and the whole menu have different return timings. Click **Options → Menu finish**, then click the **Menu finish** header. That panel folds into its own row using the same **open travel** and **open growth** settings that unfolded it. Click outside the menu or choose a leaf such as **Smoked** to minimize the whole menu to **…**; this uses **close travel** and **close growth**. The same rule applies at every submenu depth. There are no new inputs.

In **0.7.1**, a button or menu carries its motion through release. The button keeps the last pose you saw as you let go, then springs back. Set the last **bounce** input on either control to tune the feel (0–0.70). Try reversing direction during a pull: the button stays stretched instead of squeezing as the pointer crosses it. The saved Studio example uses **0.25** for both controls.

Open **Options → Menu finish**, then click the **Menu finish** header to fold it back. The same title and arrow follow the spring past their original row before settling. Only open menu rows use a translucent inner highlight. It sits one stage pixel farther left and has two extra pixels of clearance above and below at rest; these offsets scale with the panel. A button or closed launcher shows hover through motion. Its optical rim remains configurable.

In **0.7.0**, position and size have independent springs. The center leads expansion by default. When you close the menu, its body contracts while its center travels back to the launcher. If you change direction mid-animation, both springs carry their current velocity into the return.

The timing inputs at the end of the **Menu** custom block control the springs.

| Input | Default | Controls |
| --- | ---: | --- |
| `open travel` | 0.52 s | Travel when opening a menu, and when folding a submenu back into its calling row. |
| `open growth` | 0.84 s | Size change when opening a menu, and when folding a submenu back into its calling row. |
| `close travel` | 0.72 s | Travel when minimizing the whole menu to its launcher. |
| `close growth` | 0.46 s | Size change when minimizing the whole menu to its launcher. |
| `bounce` | 0.30 | Spring character. Zero gives a smooth approach from rest. The default has a small overshoot. |
| `submenu curve` | `inherit` | Four durations for submenu opening and Back, in the order shown above. |

Each duration accepts **0–4 seconds**. Zero moves that property immediately. These are perceptual durations, so a small settling motion can continue past the specified time. Bounce accepts **0–0.70**. Tune duration first and bounce second. [Apple’s *Animate with springs*](https://developer.apple.com/videos/play/wwdc2023/10158/)

The defaults above apply to a new block. The saved Studio example places **Options** at (120, 102), aligns it to **bottom left**, and uses **0.40 / 0.60 / 0.60 / 0.40** seconds for the four durations.

Click **… → Menu finish** to see the submenu exception. Its highlighted row becomes the child panel. The same label moves into the header, and its right chevron turns down through 90 degrees. Click the header to fold the panel back into the row using its Back timings. Press at either end of **Switch background**, drag across it and reverse while holding. The button stretches with the gesture and returns to its anchor and resting dimensions on release.

The **Menu** custom block has three placement inputs after `blur`. Set `alignment` to **bottom left**, **bottom right**, **top left**, or **top right** for the direction the menu should grow from the launcher. **Bottom center** keeps the panel centered below the button. **Custom** uses `expanded x` and `expanded y` as the final **center of the root panel** in Scratch stage coordinates. For example, `custom`, `-105`, `40` puts its center at (−105, 40), subject to the stage bounds. Nested panels open from their calling rows. The `drag` input on Menu enables an elastic pull and release back to its anchor.

In **0.5.0**, try **Options → Menu finish → Smoked**, then reopen Options. Compare it with **Frosted** or **Clear** on the grid: the grid remains sharp outside the control while its lines soften inside the frosted glass. Each submenu grows from the row you select. The previous panel recedes and dims behind it. Use the child's header to return one level, or click outside to dismiss the launcher menu.

| Custom block | What to configure |
| --- | --- |
| `Menu` | Set its ID, launcher position and shape, panel dimensions and placement, row height, options, opening mode and elastic pulling. The open menu is a rounded rectangle. |
| `Button` | Set its ID, fixed position, label, action, shape and dimensions. `auto` chooses a circle for a single character, a capsule for a short caption and a rounded rectangle for a longer caption. Width `0` sizes the button from the label. |
| `Background` | Set its ID, fixed position, dimensions, corner radius and optional caption. Separate caption lines with `|`, for example `Workspace|Photo|Balanced`. The panel takes no pointer input. |

Each block exposes reflection, distortion, edge, highlight, light angle, tint, quality and four material inputs. Interactive components also expose pull and connection settings. Give each instance its own ID from 1 through 8. Edit the three filled-in calls under the main green flag, or duplicate a call and assign another ID. Submenus share their owner's material and do not take another public ID.

| Material input on `Glass`, `Menu`, `Button` and `Background` | What it changes |
| --- | --- |
| `tint color` | Color of the glass coat. Enter a six-digit hex color such as `#414B59`, or a packed RGB number. |
| `transparency` | How much background shows through that color. **0** gives a solid-colored body; **100** removes the colored coat. Existing optical edges and highlights still apply. |
| `brightness` | Brightens or darkens the sampled backdrop before the coat is applied. **0** preserves it; **−100** goes to black and **100** goes to white. |
| `blur` | Background blur radius in stage pixels, **0–20**, including fractional values. **0** keeps the source sharp. Foreground labels, icons and the rest of the stage stay sharp. |

For example, a graphite menu can use `#292A32 / 46 / -12 / 12` in those four sockets. For the original optical model use `100 / 0 / 0` for transparency, brightness and blur; the earlier pale `tint`, distortion and rim inputs still work independently. In Studio, **Menu finish** changes only the sample menu. Its four variable reporters can be replaced with constants or your own reporters directly in the green-flag call.

Open menu rows draw a single inner highlight. A press takes precedence over hover, and hover takes precedence over the selection tint. The checkmark continues to show the selected option. Labels dim as whole glyphs, so the places where their strokes meet no longer brighten as the parent menu fades.

For a menu, `|` separates options and `>` opens a submenu. For example, `Open|Sort>Name|Sort>Date` displays **Open** and **Sort** at the first level, then **Name** and **Date** under **Sort**. Set mode to `toggle` for a closed launcher, `open` to start expanded, or `panel` to keep the menu open. The menu header takes you back from a submenu. Click outside a collapsible menu to dismiss it.

When a button or a leaf option is activated, the renderer broadcasts **UI activated**. The **UI source** variable identifies the slot. **UI action** is the button's action input or a menu leaf's full path, such as `Sort>Date`. Other sprites can read these with Scratch’s **(attribute) of (Liquid Glass)** reporter inside a **when I receive [UI activated]** script.

The UIEngine2.4 reference keeps buttons anchored, eases dimensions and corner radius separately, and latches a press so a held mouse does not repeatedly select. The new controls use the existing glass renderer to express those interactions. Opening a menu from its own launcher follows Apple's demonstration of the material. [Meet Liquid Glass](https://developer.apple.com/videos/play/wwdc2025/219/)

The parent and child are distinct optical layers. The child's source row supplies its opening position, while the parent stays in place enough to show where the choice came from. A larger surface uses a more frosted default than the compact button. These choices follow Apple's discussion of menu origins, softer scattering on larger glass surfaces, and keeping overlaid content legible. [Apple's Liquid Glass dynamics and adaptivity](https://developer.apple.com/videos/play/wwdc2025/219/)

The sidebar occupies the leading edge and lets the scene show through. The demo groups related menu actions one level deep and uses short button labels. [Apple HIG materials](https://developer.apple.com/design/human-interface-guidelines/materials) · [Sidebars](https://developer.apple.com/design/human-interface-guidelines/sidebars) · [Menus](https://developer.apple.com/design/human-interface-guidelines/menus) · [Buttons](https://developer.apple.com/design/human-interface-guidelines/buttons)

**Rendering in vanilla Scratch (0.3.0)**

The three `Glass` calls update the components. `LG render` draws them together. It keeps the last picture on stage while calculating a new one, then restores the affected background in eight-pixel strips and paints the finished glass rows in their original order. It never erases the whole Pen layer to start a frame. If the geometry, effects and background are unchanged, it leaves the displayed picture alone. This matters in vanilla Scratch and in TurboWarp with **Disable Compiler** checked: a long custom block can yield before its work is finished, even with **Run without screen refresh** enabled.

**Scratch editor compatibility (0.2.3)**

Version 0.2.3 repairs an internal list ID that caused the current vanilla Scratch palette to disappear or stack at the upper left. Blockly reserves `_field` and `_connection` inside block IDs; Scratch uses variable/list IDs for palette reporters. The old generated list ID `l_field` therefore triggered an exception. The list is still named `field`; only its internal ID and eight references change. The renderer, custom block inputs, native-editor customizations, comments, and saved data remain intact.

The builder now creates a safe ID when a generated storage ID contains either reserved substring, and the archive validator rejects those IDs. `tools/repair_editor_ids.py` repairs existing `.sb3`/`.sprite3` archives without rebuilding their programs. See [the source investigation](research/SCRATCH_EDITOR_COMPATIBILITY.md). For an already broken Scratch tab, refresh the editor before importing the corrected archive to clear its failed palette state.

**Try the raw renderer (G)**

1. Open `LiquidGlass_Studio.sb3`, click the green flag, and press **G** for the three-shape demo.
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

**Raw Glass interface**

Select the **Liquid Glass** sprite and open **My Blocks**. Use this block for creation, updates, animation targets and hiding:

```text
Glass (id) x (x) y (y) width (width) height (height)
  shape (shape) radius (radius)
  reflection (reflection) distortion (distortion) edge (edge)
  highlight (highlight) light (light) tint (tint)
  join (join) group (group) transition (transition)
  spring (spring) damping (damping) pull (pull) drag (drag) quality (quality)
  tint color (tint color) transparency (transparency) brightness (brightness) blur (blur)
```

This is one Scratch custom block; the line breaks above make its inputs easier to read. In **LiquidGlass_Studio.sb3**, select the **Liquid Glass** sprite and its **Code** tab. The green-flag script is the first script at the upper left of the workspace. Its forever loop contains **three visible, filled-in `Glass` calls**, following `LG demo targets`. Edit those calls directly. Duplicate a call and change its ID to configure another component without editing the geometry, physics or rendering helpers. Variables and reporter blocks can be plugged into the inputs normally.

In the raw renderer branch the loop is `LG demo targets → Glass 1 → Glass 2 → Glass 3 → LG advance → LG render → wait 0`. `LG demo targets` supplies the keyboard-controlled dimensions and positions. The separate `LG demo` helper is retained for validation convenience; it is not the place you need to edit.

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
  tint color (#748397) transparency (84) brightness (2) blur (6)
```

To expand it, call `Glass` again with `id=1`, `width=238`, `height=146`, `shape=1` and the desired other settings. To turn it into a circle, call the same ID with `width=96`, `shape=3`. Hiding with `shape=0` is immediate; showing a hidden slot starts at its newly supplied geometry.

**Import into another Scratch project**

1. Choose **Upload Sprite** and import `LiquidGlass_Component.sprite3`.
2. Select **Liquid Glass → Code**. Edit the `Background`, `Button` and `Menu` calls in the first branch of its green-flag loop. Duplicate a call with a new ID for another instance, or remove a call to hide that UI slot on the next frame.
3. In another sprite, add **when I receive [UI activated]**. Use **([UI action] of [Liquid Glass])** for the chosen action and **([UI source] of [Liquid Glass])** for the component ID. The Studio example switches photo/grid and quality settings. In an imported project, connect this event to your own actions.
4. For short taps during a heavy render, copy this Stage script from Studio: **when stage clicked → broadcast [LG UI pointer down]**. The imported sprite also polls the mouse independently. The Stage hat additionally captures presses that begin and end between two mouse samples.

The UI branch configures the visible controls each frame, processes input, advances their motion and renders the scene. The renderer draws the foreground labels after the glass. Keep the component calls in the **Liquid Glass** sprite and reuse the existing loop when editing an instance. **G** switches the imported sprite to a raw `Glass` example and back to the UI kit.

The background, glyphs, icons, configuration and logic travel together in the one sprite. Labels support printable ASCII, accented Latin characters and common UI symbols. An unsupported character displays a square, and captions that exceed the available width end with an ellipsis. Long menus offer **More…** to cycle through additional options.

**How the effects work**

The renderer uses the quadratic falloff from the **Reflection** block in `LiquidGlassRenderer_EffOnly.sb3`. Its background sample moves inward by `distortion × max(0, reflection × halfThickness − depth)² / 10` along the local surface direction. This gives the original strong displacement on a straight edge and a smoothly changing direction around rounded corners. Fractional source coordinates blend neighboring backdrop pixels. A child pane samples the underlying glass before the parent’s interaction dimming is applied. Separating the distance a sample moves from the direction it moves is also used in Kube’s implementation. [Liquid Glass in the Browser](https://kube.io/blog/liquid-glass-css-svg/)

To compare the rim on the included demo, choose **Options → Background → Grid**, then **Options → Menu finish → Clear**. The straight grid lines make it easy to see where the lens bends the image. Increase `reflection` for a wider rim, or increase `distortion` to move the sample farther within the same rim.

The shape family follows the signed-distance formulas in V1.7 and V7. A capsule uses the rounded-rectangle formula with its radius set to half the shorter dimension; a circle is the equal-width/height case. Interpolating dimensions and corner radius gives a continuous expandable-menu transition.

Connections use a compact polynomial smooth union with four smooth position gates at the pair bounds. Blending stays active through overlapping sides and corners: it never depends on an individual shape's normal, which can change abruptly inside the shape. This removes the sharp rectangle/circle junctions. Smoothing fades continuously near coincident centers, and resting connections stay inside the original overall bounds. Remote surfaces outside the compact blend remain exact; nearby shoulders can change locally to make the join smooth.

Starting in `0.2.0`, each eligible connection group is blended as a whole, in stable ascending component-ID order. The distance field and all optical properties use the same smooth weights. This avoids switching between competing pairs when three or more shapes overlap. Group `0`, or a component with `join=0`, remains isolated. Light's opposing highlight lobes are blended using doubled-angle components, so equivalent angles such as 0° and 180° retain the same appearance.

The shader also fades the refraction displacement where opposing field gradients cancel. A near-zero gradient can no longer be normalized into a full-strength, unstable texture offset. Ordinary border gradients retain the EffOnly profile.

Pulling uses separate, centered transforms on the **stage X and Y axes**: `x′ = scaleX × x`, `y′ = scaleY × y`. There are no off-diagonal terms. Rectangular sides stay horizontal/vertical, circles become axis-aligned ellipses, and capsules do not rotate or shear during diagonal dragging. The configured width, height and radius remain unchanged; inverse coordinate sampling and transformed normals make the contour, rim and refraction follow the deformation.

The free-moving shapes in the raw **Glass** demo lengthen along a horizontal or vertical drag and narrow across it. Equal diagonal motion activates both axes. The stretch cap is 1.65 per axis, and `pull` controls the response strength.

Anchored **Button** and **Menu** controls measure each pull from the point where you pressed. Their center follows the pointer on a spring. Moving back reduces the stretch on each returning axis; crossing the press point stretches the control in the opposite direction. Text follows the same surface, and releasing lets both settle back to their anchor. Dragging a submenu deforms only that panel.

**Practical limits**

- The current background is a static 480×360 RGB image paired with a matching costume: the source photo or the calibration grid. The renderer does not capture arbitrary live sprites, pen drawings or video behind it. Replacing only a costume or stage backdrop does not update the refraction data; a new background needs matching RGB data as well.
- The included photo and grid each have four prefiltered sizes. The native blur block interpolates within and between them at the refracted position, including fractional radii. If you edit the source RGB list, run **LG rebuild blur (1)** for the photo or **(2)** for the grid once after editing, not inside the forever loop. It keeps the old lookup available until the replacement is ready.
- The grid's 360 scanlines contain 102 different rows. Studio and the reusable sprite store each unique row once and recover all 172,800 original pixels exactly. To edit the conventional full `Grid RGB` list, run **LG expand grid for editing**. When done, **LG rebuild blur (2)** refreshes the blur and packs the edited rows for saving.
- Pen is one shared canvas. The renderer replaces affected horizontal strips; other Pen drawings in those strips can be overwritten. Paint overlays after the glass updates or use an ordinary foreground sprite. When replacing a sampled background, regenerate its strip costumes as well as its RGB list.
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

The tool preserves its input and refuses to overwrite an existing output unless `--overwrite` is explicitly supplied. It clears the eight named frame buffers and, in 0.3.0, the four temporary Pen command lists (`frameX`, `frameY`, `frameRGB`, `frameTransparency`). It verifies that initialization and render clear each list, that all other project data and assets are unchanged, and that the output stays under 5,000,000 JSON bytes.

For `0.2.1`, the exact starting editor save and cleanup report are preserved with the numbered version. Reproduce this data-only cleanup with `compact_project.py`; `build_renderer.py` remains the original block generator and would recreate its original demo configuration rather than retain later native-editor edits.

**Files and reproducibility**

| File | Purpose |
| --- | --- |
| `LiquidGlass_Studio.sb3` | Complete editable demo. |
| `LiquidGlass_Component.sprite3` | Importable UI controls and renderer, with editable calls in its green-flag loop. |
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

To reproduce the UI release from the native editor save, run these commands from the version directory. The two inputs in `inputs/` are the exact Studio and sprite used for the upgrade. The build includes all costumes and Scratch blocks needed by the outputs.

```sh
python3 -m tools.build_ui inputs/Studio_before_upgrade.sb3 rebuilt.sb3
python3 -m tools.build_ui inputs/Component_before_upgrade.sprite3 rebuilt.sprite3
python3 tools/validate_sb3.py rebuilt.sb3
```

**Versioned updates**

Every build now preserves a new directory under `versions/` **before it is opened in TurboWarp**. Open the numbered `.sb3` for an unambiguous window title. The unversioned root `.sb3` and `.sprite3` remain convenient copies of the latest build. Existing numbered files are never overwritten.

- Ordinary updates increment the last digit, such as `0.1.0 → 0.1.1`.
- Major framework changes increment the middle digit and reset the last digit, such as `0.1.1 → 0.2.0`.
- The first digit remains `0` under your control.

Use `tools.build_ui` above to build this framework from its native inputs. After verification, `python3 tools/snapshot_release.py` snapshots the current root files as a patch; `--minor` advances the middle digit. Supply the two source archives with `--input-studio` and `--input-component` to preserve them alongside the release. The older `build_renderer.py` reconstructs the historical raw renderer from EffOnly and does not by itself build the current UI release.

To sync a completed update, review the changes and run `sh tools/sync_github.sh "Describe the update"`. The original working directory keeps its local history and uses a separate `.github-sync` checkout for the public GitHub repository. The helper removes personal paths from the exported reports and historical builders, checks the reviewed media hashes, and uses Gitleaks to scan text and unpacked Scratch files before pushing. Two historical comparison videos with device footage are kept locally. Gitleaks must be on the PATH, in `.local-tools/gitleaks`, or supplied through `GITLEAKS_BIN`.

Before every sync, the helper verifies that the destination is the public Liquid Glass repository. For a new release, finish the numbered local snapshot, validation, and both update logs before syncing. Pushing the new `VERSION` starts **Publish Scratch release**, which verifies the Studio and component against the snapshot manifest and attaches them to the matching GitHub release. A later editor save stays in Git alongside the original release download.

**Verification status**

For **0.7.4**, Studio's `project.json` is **4,842,816 bytes**, and the component's `sprite.json` is **4,982,363 bytes**. Saving in the native runtime with a submenu open produces a **4,842,375-byte** project JSON. The Studio retains the submenu timing values from the last editor save.

For **0.7.2**, Studio's `project.json` is **4,842,871 bytes**; a native save with a settled child menu open is **4,841,810 bytes**. The importable sprite's `sprite.json` is **4,981,179 bytes**. The numbered release includes a recording of both return paths in `validation/menu-timing.mp4`. Tests cover independent open and close timings, two submenu depths, interrupted transitions, and zero durations. A standard-resolution stage capture verifies the title stays visible during the fold.

For **0.7.1**, Studio's `project.json` is **4,821,700 bytes**; a native save with a submenu open is **4,820,807 bytes**. The standalone sprite's `sprite.json` is **4,959,782 bytes**. Both exports preserve their original artwork. The release's `validation/` folder includes before/after stage captures, measurements of the first release frame, title and chevron motion, and root and nested highlight margins.

For **0.7.0**, Studio's `project.json` is **4,368,503 bytes**. A native save with a child menu open is **4,361,989 bytes**. The numbered release includes the exact EffOnly reference, the measured rim profile, the submenu motion preview and the before-and-after grid comparison.

For **0.6.0** Studio's `project.json` is **4,135,588 bytes**. The same interpreter saved **4,132,182 bytes** with a child menu open. The numbered release includes the source editor save, tests of all four corners and custom placement, interrupted open/close motion, lettering during unequal-axis pulls, rear-pane cutoff and rounded-corner continuity.

For **0.5.0** the Studio archive's `project.json` is **4,829,209 bytes**. A native save with a child open is **4,819,433 bytes**. Tests cover native nested clicks, intermediate shape and caption frames, back, cleanup outside a parent's footprint, colored materials and blur, and a deliberately slow interpreter frame. With neutral material settings the original renderer also matches the reference pixels in nine scenes. The numbered release's `validation/` folder contains the reports.

`0.2.1` passed all 42 runtime/import checks after clearing the saved buffers. The buffers regenerate with matching, finite data. Structural validation passed without warnings. An exact comparison verifies that only the eight saved list-content arrays changed; all other JSON data and all asset bytes match the latest native editor input.

`0.1.1` passed 36 headless runtime/import checks in the Scratch interpreter and TurboWarp compiler. These include pure-axis and diagonal deformation, axis-aligned ellipse normals, level rectangle/capsule sides, pointer interaction, recovery, joins, and refraction stability. The numbered build was also opened and rendered through its visible green-flag loop in TurboWarp Desktop. Automated pointer gestures can occur between rendered frames, so they are supplemented by sustained pointer tests in the VM and the user's live visual feedback.

The `0.2.0` group-blending framework passed **42 runtime/import checks** on both the generated source and the copy saved by TurboWarp Desktop. Native save/reopen preserved all 12 custom procedure definitions and all nonprimitive opcode counts, with clean archive, reference and Boolean-socket validation. Four additional native-copy smoke checks passed. The visible green-flag loop, running two-shape joining and expanded multi-shape scene were inspected on stage. See `versions/0.2.0/validation/summary.json` for the tested hashes and `versions/0.2.0/EditorVerified_0.2.0.sb3` for the native editor output. Earlier root `native_editor_*.json` reports refer to the historical unnumbered snapshot.

Independent geometry audits cover tangent continuity at mixed-shape joins, exact remote-edge behavior, bounded connections, axis-aligned pulling and multiway material continuity. See `research/geometry_validation.json`, `research/grazing_boundary_audit.json`, and `research/nary_blend_audit.json`. Headless tests verify the actual block calculations; native TurboWarp checks verify loading, editable scripts and on-stage rendering.

Invalid intermediate editor-save snapshots are isolated in `research/diagnostics/` with an explanatory note. They are not deliverables.

The block format and custom-block wiring are based on the primary [Scratch SB3 serializer/deserializer](https://github.com/scratchfoundation/scratch-vm/blob/develop/src/serialization/sb3.js), [custom procedure primitives](https://github.com/scratchfoundation/scratch-vm/blob/develop/src/blocks/scratch3_procedures.js) and [native Pen extension](https://github.com/scratchfoundation/scratch-vm/blob/develop/src/extensions/scratch3_pen/index.js), together with the supplied project blocks. The finished archives contain standard Scratch data and assets, with no JavaScript runtime, custom shader or external extension.
