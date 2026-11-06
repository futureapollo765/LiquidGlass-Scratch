#!/usr/bin/env python3
"""Independent numeric oracle for the renderer's world-axis pull deformation.

This file is validation code only, never a Scratch runtime dependency.
"""
import math
import random


def clamp(x, low=0.0, high=1.0):
    return max(low, min(high, x))


def smooth(x):
    x = clamp(x)
    return x*x*(3-2*x)


def scales(px, py, width, height):
    pull_x, pull_y = abs(px), abs(py)
    draw_x = min(pull_x/max(4, width/2), .65)
    draw_y = min(pull_y/max(4, height/2), .65)
    squeeze_x = smooth(1-pull_x/max(.001, pull_y))
    squeeze_y = smooth(1-pull_y/max(.001, pull_x))
    sx = (1+draw_x)/(1+draw_y*squeeze_x)
    sy = (1+draw_y)/(1+draw_x*squeeze_y)
    amplitude = max(abs(sx-1)*width/2, abs(sy-1)*height/2)
    return sx, sy, amplitude


def forward(x, y, sx, sy):
    return sx*x, sy*y


def rest_distance_normal(x, y, width, height, radius):
    qx, qy = abs(x)-width/2+radius, abs(y)-height/2+radius
    ox, oy = max(qx, 0), max(qy, 0)
    length = math.hypot(ox, oy)
    sx, sy = (1 if x >= 0 else -1), (1 if y >= 0 else -1)
    if length > .0001:
        normal = (sx*ox/length, sy*oy/length)
    else:
        normal = (sx, 0) if qx > qy else (0, sy)
    return length+min(max(qx, qy), 0)-radius, normal


def distance_normal(x, y, width, height, radius, sx, sy, amplitude):
    if amplitude <= .02:
        return rest_distance_normal(x, y, width, height, radius)
    distance, (nx, ny) = rest_distance_normal(x/sx, y/sy, width, height, radius)
    gx, gy = nx/sx, ny/sy
    gradient_length = max(.2, math.hypot(gx, gy))
    return distance/gradient_length, (gx/gradient_length, gy/gradient_length)


def contour(width, height, radius, count=120):
    result = []
    for i in range(count):
        theta = 2*math.pi*i/count
        ux, uy = math.cos(theta), math.sin(theta)
        low, high = 0, math.hypot(width, height)
        for _ in range(48):
            middle = (low+high)/2
            if rest_distance_normal(middle*ux, middle*uy, width, height, radius)[0] < 0:
                low = middle
            else:
                high = middle
        result.append(((low+high)/2*ux, (low+high)/2*uy))
    return result


def polygon_area(points):
    return abs(sum(x*y1-x1*y for (x, y), (x1, y1) in zip(points, points[1:]+points[:1])))/2


