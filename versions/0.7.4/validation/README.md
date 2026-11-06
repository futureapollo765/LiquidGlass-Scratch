# 0.7.4 drag checks

The recording uses the saved Studio demo in the installed TurboWarp renderer. The mouse stays down as each control moves away from the press point, returns to it, then moves to the other side. The pointer indicator shows the held position. See `held-drag.mp4` and `visual-drag-final.json`.

In both compiled and interpreted execution, the expanded menu measured 188 pixels wide at the press point, 210.59 after a horizontal pull, 199.14 partway back, and 188 on return. Its nested Background submenu returned to exactly 196 × 102, without moving the parent or activating the row. Back still opened the parent. The `0.7.3-panel` reports show the previous failure.

`stretch_gesture.json` covers rectangular, circular and capsule silhouettes, both directions, independent axes, long pulls, and off-center presses. `gesture_spring.json` checks release velocity, spring overshoot and re-grabbing. `menu-drag-return.json` checks the expanded menu and nested panel.

Both archives passed structural checks, retained their native artwork and public block inputs, and remained below 5,000,000 bytes of uncompressed JSON. The reusable sprite also passed import and activation checks with the compiler on and off.
