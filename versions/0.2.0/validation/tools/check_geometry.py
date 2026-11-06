#!/usr/bin/env python3
"""Independent, standard-library checks for the Scratch renderer's geometry.

This code is a test oracle, not project runtime code. All lengths are stage units.
"""
from __future__ import annotations
import json
import math
import hashlib
from pathlib import Path

EPS = 1e-12


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def smoothstep(x):
    x = clamp(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def normalize_shape(shape, width, height, radius):
    width, height = max(1.0, width), max(1.0, height)
    if shape == "circle":
        height = width
        radius = width / 2.0
    elif shape == "capsule":
        radius = min(width, height) / 2.0
    else:
        radius = clamp(radius, 0.0, min(width, height) / 2.0)
    return width, height, radius


def rounded_rect(x, y, width, height, radius):
    radius = clamp(radius, 0.0, min(width, height) / 2.0)
    qx = abs(x) - (width / 2.0 - radius)
    qy = abs(y) - (height / 2.0 - radius)
    return math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - radius


def circle_distance_normal(x, y, center, radius):
    dx, dy = x - center[0], y - center[1]
    length = math.hypot(dx, dy)
    return length - radius, ((dx / length, dy / length) if length else (0.0, 0.0))


def bbox_gate(x, y, bbox, band):
    left, bottom, right, top = bbox
    return (smoothstep((x - left) / band)
            * smoothstep((right - x) / band)
            * smoothstep((y - bottom) / band)
            * smoothstep((top - y) / band))


def legacy_facing_union(x, y, ca, cb, radius, join, gate_slope=2.0, bounded=True):
    da, na = circle_distance_normal(x, y, ca, radius)
    db, nb = circle_distance_normal(x, y, cb, radius)
    dx, dy = cb[0] - ca[0], cb[1] - ca[1]
    separation = math.hypot(dx, dy)
    hard = min(da, db)
    if separation <= EPS or join <= 0:
        return hard
    vx, vy = dx / separation, dy / separation
    ga = smoothstep(gate_slope * (na[0] * vx + na[1] * vy))
    gb = smoothstep(-gate_slope * (nb[0] * vx + nb[1] * vy))
    edge_gate = 1.0
    if bounded:
        bbox = (min(ca[0], cb[0]) - radius, min(ca[1], cb[1]) - radius,
                max(ca[0], cb[0]) + radius, max(ca[1], cb[1]) + radius)
        edge_gate = bbox_gate(x, y, bbox, max(0.01, min(join, radius / 2.0)))
    keff = 2.0 * join * ga * gb * edge_gate
    if keff <= EPS:
        return hard
    h = max(keff - abs(da - db), 0.0)
    return hard - h * h / (4.0 * keff)


def shape_distance_normal(x, y, shape):
    cx, cy, width, height, radius = shape[:5]
    lx, ly = x - cx, y - cy
    radius = clamp(radius, 0.0, min(width, height) / 2.0)
    qx, qy = abs(lx) - width / 2.0 + radius, abs(ly) - height / 2.0 + radius
    ox, oy = max(qx, 0.0), max(qy, 0.0)
    length = math.hypot(ox, oy)
    sx, sy = (1 if lx >= 0 else -1), (1 if ly >= 0 else -1)
    if length > 1e-10:
        normal = (sx * ox / length, sy * oy / length)
    elif qx > qy:
        normal = (sx, 0.0)
    else:
        normal = (0.0, sy)
    return length + min(max(qx, qy), 0.0) - radius, normal


def pair_bbox(a, b):
    # Optional sixth entry is the conservative pull-amplitude padding.
    pa, pb = (2*a[5] if len(a) > 5 else 0), (2*b[5] if len(b) > 5 else 0)
    return (min(a[0]-a[2]/2-pa, b[0]-b[2]/2-pb),
            min(a[1]-a[3]/2-pa, b[1]-b[3]/2-pb),
            max(a[0]+a[2]/2+pa, b[0]+b[2]/2+pb),
            max(a[1]+a[3]/2+pa, b[1]+b[3]/2+pb))


def bounded_shape_union(x, y, a, b, join):
    da = shape_distance_normal(x, y, a)[0]
    db = shape_distance_normal(x, y, b)[0]
    hard = min(da, db)
    dx, dy = b[0]-a[0], b[1]-a[1]
    separation = math.hypot(dx, dy)
    if separation <= 0.01 or join <= 0:
        return hard
    reach = 2 * join * smoothstep(separation / (2 * join))
    band = max(0.01, min(reach/2, min(a[2], a[3], b[2], b[3]) / 4.0))
    keff = reach * bbox_gate(x, y, pair_bbox(a, b), band)
    if keff <= EPS:
        return hard
    h = max(keff-abs(da-db), 0.0)
    return hard-h*h/(4*keff)


def gated_union(x, y, ca, cb, radius, join):
    return bounded_shape_union(x,y,(ca[0],ca[1],2*radius,2*radius,radius),
                               (cb[0],cb[1],2*radius,2*radius,radius),join)


def run_checks():
    from axis_geometry_oracle import run_checks as check_axis_pull
    from audit_nary_blend import audit as check_nary
    pull_results = check_axis_pull()
    nary_results = check_nary()

    shape_cases = []
    for shape, w, h, r in [("circle", 80, 30, 2), ("capsule", 120, 40, 0), ("capsule", 40, 120, 100), ("rounded rectangle", 90, 50, 100), ("rounded rectangle", 90, 50, -5)]:
        nw, nh, nr = normalize_shape(shape, w, h, r)
        assert 0 <= nr <= min(nw, nh) / 2
        assert abs(rounded_rect(nw / 2, 0, nw, nh, nr)) < 1e-10
        assert abs(rounded_rect(0, nh / 2, nw, nh, nr)) < 1e-10
        shape_cases.append(dict(shape=shape, input=[w, h, r], normalized=[nw, nh, nr]))
    circle_max_error = max(abs(rounded_rect(x, y, 80, 80, 40) - (math.hypot(x, y) - 40)) for x in range(-70, 71, 7) for y in range(-70, 71, 7))
    assert circle_max_error < 1e-10

    remote_max_error = 0.0
    remote_samples = 0
    shoulder_max_change = 0.0
    shoulder_samples = 0
    axis_aligned_back_arc_max_error = 0.0
    for angle in (0.0, math.pi / 2, math.pi / 4):
        ux, uy = math.cos(angle), math.sin(angle)
        for separation in (0.0, 15.0, 40.0, 80.0, 90.0, 110.0):
            ca, cb = (-separation / 2 * ux, -separation / 2 * uy), (separation / 2 * ux, separation / 2 * uy)
            for side, center in enumerate((ca, cb)):
                for deg in range(0, 360, 2):
                    phi = math.radians(deg)
                    nx, ny = math.cos(phi), math.sin(phi)
                    facing = (nx * ux + ny * uy) * (1 if side == 0 else -1)
                    if facing <= 1e-10:
                        x, y = center[0] + 40 * nx, center[1] + 40 * ny
                        da = math.hypot(x-ca[0], y-ca[1])-40
                        db = math.hypot(x-cb[0], y-cb[1])-40
                        hard = min(da,db)
                        val = gated_union(x, y, ca, cb, 40, 20)
                        reach = 40*smoothstep(separation/40)
                        if abs(da-db) >= reach-1e-10:
                            remote_max_error = max(remote_max_error, abs(val-hard))
                            remote_samples += 1
                        else:
                            shoulder_max_change = max(shoulder_max_change, abs(val-hard))
                            shoulder_samples += 1
                        if angle != math.pi/4:
                            axis_aligned_back_arc_max_error = max(axis_aligned_back_arc_max_error,abs(val-hard))
    assert remote_max_error < 1e-10
    # The final attenuated edge band can modify near-overlap shoulders even on
    # an axis-aligned pair; only compact-support remote arcs must remain exact.

    topology = []
    for gap in (-20, 0, 10, 19, 20, 21, 30):
        separation = 80 + gap
        value = gated_union(0, 0, (-separation/2,0), (separation/2,0), 40, 20)
        expected = gap/2 - 10
        assert abs(value - expected) < 1e-10
        topology.append(dict(gap=gap, midpoint_distance=value, connected=value < 0))
    coincident_error = max(abs(gated_union(x,y,(0,0),(0,0),40,20)-(math.hypot(x,y)-40)) for x in range(-60,61,5) for y in range(-60,61,5))
    assert coincident_error < 1e-10

    # Final model: edge gates attenuate k, with no hard contour clamp.
    bridge_extents = []
    for separation in (0, 15, 40, 60, 80, 90):
        radius, join = 40.0, 20.0
        ca, cb = (-separation / 2, 0), (separation / 2, 0)
        max_y = radius
        max_x_at_y = None
        for ix in range(401):
            x = -separation / 2 + separation * ix / 400 if separation else 0
            lo, hi = 0.0, 80.0
            if gated_union(x, lo, ca, cb, radius, join) >= 0:
                continue
            for _ in range(40):
                mid = (lo + hi) / 2
                if gated_union(x, mid, ca, cb, radius, join) <= 0:
                    lo = mid
                else:
                    hi = mid
            if lo > max_y:
                max_y, max_x_at_y = lo, x
        bridge_extents.append(dict(center_separation=separation, original_top=radius, union_top=max_y, inflation=max_y-radius, x_at_union_top=max_x_at_y))
        assert max_y-radius < 1e-8

    mixed_cases = [
        ("rectangle_circle", (-65,0,100,80,18), (30,0,60,60,30)),
        ("capsule_circle", (-65,0,100,40,20), (30,0,60,60,30)),
        ("vertical_capsule_rectangle", (0,-65,40,100,20), (0,30,80,60,12)),
        ("diagonal_rectangle_circle", (-30,-20,100,70,12), (40,50,60,60,30)),
        ("overlapping_round_rectangles", (-20,0,120,60,15), (20,0,120,60,15)),
        ("overlapping_unequal_circles", (-15,0,80,80,40), (15,0,50,50,25)),
        ("grazing_rectangle_circle", (0,0,120,60,12), (60,0,80,80,40)),
        ("grazing_capsule_circle", (0,0,160,40,20), (75,0,60,60,30)),
        ("unequal_circle_center_plane_contact", (0,0,80,80,40), (30,0,100,100,50)),
    ]
    mixed_results = []
    exterior_samples = 0
    for name, a, b in mixed_cases:
        left, bottom, right, top = pair_bbox(a, b)
        max_error = 0.0
        for join in (0, 10, 20, 40, 60):
            for index in range(81):
                x, y = left+(right-left)*index/80, bottom+(top-bottom)*index/80
                for offset in (0, 1e-5, 0.1, 1, 5):
                    for px, py in ((left-offset,y), (right+offset,y), (x,bottom-offset), (x,top+offset)):
                        hard = min(shape_distance_normal(px,py,a)[0], shape_distance_normal(px,py,b)[0])
                        actual = bounded_shape_union(px,py,a,b,join)
                        max_error = max(max_error, abs(hard-actual))
                        assert actual >= -1e-8
                        exterior_samples += 1
        assert max_error < 1e-12
        mixed_results.append(dict(case=name, bbox=[left,bottom,right,top], max_exterior_hard_union_error=max_error))
    mixed_neck = bounded_shape_union(-7.5, 0, mixed_cases[0][1], mixed_cases[0][2], 20)
    assert abs(mixed_neck + 2.5) < 1e-10

    # The edge envelope has zero first derivative as each margin reaches zero.
    edge_derivative = []
    for step in (1e-2, 1e-3, 1e-4):
        edge_derivative.append(bbox_gate(step, 50, (0,0,100,100), 10)/step)
    assert edge_derivative[-1] < 4e-6

    # A top-edge/circle contact used to receive zero smooth radius from the
    # normal-facing gate. Its two one-sided contour slopes stayed different.
    # The final position-only envelope must converge to a common tangent.
    def upper_boundary(x, a, b, join):
        lo, hi = 0.0, pair_bbox(a,b)[3] + 10
        assert bounded_shape_union(x,lo,a,b,join) < 0
        for _ in range(56):
            middle = (lo+hi)/2
            if bounded_shape_union(x,middle,a,b,join) <= 0:
                lo = middle
            else:
                hi = middle
        return (lo+hi)/2

    grazing_tangents = []
    for name, a, b, x0, x_start, x_end in [
        ("rectangle_circle",(0,0,120,60,12),(60,0,80,80,40),60-math.sqrt(40**2-30**2),20,80),
        ("capsule_circle",(0,0,160,40,20),(75,0,60,60,30),75-math.sqrt(30**2-20**2),35,90),
        ("diagonal_rectangle_circle",(0,0,120,60,12),(70,20,60,60,30),70-math.sqrt(30**2-10**2),25,85),
        ("unequal_circles",(0,0,80,80,40),(30,0,100,100,50),0,-10,50),
    ]:
        join = 30
        y0 = upper_boundary(x0,a,b,join)
        one_sided = []
        for step in (.1,.01,.001,.0001):
            left_slope = (y0-upper_boundary(x0-step,a,b,join))/step
            right_slope = (upper_boundary(x0+step,a,b,join)-y0)/step
            one_sided.append(dict(step=step,left=left_slope,right=right_slope,gap=abs(left_slope-right_slope)))
        assert one_sided[-1]['gap'] < 1e-4
        max_gap = 0.0
        for index in range(401):
            x = x_start+(x_end-x_start)*index/400
            y = upper_boundary(x,a,b,join)
            step = 1e-4
            gap = abs((upper_boundary(x+step,a,b,join)-y)/step-(y-upper_boundary(x-step,a,b,join))/step)
            max_gap = max(max_gap,gap)
        assert max_gap < 1e-3
        grazing_tangents.append(dict(case=name,intersection_x=x0,boundary_y=y0,
            one_sided_tangents=one_sided,dense_contour_samples=401,dense_max_slope_gap=max_gap))

    coincidence_samples = []
    for separation in (1,.1,.01,.001,.0001,0):
        ca,cb = (-separation/2,0),(separation/2,0)
        reach = 40*smoothstep(separation/40)
        max_change = 0
        for x in range(-40,41,5):
            for y in range(-40,41,5):
                hard = min(math.hypot(x-ca[0],y)-40,math.hypot(x-cb[0],y)-40)
                max_change = max(max_change,abs(gated_union(x,y,ca,cb,40,20)-hard))
        assert max_change <= reach/4+1e-10
        coincidence_samples.append(dict(separation=separation,reach=reach,max_distance_change=max_change))

    # Historical alternatives quantify why slope reduction alone was insufficient.
    unbounded_alternatives = []
    for slope, join, separation in ((2,20,40), (1,40,40), (1,60,60)):
        ca, cb = (-separation/2,0), (separation/2,0)
        best = 40.0
        for ix in range(201):
            x = -separation/2 + separation*ix/200
            lo, hi = 0.0, 100.0
            for _ in range(35):
                mid = (lo+hi)/2
                if legacy_facing_union(x,mid,ca,cb,40,join,slope,bounded=False) <= 0:
                    lo = mid
                else:
                    hi = mid
            best = max(best,lo)
        unbounded_alternatives.append(dict(gate_slope=slope, join=join, separation=separation, inflation=best-40))

    return {
        "status": "passed",
        "version": "0.2.0",
        "scope": "Independent formula oracles for axis-aligned pulling, bounded pairs and the n-ary geometry/optical group fold. Actual Scratch execution is tested separately.",
        "pull": pull_results,
        "nary": nary_results,
        "shapes": {"normalization_cases": shape_cases, "circle_sdf_max_error": circle_max_error},
        "metaball": {
            "model": "Normal-independent polynomial smooth union with four C1 bounds gates and reach=2*join*smoothstep(centerDistance/(2*join)).",
            "remote_boundary_samples": remote_samples,
            "max_remote_boundary_error": remote_max_error,
            "remote_definition": "Boundary points with |dA-dB| at least the global pair reach; compact support guarantees exact original union there.",
            "near_overlap_back_shoulder_samples": shoulder_samples,
            "max_near_overlap_back_shoulder_field_change": shoulder_max_change,
            "axis_aligned_circle_back_arc_max_error": axis_aligned_back_arc_max_error,
            "coincident_shape_max_error": coincident_error,
            "topology_join_distance_20": topology,
            "bridge_extents_radius_40_join_20": bridge_extents,
            "bounds_gate": "Product of four smoothstep(margin/band) gates, band=max(.01,min(attenuatedReach/2,min(wA,hA,wB,hB)/4)); attenuates kEff, never clamps final distance.",
            "mixed_shape_exterior_samples": exterior_samples,
            "mixed_shape_bounds": mixed_results,
            "mixed_rectangle_circle_gap_15_join_20_midpoint_distance": mixed_neck,
            "grazing_and_diagonal_contour_tangents": grazing_tangents,
            "coincident_center_continuity": coincidence_samples,
            "edge_gate_one_sided_derivative_approaching_boundary": edge_derivative,
            "rejected_unbounded_alternatives": unbounded_alternatives,
            "limitations": "Exact rest bounds and compact-support remote arcs; diagonal deep-overlap shoulders within the active blend region may change locally. Pull uses conservative 2*amplitude-padded bounds, not the exact tight deformed bounds. Grid checks are not an all-configurations visual smoothness proof.",
        },
    }


if __name__ == "__main__":
    results = run_checks()
    root = Path(__file__).resolve().parents[1]
    results['artifact_sha256'] = {name:hashlib.sha256((root/name).read_bytes()).hexdigest()
                                  for name in ('LiquidGlass_Studio.sb3','LiquidGlass_Component.sprite3')}
    destination = root / "research" / "geometry_validation.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