def run_checks():
    rng = random.Random(20261105)
    inverse_error = symmetry_error = off_diagonal = bounds_excess = 0.0
    for _ in range(2500):
        width, height = rng.uniform(8, 440), rng.uniform(8, 300)
        px, py = rng.uniform(-300, 300), rng.uniform(-300, 300)
        sx, sy, amplitude = scales(px, py, width, height)
        assert 1/1.65-1e-12 <= sx <= 1.65+1e-12
        assert 1/1.65-1e-12 <= sy <= 1.65+1e-12
        assert sx*sy >= 1-1e-12
        x, y = rng.uniform(-width/2, width/2), rng.uniform(-height/2, height/2)
        xp, yp = forward(x,y,sx,sy)
        inverse_error = max(inverse_error, math.hypot(xp/sx-x, yp/sy-y))
        symmetry_error = max(symmetry_error, abs(xp+sx*(-x)), abs(yp+sy*(-y)))
        # x depends only on x; y depends only on y, even with two active channels.
        off_diagonal = max(off_diagonal,
            abs((forward(x,y+1e-4,sx,sy)[0]-forward(x,y-1e-4,sx,sy)[0])/2e-4),
            abs((forward(x+1e-4,y,sx,sy)[1]-forward(x-1e-4,y,sx,sy)[1])/2e-4))
        for bx, by in ((width/2,height/2),(width/2,-height/2),(-width/2,height/2),(-width/2,-height/2)):
            bounds_excess = max(bounds_excess, abs(sx*bx)-width/2-2*amplitude, abs(sy*by)-height/2-2*amplitude)
            # The new amp is itself a world-axis extent allowance; even 1*amp is sufficient.
            assert abs(sx*bx) <= width/2+amplitude+1e-10
            assert abs(sy*by) <= height/2+amplitude+1e-10
    assert inverse_error < 1e-10 and symmetry_error == 0 and off_diagonal == 0
    assert bounds_excess <= 1e-10

    pure_axis_area_error = 0.0
    pure_cases = []
    for width,height in ((80,80),(160,40),(40,160),(140,70)):
        for amount in (0,.1,10,50,300):
            for px,py in ((amount,0),(0,amount),(-amount,0),(0,-amount)):
                sx,sy,amplitude = scales(px,py,width,height)
                pure_axis_area_error = max(pure_axis_area_error,abs(sx*sy-1))
                pure_cases.append((sx,sy))
    assert pure_axis_area_error < 1e-12
    diagonal_cases = []
    for px,py in ((10,10),(30,15),(15,30),(-30,15),(30,-15),(300,300)):
        sx,sy,amplitude = scales(px,py,80,80)
        assert sx*sy > 1
        diagonal_cases.append(dict(pull=[px,py],scale_x=sx,scale_y=sy,area_factor=sx*sy))

    ellipse_error = contour_error = normal_error = polygon_error = 0.0
    contour_samples = 0
    shape_cases = []
    for name,width,height,radius in (('circle',80,80,40),('rounded_rectangle',140,70,16),('horizontal_capsule',160,40,20),('vertical_capsule',32,120,16)):
        base = contour(width,height,radius)
        for px,py in ((26,0),(0,26),(26,26),(30,10),(-10,30)):
            sx,sy,amplitude = scales(px,py,width,height)
            transformed = [forward(x,y,sx,sy)for x,y in base]
            area_error = abs(polygon_area(transformed)/polygon_area(base)-sx*sy)
            polygon_error = max(polygon_error,area_error)
            for x,y in transformed:
                d,n = distance_normal(x,y,width,height,radius,sx,sy,amplitude)
                dm,nm = distance_normal(-x,-y,width,height,radius,sx,sy,amplitude)
                contour_error = max(contour_error,abs(d))
                symmetry_error = max(symmetry_error,abs(d-dm),math.hypot(n[0]+nm[0],n[1]+nm[1]))
                if name == 'circle':
                    ellipse_error = max(ellipse_error,abs((x/(radius*sx))**2+(y/(radius*sy))**2-1))
                h=1e-4
                gx=(distance_normal(x+h,y,width,height,radius,sx,sy,amplitude)[0]-distance_normal(x-h,y,width,height,radius,sx,sy,amplitude)[0])/(2*h)
                gy=(distance_normal(x,y+h,width,height,radius,sx,sy,amplitude)[0]-distance_normal(x,y-h,width,height,radius,sx,sy,amplitude)[0])/(2*h)
                normal_error=max(normal_error,abs(1-(gx*n[0]+gy*n[1])/math.hypot(gx,gy)))
                contour_samples += 1
            # Level sides remain level and vertical sides remain vertical under all pulls.
            assert forward(-width/4,height/2,sx,sy)[1] == forward(width/4,height/2,sx,sy)[1]
            assert forward(width/2,-height/4,sx,sy)[0] == forward(width/2,height/4,sx,sy)[0]
            shape_cases.append(dict(shape=name,pull=[px,py],scale_x=sx,scale_y=sy,area_factor=sx*sy))
    assert ellipse_error < 1e-10 and contour_error < 1e-9
    assert symmetry_error < 1e-10 and normal_error < 1e-8 and polygon_error < 1e-12
    assert scales(0,0,80,80)==(1,1,0)
    return {
        'status':'passed',
        'model':'World-axis diagonal deformation matrix diag(scaleX,scaleY); no rotation, shear, taper or center shift. Each pull channel stretches its own axis; reciprocal cross-squeeze fades when both channels are active.',
        'random_inverse_and_axis_matrix_cases':2500,
        'max_inverse_error':inverse_error,
        'max_off_diagonal_transform':off_diagonal,
        'max_opposite_point_or_normal_symmetry_error':symmetry_error,
        'scale_bounds':[1/1.65,1.65],
        'pure_axis_cases':len(pure_cases),
        'max_pure_axis_area_factor_error':pure_axis_area_error,
        'diagonal_area_is_intentionally_not_preserved':True,
        'diagonal_cases':diagonal_cases,
        'contour_samples':contour_samples,
        'max_axis_aligned_ellipse_equation_residual':ellipse_error,
        'max_forward_contour_distance_error':contour_error,
        'max_normal_gradient_alignment_error':normal_error,
        'max_polygon_area_factor_error':polygon_error,
        'two_amplitude_bounds_corner_samples':10000,
        'max_extent_outside_two_amplitude_bounds':max(0,bounds_excess),
        'one_amplitude_bounds_also_sufficient_for_axis_formula':True,
        'zero_pull_identity':True,
        'shape_cases':shape_cases,
    }


if __name__=='__main__':
    import json
    print(json.dumps(run_checks(),indent=2))
