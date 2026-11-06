# Liquid Glass Studio 0.7.0 verification

Both the numbered Studio and the importable sprite preserve all 276 prior assets, the two backdrop sources and the original green-flag examples. Studio contains 4,368,503 bytes of project JSON. The sprite contains 4,496,966 bytes of sprite JSON. Saving through the VM with a child menu visible produced a 4,361,989-byte project JSON. The files use Scratch blocks and the native Pen extension.

## Refraction

The exact source is included in `../inputs/EffOnly_reference.sb3`. Its own `Reflection` and `ProcessImage` blocks ran over the same calibration image used for the four public components. With half-thickness 80, reflection 0.5 and distortion 1, the sample two stage pixels inside the rim moves inward by (40 − 2)² / 10 = 144.4 pixels. The 0.6.0 public UI capped this at 19.09, while raw Glass capped it at 110. All four new public components reached 144.4. The private pane reached 143.98. Fractional positions interpolate RGB, and offstage positions read the color at the nearest stage edge.

The rounded-rectangle test examined eight transitions from a side to a curved corner. The capsule test examined four. The maximum turn of the sampled direction per stage pixel was 1.71° on the rectangle and 1.10° on the capsule. Displacement on the curved portions reached 132.16 and 90.47 pixels respectively. A separate test covered the four corners of a child panel, including all 28 geometric coverage probes. The parent edge visible behind the foreground stayed continuous across the child. A joined shape's center changed its source coordinate by 1.10 pixels for a one-pixel move.

The Scratch reference supplies the displacement equation. Kube’s published implementation illustrates how a material profile and a surface direction can be computed separately. [Liquid Glass in the Browser](https://kube.io/blog/liquid-glass-css-svg/)

## Menus and input

The green-flag loop was exercised with independent open and close travel and growth times, zero-duration channels, zero bounce, reversal during flight, and 10 Hz and 30 Hz simulation clocks. At the default bounce of 0.30 the root overshot by about 4.6%, then settled. The springs carry velocity when a target changes. [Apple’s Animate with springs](https://developer.apple.com/videos/play/wwdc2023/10158/)

For the Menu finish submenu, the collapsed label and right-facing chevron were traced through their first, middle and open positions, then back again. The child begins at the measured source capsule, including at a stage edge. The original two chevron strokes rotate to 90 degrees and retain their right-hand placement. Tests also covered two levels of nested menus, rapidly reversing a return, leaf actions, and removal of a closed child.

A 96-pixel pointer step moved the button center 9.07 pixels on the first frame and 13.88 on the second, settling at 19.33. Reversing during that approach changed direction on the next frame. The width measured 154.80 pixels at reversal and again as the cursor crossed the original press. Horizontal, vertical, diagonal and mirrored gestures ran in both the interpreter and the compiler.

The nine presentation scenarios compare the Pen frame against the earlier stable reference with rim effects neutralized. A separate slow-interpreter test used active glass layers. It found zero missing child probes at scheduler yields and zero Pen operations when stationary. The two media files use the native Pen commands from the numbered Studio, as detailed in preview_provenance.md.

## Desktop and reproducibility

The dedicated TurboWarp Desktop window loaded the numbered project and identified it as LiquidGlass_Studio_0.7.0. Desktop automation could read the window title but could not send pointer or keyboard input to the stage. The green-flag, cursor and pixel results above come from the installed TurboWarp VM running the numbered files. Both archives reproduced byte-for-byte when rebuilt from the source and inputs in this release. All 57 recorded manifest entries passed their size and SHA-256 checks.
