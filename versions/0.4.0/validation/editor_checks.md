# Live editor checks

The numbered 0.4.0 Studio archive was loaded through the normal file menu and started with the green flag in both TurboWarp Desktop and the signed-out Scratch editor.

In TurboWarp, the main script displayed the three editable component calls. The **Options** capsule expanded into a rounded rectangular panel with **Background** and **Detail** as separate rows. Only the dedicated test window was used for the new release.

In vanilla Scratch, a normal click on **Options** opened the menu. Clicking **Background** displayed a back arrow, a checkmark on **Photo** and a **Grid** option. Choosing **Grid** collapsed the menu, updated the glass sampling and changed the sidebar readout to **Grid**. Clicking **Switch background** restored the photo and its readout. The controls and labels remained in their stage positions.

The interpreter and compiler tests in `ui_controls.json` also cover pressed-state cancellation, axis-aligned pull, independent component configuration, retained idle frames, a short click during rendering, and receiver scripts in a separate host project.
