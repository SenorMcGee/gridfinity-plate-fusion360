"""Fusion 360 geometry builders using a single seed socket + RectangularPatternFeature."""
import math

import adsk.core
import adsk.fusion

from . import profile as P

MM = 0.1  # mm -> cm


def _pt(x, y, z=0.0):
    return adsk.core.Point3D.create(x * MM, y * MM, z * MM)


def _rounded_rect(sketch, x0, y0, x1, y1, r):
    """Draw a (rounded) rectangle in sketch coordinates (mm)."""
    lines = sketch.sketchCurves.sketchLines
    if r <= 0.01:
        lines.addTwoPointRectangle(_pt(x0, y0), _pt(x1, y1))
        return
    r = min(r, (x1 - x0) / 2 - 0.01, (y1 - y0) / 2 - 0.01)
    arcs = sketch.sketchCurves.sketchArcs
    lines.addByTwoPoints(_pt(x0 + r, y0), _pt(x1 - r, y0))
    lines.addByTwoPoints(_pt(x1, y0 + r), _pt(x1, y1 - r))
    lines.addByTwoPoints(_pt(x1 - r, y1), _pt(x0 + r, y1))
    lines.addByTwoPoints(_pt(x0, y1 - r), _pt(x0, y0 + r))
    half_pi = math.pi / 2
    for (cx, cy, sx, sy) in ((x1 - r, y0 + r, x1 - r, y0),
                             (x1 - r, y1 - r, x1, y1 - r),
                             (x0 + r, y1 - r, x0 + r, y1),
                             (x0 + r, y0 + r, x0, y0 + r)):
        arcs.addByCenterStartSweep(_pt(cx, cy), _pt(sx, sy), half_pi)


def _plus_cutout(sketch, cx0, cy0, pitch, wall_inset, tab_inset, r_wall, r_tab):
    """Draw the filament-saving '+' cutout that leaves 4 corner tabs for magnets."""
    lines = sketch.sketchCurves.sketchLines
    arcs = sketch.sketchCurves.sketchArcs
    half_pi = math.pi / 2

    w0x, w1x = cx0 + wall_inset, cx0 + pitch - wall_inset
    w0y, w1y = cy0 + wall_inset, cy0 + pitch - wall_inset
    t0x, t1x = cx0 + tab_inset, cx0 + pitch - tab_inset
    t0y, t1y = cy0 + tab_inset, cy0 + pitch - tab_inset

    # 8 straight segments of the '+' cutout
    lines.addByTwoPoints(_pt(t0x, w0y), _pt(t1x, w0y))                  # bottom edge
    lines.addByTwoPoints(_pt(t1x, w0y), _pt(t1x, t0y - r_tab))          # bottom-right vertical
    lines.addByTwoPoints(_pt(t1x + r_tab, t0y), _pt(w1x, t0y))          # bottom-right horizontal
    lines.addByTwoPoints(_pt(w1x, t0y), _pt(w1x, t1y))                  # right edge
    lines.addByTwoPoints(_pt(w1x, t1y), _pt(t1x + r_tab, t1y))          # top-right horizontal
    lines.addByTwoPoints(_pt(t1x, t1y + r_tab), _pt(t1x, w1y))          # top-right vertical
    lines.addByTwoPoints(_pt(t1x, w1y), _pt(t0x, w1y))                  # top edge
    lines.addByTwoPoints(_pt(t0x, w1y), _pt(t0x, t1y + r_tab))          # top-left vertical
    lines.addByTwoPoints(_pt(t0x - r_tab, t1y), _pt(w0x, t1y))          # top-left horizontal
    lines.addByTwoPoints(_pt(w0x, t1y), _pt(w0x, t0y))                  # left edge
    lines.addByTwoPoints(_pt(w0x, t0y), _pt(t0x - r_tab, t0y))          # bottom-left horizontal
    lines.addByTwoPoints(_pt(t0x, t0y - r_tab), _pt(t0x, w0y))          # bottom-left vertical

    # 4 rounded inner corners of the magnet tabs (each sweeps +90 deg CCW)
    arcs.addByCenterStartSweep(_pt(t1x + r_tab, t0y - r_tab), _pt(t1x + r_tab, t0y), half_pi)
    arcs.addByCenterStartSweep(_pt(t1x + r_tab, t1y + r_tab), _pt(t1x, t1y + r_tab), half_pi)
    arcs.addByCenterStartSweep(_pt(t0x - r_tab, t1y + r_tab), _pt(t0x - r_tab, t1y), half_pi)
    arcs.addByCenterStartSweep(_pt(t0x - r_tab, t0y - r_tab), _pt(t0x, t0y - r_tab), half_pi)


