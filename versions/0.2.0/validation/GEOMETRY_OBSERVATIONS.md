# Independent geometry checks — 0.2.0

Run `python3 tools/check_geometry.py`. It combines independent axis-deformation, two-shape contour and group-blending oracles and writes `research/geometry_validation.json`. These standard-library Python calculations are test oracles; the Scratch project runs native blocks.

The current model differs from the earlier directional/tapered prototypes. Those prototypes' area-preservation claims must not be applied to diagonal motion in 0.2.0.

**Axis-aligned deformation**

The rest contour is evaluated at `(localX / scaleX, localY / scaleY)`. Normals use the inverse-transpose transform, followed by normalization. There are no cross-coordinate terms, so circles remain axis-aligned ellipses and rounded rectangles/capsules cannot rotate or shear.

Let `pX` and `pY` be the absolute smoothed pull channels. Each axis has a bounded draw amount, `drawX=min(pX/max(4,width/2),.65)` and similarly for Y. Cross-squeeze factors are `squeezeX=smoothstep(clamp(1-pX/max(.001,pY),0,1))` and the corresponding swapped expression for Y. The scales are:

```text
scaleX = (1 + drawX) / (1 + drawY * squeezeX)
scaleY = (1 + drawY) / (1 + drawX * squeezeY)
```

Pure horizontal or vertical pulling has reciprocal scales and preserves continuous area. When both channels move, cross-squeeze fades and the stretches combine. Diagonal deformation intentionally permits area change; its area ratio is `scaleX * scaleY`. Opposite sides remain symmetric about the component's current center, and configured width/height/radius are unchanged. Continuous-geometry claims do not imply identical pixel coverage after rasterization.

**Continuous bounded joins**

Pair smoothing uses the standard polynomial smooth minimum, with no individual-normal gate. Its radius starts at twice the smaller join input and fades using `smoothstep(centerDistance / initialReach)` near coincident centers. Four smoothstep gates, measured inside the pair bounds, further attenuate the radius. The edge band uses the attenuated radius: `max(.01,min(attenuatedReach/2,min(wA,hA,wB,hB)/4))`. At or beyond an edge the pair's radius is exactly zero; the final distance is never hard-clipped.

Removing the former normal gate fixes a concrete grazing contact: a 120×60 rounded rectangle centered at the origin and a radius-40 circle centered at `(60,0)`. The old contour's two tangent slopes differed by approximately 0.882 at their original intersection. The new one-sided slopes converge; the difference is below 3.1×10⁻⁷ at a 10⁻⁴-pixel probe. Additional capsule/circle, diagonal rectangle/circle and unequal-circle cases also converge to common tangents. Dense contour checks cover the surrounding join, rather than just one chosen point.

Two-shape regressions also cover shape normalization, circle/capsule special cases, 72,900 mixed-shape exterior samples, exact compact-support remote samples, coincidence limits, and neck formation before contact. "Remote" means outside the active compact blend, not every point on a back-facing half of an overlapping shape. Nearby shoulders can change locally to make a smooth connection. Resting group bounds remain unchanged.

**More than two components**

Within each eligible group, components fold in stable ascending ID order. For each new component j, the continuous pair radii combine as:

```text
Kj = 2 * join[j] * (1 - product_i(1 - Kij / (2 * join[j])))
h  = clamp(.5 + .5 * (distance[j] - accumulatedDistance) / Kj, 0, 1)
D  = h * accumulatedDistance + (1-h) * distance[j] - Kj * h * (1-h)
```

The same h combines all seven optical values: band, distortion, edge, highlight, light X, light Y and tint. This removes the discontinuous material switch between competing pairs at three-way overlaps. Pair radii depend on position, never on a branch comparing shape distances. Components with group 0 or join 0 are isolated; separate groups use hard union.

Light X/Y store `cos(2*angle)` and `sin(2*angle)`. This reproduces the original opposing highlight lobes exactly for an isolated component and blends equivalent 0°/180° lighting without an artificial cancellation. The shader's separate low-gradient gain prevents nearly cancelled field gradients from generating a full-strength texture displacement.

`tools/audit_nary_blend.py` checks three unequal three-component arrangements. The former pair-selection rule produced optical-band jumps of roughly 3.6–5.2 pixels; differences across the new fold tend to zero. It also checks all seven properties, two-shape equivalence, disabled-join isolation and 6,060 exterior group-bound samples. Results are in `research/nary_blend_audit.json`.

**Limits and evidence**

Sequential folding is order-dependent, so IDs must stay stable during a scene. A multiway bridge can contain more interior material than a minimum of separate pair unions while preserving the group's outer bounds. Different groups deliberately do not have smooth material transitions. These sampled checks are not proof of every possible arrangement's visual quality.

The geometry reports are independent of the Scratch VM and of native UI testing. Actual block execution is recorded separately in `research/runtime_validation.json`; native observations identify their own version. `research/version_integrity.json` records a read-only check that preserved 0.1.1 and 0.2.0 manifest files still match their hashes and that the current archives match 0.2.0.
