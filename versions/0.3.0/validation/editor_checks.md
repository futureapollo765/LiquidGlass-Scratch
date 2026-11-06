# Live editor checks • 0.3.0

Tested `LiquidGlass_Studio_0.3.0.sb3` (`efabb11965f15e7a0482486dcd6b9473d13750a9e6bab6f36fdeb1695a87dea7`) from its green flag in both editors.

- **TurboWarp Desktop:** Used a dedicated test window. Confirmed **Disable Compiler = on** and **Warp Timer = on** after importing the numbered archive. The rounded rectangle, circle and capsule appeared together over the photo. Two captures of the running idle stage had zero differences across the 2,511,600 pixels compared. The user's other TurboWarp project was not replaced.
- **Vanilla Scratch:** Imported into a separate signed-out Scratch editor at `scratch.mit.edu/projects/editor/`. The palette loaded normally. Three repeated captures of the running idle scene showed no change above six RGB levels in any of the three component regions. Pressed **3** to animate just the main rectangle to a circle: in six captures the main region visibly changed and neither neighboring shape's region changed above that threshold. Pressed **B** and saw all three components refract the calibration grid. Pressed **R** and all three photo-background regions matched their initial capture exactly. These are visual samples; the separate interpreter trace checks Pen operations between rendered frames.

The test did not save to or publish a Scratch account. A slow interpreter can still take several ticks to compute a moving frame; the previous image remains visible while it works.