def _new_component(design, name):
    occ = design.rootComponent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    comp = occ.component
    comp.name = name
    return comp


def _offset_plane(comp, z_mm):
    planes = comp.constructionPlanes
    inp = planes.createInput()
    inp.setByOffset(comp.xYConstructionPlane, adsk.core.ValueInput.createByReal(z_mm * MM))
    plane = planes.add(inp)
    plane.isLightBulbOn = False
    return plane


def _split_into_tiles(comp, layout, tile_gap=0.0):
    """Split the component's bodies along layout.split_x and layout.split_y, rename tiles, and optionally separate them."""
    if not layout.split_x and not layout.split_y:
        return
    planes = comp.constructionPlanes
    split_feats = comp.features.splitBodyFeatures

    # Split along X (using YZ plane)
    yz = comp.yZConstructionPlane
    sign_x = 1.0 if yz.geometry.normal.x >= 0 else -1.0
    for sx in layout.split_x:
        inp = planes.createInput()
        inp.setByOffset(yz, adsk.core.ValueInput.createByReal(sign_x * sx * MM))
        pl = planes.add(inp)
        pl.isLightBulbOn = False
        bodies = adsk.core.ObjectCollection.create()
        for b in comp.bRepBodies:
            bodies.add(b)
        sb_in = split_feats.createInput(bodies, pl, True)
        split_feats.add(sb_in)

    # Split along Y (using XZ plane)
    xz = comp.xZConstructionPlane
    sign_y = 1.0 if xz.geometry.normal.y >= 0 else -1.0
    for sy in layout.split_y:
        inp = planes.createInput()
        inp.setByOffset(xz, adsk.core.ValueInput.createByReal(sign_y * sy * MM))
        pl = planes.add(inp)
        pl.isLightBulbOn = False
        bodies = adsk.core.ObjectCollection.create()
        for b in comp.bRepBodies:
            bodies.add(b)
        sb_in = split_feats.createInput(bodies, pl, True)
        split_feats.add(sb_in)

    # Match each resulting body to its tile by bounding-box center, name it, and apply visual gap if requested
    move_feats = comp.features.moveFeatures
    for b in list(comp.bRepBodies):
        bb = b.boundingBox
        cx = (bb.minPoint.x + bb.maxPoint.x) / 2.0 / MM
        cy = (bb.minPoint.y + bb.maxPoint.y) / 2.0 / MM
        best = min(
            layout.tiles,
            key=lambda t: (cx - (t.x0 + t.x1) / 2) ** 2 + (cy - (t.y0 + t.y1) / 2) ** 2)
        b.name = 'Tile_{}_{} ({:.0f}x{:.0f}mm)'.format(
            best.ty + 1, best.tx + 1, best.width, best.height)
        if tile_gap > 1e-4 and (best.tx > 0 or best.ty > 0):
            col = adsk.core.ObjectCollection.create()
            col.add(b)
            xform = adsk.core.Matrix3D.create()
            xform.translation = adsk.core.Vector3D.create(
                best.tx * tile_gap * MM, best.ty * tile_gap * MM, 0.0)
            mv_in = move_feats.createInput2(col)
            mv_in.defineAsFreeMove(xform)
            move_feats.add(mv_in)


