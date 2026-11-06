# Highlight verification

In vanilla Scratch, the 0.4.0 button reproduced the brighter disk shown in the reported screenshot. The comparison used the same photo, hovered button and stage size for 0.4.1. The distinct disk disappeared. In matched screen captures, an interior sample in the old starting cap was 22.32 RGB levels brighter on average than in the patch, while the corresponding sample along the shaft had zero mean difference.

The numbered patch also loaded in the dedicated TurboWarp Desktop window. The real Pen extension tests in `highlights.json` exercise horizontal, vertical and circular highlights plus five button and menu-row combinations. Use the final fixture beside the report to reproduce the foreground checks. The full UI and separate-host import tests are in `ui_controls.json`.
