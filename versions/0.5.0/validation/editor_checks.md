# Release verification — Liquid Glass 0.5.0

The numbered Studio was opened in the existing dedicated TurboWarp Desktop test window. Its editor displayed the native green flag, the three editable component calls in its forever loop, and the Pen extension. Desktop mouse automation did not confirm the green-flag click after loading; the interaction, animation, import and optical checks below ran in the real VM bundled in that same installation.

On the shipped Studio and sprite, the 42 original renderer and import checks, 8 layered menu checks, 9 optical checks, 17 UI and cross-project integration checks, and 23 uniform highlight cases all passed. The menu tests drive the VM's mouse device: open a launcher, push two levels, hit a growing child, navigate back, and activate a leaf. All six sampled child pixels outside the root were restored after dismissal. Frosted, Clear and Smoked change the menu's own material.

The nine neutral reference scenes match the older renderer pixel-for-pixel. During a costly interpreted Pen redraw, the early private-panel implementation lost all nine sampled areas between drawing commands and published three missing at a scheduler yield. The corrected composite keeps all nine visible at every observed yield; at most one was transiently being repainted between individual Pen operations. A stationary redraw emitted no pen strokes or stamps.

Studio project.json is 4,829,209 bytes. The importable sprite manifest is 4,946,657 bytes. The native serializer also checked running scenes with the launcher closed, the root open and the child open (4,819,433 bytes in the last case), then reloaded the saved state. Original costumes, other assets and both full background RGB lists are preserved. The exact 0.4.1 editor save is in inputs/.

Reports retain the tested temporary paths and identify the archive bytes by SHA-256. submenu.png is a 2× visual preview reconstructed from the final VM's own Pen lines and costume stamps on the photo background, not a desktop screen capture. The recipe for repeating the tests is in the tools directory; the renderer runs entirely in Scratch.