def _extrude_slab(comp, length, width, thickness, outer_radius=0.0):
    sk = comp.sketches.add(comp.xYConstructionPlane)
    sk.isComputeDeferred = True
    _rounded_rect(sk, 0, 0, length, width, outer_radius)
    sk.isComputeDeferred = False
    ext = comp.features.extrudeFeatures.createInput(
        sk.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ext.setDistanceExtent(False, adsk.core.ValueInput.createByReal(thickness * MM))
    return comp.features.extrudeFeatures.add(ext).bodies.item(0)


def _cut_seed_socket(comp, cell, top_z, corner_min, pitch, opening, magnets=False, floor=0.0):
    """Cut the stepped socket profile (and magnet frame if magnets=True) for a single seed cell."""
    cx0, cy0 = cell.nominal_x, cell.nominal_y
    margin = (pitch - opening) / 2
    feats = []
    for (below, inset, depth, taper) in P.LAYERS:
        z = top_z - below
        plane = _offset_plane(comp, z)
        sk = comp.sketches.add(plane)
        sk.isComputeDeferred = True
        i = margin + inset
        r = max(P.CORNER_RADIUS - inset, corner_min, 0.5)
        _rounded_rect(sk, cx0 + i, cy0 + i, cx0 + pitch - i, cy0 + pitch - i, r)
        sk.isComputeDeferred = False
        prof = sk.profiles.item(0)
        ext_in = comp.features.extrudeFeatures.createInput(
            prof, adsk.fusion.FeatureOperations.CutFeatureOperation)
        ext_in.setOneSideExtent(
            adsk.fusion.DistanceExtentDefinition.create(
                adsk.core.ValueInput.createByReal(depth * MM)),
            adsk.fusion.ExtentDirections.NegativeExtentDirection,
            adsk.core.ValueInput.createByReal(math.radians(-taper)))
        feats.append(comp.features.extrudeFeatures.add(ext_in))

    if magnets:
        # 1. Cut the '+' center opening all the way down (leaving `floor` at bottom if > 0),
        #    leaving 4 corner tabs for the magnets.
        frame_z = top_z - P.PROFILE_HEIGHT
        frame_depth = frame_z - floor
        wall_inset = margin + P.TOP_CHAMFER + P.BOTTOM_CHAMFER  # 2.85 mm -> 36.3 mm inner opening
        plane_plus = _offset_plane(comp, frame_z)
        sk_plus = comp.sketches.add(plane_plus)
        sk_plus.isComputeDeferred = True
        _plus_cutout(sk_plus, cx0, cy0, pitch, wall_inset, P.TAB_INNER_OFFSET,
                     max(P.CORNER_RADIUS - (P.TOP_CHAMFER + P.BOTTOM_CHAMFER), 0.5),
                     P.TAB_FILLET_RADIUS)
        sk_plus.isComputeDeferred = False
        ext_plus = comp.features.extrudeFeatures.createInput(
            sk_plus.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation)
        ext_plus.setOneSideExtent(
            adsk.fusion.DistanceExtentDefinition.create(
                adsk.core.ValueInput.createByReal(frame_depth * MM)),
            adsk.fusion.ExtentDirections.NegativeExtentDirection,
            adsk.core.ValueInput.createByReal(0.0))
        feats.append(comp.features.extrudeFeatures.add(ext_plus))

        # 2. Cut the 4 magnet counterbores (from top of magnet tab downward) + screw through-holes
        r_mag = P.MAGNET_DIAMETER / 2
        r_scr = P.SCREW_DIAMETER / 2
        sk_mag = comp.sketches.add(plane_plus)
        sk_mag.isComputeDeferred = True
        for dx in (P.MAGNET_OFFSET, pitch - P.MAGNET_OFFSET):
            for dy in (P.MAGNET_OFFSET, pitch - P.MAGNET_OFFSET):
                hx, hy = cx0 + dx, cy0 + dy
                sk_mag.sketchCurves.sketchCircles.addByCenterRadius(_pt(hx, hy), r_mag * MM)
                sk_mag.sketchCurves.sketchCircles.addByCenterRadius(_pt(hx, hy), r_scr * MM)
        sk_mag.isComputeDeferred = False

        # Counterbore (all circle profiles, outer rings + inner circles = full 6.5mm cylinder)
        mag_profs = adsk.core.ObjectCollection.create()
        scr_profs = adsk.core.ObjectCollection.create()
        for p in sk_mag.profiles:
            mag_profs.add(p)
            if p.profileLoops.count == 1:
                scr_profs.add(p)

        ext_mag = comp.features.extrudeFeatures.createInput(
            mag_profs, adsk.fusion.FeatureOperations.CutFeatureOperation)
        ext_mag.setOneSideExtent(
            adsk.fusion.DistanceExtentDefinition.create(
                adsk.core.ValueInput.createByReal(P.MAGNET_DEPTH * MM)),
            adsk.fusion.ExtentDirections.NegativeExtentDirection,
            adsk.core.ValueInput.createByReal(0.0))
        feats.append(comp.features.extrudeFeatures.add(ext_mag))

        # Screw through-hole all the way through the tab
        if scr_profs.count > 0:
            ext_scr = comp.features.extrudeFeatures.createInput(
                scr_profs, adsk.fusion.FeatureOperations.CutFeatureOperation)
            ext_scr.setOneSideExtent(
                adsk.fusion.DistanceExtentDefinition.create(
                    adsk.core.ValueInput.createByReal(frame_z * MM)),
                adsk.fusion.ExtentDirections.NegativeExtentDirection,
                adsk.core.ValueInput.createByReal(0.0))
            feats.append(comp.features.extrudeFeatures.add(ext_scr))

    return feats


def _pattern_features(comp, feats, cols, rows, pitch):
    """Pattern a list of seed features across (cols x rows) at spacing = pitch."""
    if (cols <= 1 and rows <= 1) or not feats:
        return
    entities = adsk.core.ObjectCollection.create()
    for f in feats:
        entities.add(f)
    rect_feats = comp.features.rectangularPatternFeatures
    inp = rect_feats.createInput(
        entities,
        comp.xConstructionAxis,
        adsk.core.ValueInput.createByReal(max(cols, 1)),
        adsk.core.ValueInput.createByReal(pitch * MM),
        adsk.fusion.PatternDistanceType.SpacingPatternDistanceType)
    inp.setDirectionTwo(
        comp.yConstructionAxis,
        adsk.core.ValueInput.createByReal(max(rows, 1)),
        adsk.core.ValueInput.createByReal(pitch * MM))
    try:
        inp.patternComputeOption = adsk.fusion.PatternComputeOptions.OptimizedPatternCompute
    except Exception:
        pass
    rect_feats.add(inp)


def _socket_plate(design, name, layout, length, width, pitch, thickness,
                  corner_min, magnets, floor=0.0, outer_radius=0.0, tile_gap=0.0):
    tl = design.timeline
    start_idx = tl.markerPosition
    comp = _new_component(design, name)
    _extrude_slab(comp, length, width, thickness, outer_radius=outer_radius)
    if layout.cells:
        seed_feats = _cut_seed_socket(
            comp, layout.cells[0], thickness, corner_min, pitch,
            pitch - P.CLEARANCE, magnets=magnets, floor=floor)
        _pattern_features(comp, seed_feats, layout.cols, layout.rows, pitch)
    _split_into_tiles(comp, layout, tile_gap=tile_gap)
    end_idx = tl.markerPosition - 1
    if end_idx > start_idx:
        tl.timelineGroups.add(start_idx, end_idx)
    return comp


def build_printed(design, layout, length, width, pitch, floor, magnets, tile_gap=0.0):
    extra = (P.MAGNET_FRAME_HEIGHT if magnets else 0.0) + floor
    return _socket_plate(design, 'Gridfinity Plate (Printed)', layout, length, width,
                         pitch, P.PROFILE_HEIGHT + extra, 0.5, magnets, floor=floor,
                         outer_radius=P.CORNER_RADIUS, tile_gap=tile_gap)


def build_cnc(design, layout, length, width, pitch, stock_thickness, tool_diameter, tile_gap=0.0):
    return _socket_plate(design, 'Gridfinity Plate (CNC)', layout, length, width,
                         pitch, max(stock_thickness, P.PROFILE_HEIGHT + 0.5),
                         tool_diameter / 2, False, tile_gap=tile_gap)


def build_laser(design, layout, length, width, pitch, thickness, kerf, corner_radius, tile_gap=0.0):
    tl = design.timeline
    start_idx = tl.markerPosition
    comp = _new_component(design, 'Gridfinity Plate (Laser)')
    sk = comp.sketches.add(comp.xYConstructionPlane)
    sk.isComputeDeferred = True
    _rounded_rect(sk, 0, 0, length, width, 0)
    # In a flat 2D laser-cut Gridfinity baseplate, the cutout receives the bottom
    # foot of the bin (which is inset by TOP_CHAMFER + BOTTOM_CHAMFER = 2.85 mm per side,
    # leaving a 5.7 mm web/rib between adjacent cells).
    wall_inset = P.TOP_CHAMFER + P.BOTTOM_CHAMFER + kerf / 2
    for c in layout.cells:
        # Use nominal cell coordinates clipped to the plate bounds so partial cells work too
        x0 = max(c.x, c.nominal_x + wall_inset)
        y0 = max(c.y, c.nominal_y + wall_inset)
        x1 = min(c.x + c.w, c.nominal_x + pitch - wall_inset)
        y1 = min(c.y + c.h, c.nominal_y + pitch - wall_inset)
        if x1 - x0 > 1.0 and y1 - y0 > 1.0:
            _rounded_rect(sk, x0, y0, x1, y1, corner_radius)
    sk.isComputeDeferred = False
    profs = adsk.core.ObjectCollection.create()
    areas = sorted(sk.profiles, key=lambda p: p.areaProperties().area, reverse=True)
    for p in areas:
        if p.profileLoops.count > 1 or len(layout.cells) == 0:
            profs.add(p)
    if profs.count == 0 and areas:
        profs.add(areas[0])
    ext = comp.features.extrudeFeatures.createInput(
        profs, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ext.setDistanceExtent(False, adsk.core.ValueInput.createByReal(thickness * MM))
    comp.features.extrudeFeatures.add(ext)
    _split_into_tiles(comp, layout, tile_gap=tile_gap)
    end_idx = tl.markerPosition - 1
    if end_idx > start_idx:
        tl.timelineGroups.add(start_idx, end_idx)
    return comp
