# Breaking Point Studio — Blender grid kit (copied from Impossible Builds) ("X-Ray Grid" look).
# THE single source of truth for the look: every approved setting lives here
# (why each one exists: STYLE.md; what it should look like: reference.png).
# Episode scripts only build their parts and call these functions — they
# never set colours, lights, camera numbers or render settings themselves.
#
#   import sys; sys.path.append(r"<path to this project>\blender\kit")
#   import grid_kit as kit
#   out, stills, final = kit.cli(__file__, "my_preview.mp4")
#   look, rig = kit.setup(out, shot="orbit", preview=not final)  # look, camera, orbit, timing
#   part.data.materials.append(look.mat("accent"))   # shell / accent / neutral / hot
#   kit.cutaway([outer, ..., inner], mode="quarter", ghost_material=look.mat("ghost"))
#   kit.glow_sphere("Star")            # glowing star: crisp, textured, thin halo, floor glow
#   mount, line = kit.orbit_mount()    # tilted mount + faint cyan orbit line
#   kit.solar_panel(name, sunlit=...)  # cyan cell-grid panel with a bright edge
#   kit.fly_in_on_orbit(part, angle, f_start, f_land)   # arrive on an orbit slot
#   kit.arrive(part, start, target, f_start, f_land)    # any arrival: overshoot, settle, flash
#   kit.safe_zone_report([...parts...])   # warns if a part leaves the safe zone
#   kit.render(out, stills)               # MP4, or PNG stills
#
# Animation rules (CLAUDE.md): motion starts on frame 1; every arrival
# overshoots, settles and flashes once; important action stays in the safe zone.
import math
import bpy
from mathutils import Vector

# ---------------------------------------------------------------- palette
PALETTE = {
    "cyan":   "#00C2FF",  # electric cyan
    "orange": "#FF6B2C",  # warning orange
    "grey_1": "#0A0B0D",  # background
    "grey_2": "#111316",  # floor
    "grey_3": "#2C3136",  # grid lines
    "grey_4": "#3A3F45",  # outer shell
    "grey_5": "#6B7078",  # neutral parts
}


def hex_to_linear(hex_color):
    """'#00C2FF' -> linear RGB tuple, so Blender shows the exact hex colour."""
    h = hex_color.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb)


def rgba(hex_color):
    return (*hex_to_linear(hex_color), 1.0)


# ---------------------------------------------------------------- the look
# Material roles:
#   shell   – outer skin of a build (dark grey)
#   accent  – the cyan part (the "solution")
#   neutral – supporting grey parts
#   hot     – the orange part (the "problem" / the core / the warning)
#   ghost   – the removed cutaway piece: faint glass with a glowing cyan edge
# Light positions are relative to the camera rig (camera sits at -Y),
# so the look stays the same from any orbit angle.
STYLE = {
    "name": "X-Ray Grid",
    "world": "#0A0B0D", "world_strength": 1.0,
    "floor": "#111316", "floor_rough": 0.6,
    "grid": {"line": "#2C3136", "spacing": 0.5, "width": 0.012},
    "materials": {
        "shell":   ("#3A3F45", 0.4),
        "accent":  ("#00C2FF", 0.3),
        "neutral": ("#6B7078", 0.4),
        "hot":     ("#FF6B2C", 0.3),
    },
    # (name, location, energy W, size, colour) — all soft area lights
    "lights": [
        ("Key",  (-4.0, -3.0, 5.0), 600, 3.0, "#FFFFFF"),
        ("Fill", ( 4.5, -2.0, 1.5), 100, 3.0, "#FFFFFF"),
        ("Rim",  (-1.5,  3.5, 3.0), 400, 2.0, "#FFFFFF"),
    ],
}


# ---------------------------------------------------------------- scene
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def _link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def empty(name, location=(0, 0, 0), parent=None):
    e = _link(bpy.data.objects.new(name, None))
    e.location = location
    e.parent = parent
    return e


def look_at(obj, target):
    c = obj.constraints.new("TRACK_TO")
    c.target = target
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    return c


# ---------------------------------------------------------------- materials
def mat_solid(name, hex_color, roughness=0.45):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = rgba(hex_color)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def mat_ghost(name, hex_color="#00C2FF", alpha=0.03, edge_glow=3.0):
    """See-through glass with a glowing edge (shows a removed piece)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = rgba(hex_color)
    bsdf.inputs["Roughness"].default_value = 0.2
    bsdf.inputs["Alpha"].default_value = alpha
    bsdf.inputs["Emission Color"].default_value = rgba(hex_color)
    # Glow only where the surface turns away from the camera (the edges)
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    p = nt.nodes.new("ShaderNodeMath"); p.operation = "POWER"
    p.inputs[1].default_value = 4.0
    m = nt.nodes.new("ShaderNodeMath"); m.operation = "MULTIPLY"
    m.inputs[1].default_value = edge_glow
    nt.links.new(lw.outputs["Facing"], p.inputs[0])
    nt.links.new(p.outputs[0], m.inputs[0])
    nt.links.new(m.outputs[0], bsdf.inputs["Emission Strength"])
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    if hasattr(mat, "use_transparent_shadow"):
        mat.use_transparent_shadow = True
    return mat


def mat_grid_floor(name, base_hex, line_hex, spacing=0.5, width=0.012, roughness=0.6):
    """Floor with thin engineering grid lines."""
    mat = mat_solid(name, base_hex, roughness)
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    lines = []
    for axis in ("X", "Y"):
        # distance to the nearest grid line, then "is it closer than width?"
        pp = nt.nodes.new("ShaderNodeMath"); pp.operation = "PINGPONG"
        pp.inputs[1].default_value = spacing / 2
        lt = nt.nodes.new("ShaderNodeMath"); lt.operation = "LESS_THAN"
        lt.inputs[1].default_value = width
        nt.links.new(sep.outputs[axis], pp.inputs[0])
        nt.links.new(pp.outputs[0], lt.inputs[0])
        lines.append(lt)
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MAXIMUM"
    nt.links.new(lines[0].outputs[0], mx.inputs[0])
    nt.links.new(lines[1].outputs[0], mx.inputs[1])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].color = rgba(base_hex)
    ramp.color_ramp.elements[1].position = 0.5
    ramp.color_ramp.elements[1].color = rgba(line_hex)
    nt.links.new(mx.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


class Look:
    """What apply_look() returns: the materials and lights."""
    def __init__(self):
        self.materials = {}
        self.lights = []

    def mat(self, role):
        return self.materials[role]


def apply_look(rig=None, floor_z=-1.0):
    """Builds background, grid floor, lights and materials.
    Pass the camera rig so lights travel with the camera during an orbit.
    floor_z = height of the floor (put it under the build)."""
    scene = bpy.context.scene
    scene["ib_floor_z"] = floor_z  # other kit parts (floor glow) need it
    look = Look()

    # Background (also the soft ambient light)
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = rgba(STYLE["world"])
    bg.inputs["Strength"].default_value = STYLE["world_strength"]
    scene.world = world

    # Grid floor: big enough to fill the frame edge to edge
    bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, floor_z))
    floor = bpy.context.active_object
    floor.name = "Floor"
    g = STYLE["grid"]
    floor.data.materials.append(mat_grid_floor(
        "Floor", STYLE["floor"], g["line"], g["spacing"], g["width"], STYLE["floor_rough"]))

    # Palette materials by role
    for role, (hex_color, rough) in STYLE["materials"].items():
        look.materials[role] = mat_solid(role, hex_color, rough)
    look.materials["ghost"] = mat_ghost("ghost")

    # Lights, aimed at the subject
    aim = bpy.data.objects.get("CamTarget") or empty("LightTarget")
    for lname, loc, energy, size, color in STYLE["lights"]:
        data = bpy.data.lights.new(lname, "AREA")
        data.energy = energy
        data.size = size
        data.color = hex_to_linear(color)
        light = _link(bpy.data.objects.new(lname, data))
        light.parent = rig
        light.location = loc
        look_at(light, aim)
        look.lights.append(light)
    return look


# ---------------------------------------------------------------- camera
# Shorts framing: nudge the subject left (away from YouTube's buttons on the
# right) and up (away from the title/caption area at the bottom).
SHORTS_SHIFT = (0.03, -0.03)


def camera_rig(angle=-35.0, distance=6.5, height=3.0, target_z=0.0, lens=50,
               shift=(0.0, 0.0)):
    """Turntable rig. The camera rides on 'CamRig'; turn CamRig around Z
    to orbit. angle 0 = camera looking from -Y (the front).
    shift = lens shift (x, y): positive x moves the subject left on screen."""
    rig = empty("CamRig", (0, 0, target_z))
    target = empty("CamTarget", (0, 0, 0), parent=rig)
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = lens
    cam_data.shift_x, cam_data.shift_y = shift
    cam = _link(bpy.data.objects.new("Camera", cam_data))
    cam.parent = rig
    cam.location = (0, -distance, height)
    look_at(cam, target)
    bpy.context.scene.camera = cam
    set_orbit(rig, angle)
    return rig


def set_orbit(rig, angle_deg):
    rig.rotation_euler = (0, 0, math.radians(angle_deg))


def orbit(rig, start_deg, end_deg, frame_start=None, frame_end=None):
    """Slow, steady (linear) camera orbit across the whole shot."""
    scene = bpy.context.scene
    fs = scene.frame_start if frame_start is None else frame_start
    fe = scene.frame_end if frame_end is None else frame_end
    with _interpolation("LINEAR"):
        set_orbit(rig, start_deg)
        rig.keyframe_insert("rotation_euler", index=2, frame=fs)
        set_orbit(rig, end_deg)
        rig.keyframe_insert("rotation_euler", index=2, frame=fe)


# ---------------------------------------------------------------- glow
def _math(nt, op, a=None, b=None, clamp=False):
    m = nt.nodes.new("ShaderNodeMath")
    m.operation = op
    m.use_clamp = clamp
    if a is not None:
        m.inputs[0].default_value = a
    if b is not None:
        m.inputs[1].default_value = b
    return m


def _emission_only(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    return mat, nt


def mat_glow_surface(name, hex_color, centre_hex="#FFC94D", rim_hex="#D9480F",
                     centre_boost=0.5, mottle=0.3):
    """Glowing surface, mottled like boiling gas. Colour runs from a bright
    yellow-orange centre (centre_hex) through hex_color to a deeper rim
    (rim_hex); brightness runs from 1.0 at the rim to 1.5 in the middle.
    The brightness comes mostly from the yellow colour, not from pushing the
    strength very high: red is already full, so a big strength just clips
    everything to flat red/yellow and wipes out the texture and the edge."""
    mat, nt = _emission_only(name)
    L = nt.links.new
    lw = nt.nodes.new("ShaderNodeLayerWeight")  # Facing: 0 centre .. 1 rim
    lw.inputs["Blend"].default_value = 0.5
    centre = _math(nt, "SUBTRACT", a=1.0)
    L(lw.outputs["Facing"], centre.inputs[1])
    centre2 = _math(nt, "POWER", b=2.0)
    L(centre.outputs[0], centre2.inputs[0])
    bright = _math(nt, "MULTIPLY_ADD")
    bright.inputs[1].default_value = centre_boost
    bright.inputs[2].default_value = 1.0
    L(centre2.outputs[0], bright.inputs[0])
    # Colour: yellow-orange centre -> palette orange -> deeper orange rim
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, rgba(centre_hex)
    els[1].position, els[1].color = 1.0, rgba(rim_hex)
    mid = els.new(0.6)
    mid.color = rgba(hex_color)
    L(lw.outputs["Facing"], ramp.inputs["Fac"])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 4.0  # big cells: survive small sizes and video compression
    noise.inputs["Detail"].default_value = 4.0
    noise.inputs["Roughness"].default_value = 0.6
    L(tc.outputs["Object"], noise.inputs["Vector"])
    mot = _math(nt, "MULTIPLY_ADD")  # 1-mottle .. 1+mottle
    mot.inputs[1].default_value = 2 * mottle
    mot.inputs[2].default_value = 1 - mottle
    # Noise mostly stays between 0.3 and 0.7; stretch that to 0..1 so the
    # mottling actually shows at the strength we ask for
    stretch = nt.nodes.new("ShaderNodeMapRange")
    stretch.clamp = True
    stretch.inputs["From Min"].default_value = 0.3
    stretch.inputs["From Max"].default_value = 0.7
    L(noise.outputs["Fac"], stretch.inputs["Value"])
    L(stretch.outputs["Result"], mot.inputs[0])
    strength = _math(nt, "MULTIPLY")
    L(bright.outputs[0], strength.inputs[0])
    L(mot.outputs[0], strength.inputs[1])
    emit = nt.nodes.new("ShaderNodeEmission")
    L(ramp.outputs["Color"], emit.inputs["Color"])
    L(strength.outputs[0], emit.inputs["Strength"])
    L(emit.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    return mat


def glow_halo(name, hex_color, radius, inner_radius, opacity=0.3, falloff=1.6, brightness=1.0,
              location=(0, 0, 0), parent=None):
    """Thin soft halo: a ring-shaped card that always faces the camera and sits
    just BEHIND the glowing object, so it never covers its crisp edge or surface.
    It paints the glow colour over whatever is behind it, so it looks the same
    on all sides (an added-on glow would fade over the brighter floor)."""
    mat, nt = _emission_only(name)
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    length = nt.nodes.new("ShaderNodeVectorMath")
    length.operation = "LENGTH"
    L(tc.outputs["Object"], length.inputs[0])
    # t = 1 at the object's edge (inner_radius), 0 at the halo's edge
    k = inner_radius / radius
    t = _math(nt, "SUBTRACT", a=1.0)
    L(length.outputs["Value"], t.inputs[1])
    t2 = _math(nt, "DIVIDE", b=1 - k, clamp=True)
    L(t.outputs[0], t2.inputs[0])
    pw = _math(nt, "POWER", b=falloff)
    L(t2.outputs[0], pw.inputs[0])
    op = _math(nt, "MULTIPLY", b=opacity, clamp=True)
    L(pw.outputs[0], op.inputs[0])
    # Hole in the middle: no glow at all where the object itself is
    hole = _math(nt, "GREATER_THAN", b=k)
    L(length.outputs["Value"], hole.inputs[0])
    op2 = _math(nt, "MULTIPLY")
    L(op.outputs[0], op2.inputs[0])
    L(hole.outputs[0], op2.inputs[1])
    op = op2
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = rgba(hex_color)
    emit.inputs["Strength"].default_value = brightness
    clear = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    L(op.outputs[0], mix.inputs["Fac"])
    L(clear.outputs[0], mix.inputs[1])
    L(emit.outputs[0], mix.inputs[2])
    L(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"

    # A pivot at the object's centre turns to face the camera; the card hangs
    # just behind the object on the far side.
    pivot = empty(f"{name} pivot", location, parent=parent)
    c = pivot.constraints.new("TRACK_TO")
    c.target = bpy.context.scene.camera
    c.track_axis = "TRACK_Z"
    c.up_axis = "UP_Y"
    bpy.ops.mesh.primitive_circle_add(vertices=96, radius=1.0, fill_type="NGON")
    card = bpy.context.active_object
    card.name = name
    card.parent = pivot
    card.location = (0, 0, -inner_radius * 1.05)
    card.scale = (radius, radius, radius)
    card.data.materials.append(mat)
    card.visible_shadow = False
    return card


def glow_sphere(name="Star", radius=0.7, hex_color=PALETTE["orange"],
                halo_radius=None, light_energy=250, floor_glow=4500, location=(0, 0, 0)):
    """Glowing sphere (a star, a reactor core...) with an even soft halo,
    a light inside that lights nearby parts in its colour, and a warm pool of
    light on the floor below (floor_glow, watts; 0 = off).
    Keep it about 5 radii above the floor: a brightly lit floor right behind
    the halo washes out its lower half."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, radius=radius,
                                         location=location)
    s = bpy.context.active_object
    s.name = name
    bpy.ops.object.shade_smooth()
    s.data.materials.append(mat_glow_surface(f"{name} surface", hex_color))
    s.visible_shadow = False  # let the light inside shine out
    glow_halo(f"{name} halo", hex_color, halo_radius or radius * 1.5, radius,
              location=location)
    data = bpy.data.lights.new(f"{name} light", "POINT")
    data.energy = light_energy
    data.color = hex_to_linear(hex_color)
    data.shadow_soft_size = radius
    light = _link(bpy.data.objects.new(f"{name} light", data))
    light.location = location
    if floor_glow:
        _floor_glow(name, s, radius, hex_color, floor_glow)
    return s


def _floor_glow(name, sphere, radius, hex_color, power, below=1.8, cone_deg=75):
    """Warm pool of light on the floor that appears directly UNDER the sphere
    on screen. The floor straight below is far down and shows up near the
    bottom of the frame, so instead the light is aimed at the patch of floor
    the camera sees just below the sphere (below = how far under, in radii).
    The aim point rides on the camera rig, so the pool stays put during an
    orbit. power = brightness, as if a light of that many watts hung straight
    above the pool at the floor's depth. The narrow cone misses parts that
    orbit beside the sphere."""
    scene = bpy.context.scene
    cam = scene.camera
    rig = cam.parent if cam else None
    floor_z = scene.get("ib_floor_z")
    if rig is None or floor_z is None:
        return None
    centre = sphere.location - rig.location            # rig-local (orbit axis)
    cam_pos = Vector(cam.location)                     # camera in rig space
    aim = centre - Vector((0, 0, below * radius))      # just under the sphere
    ray = aim - cam_pos
    floor_local = floor_z - rig.location.z
    t = (floor_local - cam_pos.z) / ray.z
    pool = cam_pos + ray * t                           # where that ray hits the floor
    target = empty(f"{name} floor glow target", tuple(pool), parent=rig)

    drop = centre.z - floor_local
    dist = (pool - centre).length
    spot = bpy.data.lights.new(f"{name} floor glow", "SPOT")
    spot.energy = power * (dist / drop) ** 2 / (drop / dist)  # same brightness as overhead
    spot.color = hex_to_linear(hex_color)
    spot.spot_size = math.radians(cone_deg)
    spot.spot_blend = 1.0
    spot.shadow_soft_size = radius
    sp = _link(bpy.data.objects.new(f"{name} floor glow", spot))
    sp.location = sphere.location
    look_at(sp, target)
    return sp


def orbit_line(radius, parent=None, hex_color=PALETTE["cyan"], strength=0.5,
               thickness=0.008):
    """Thin, faint guide circle (an orbit, a track). Lies flat in the
    parent's XY plane."""
    mat, nt = _emission_only("orbit line")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = rgba(hex_color)
    emit.inputs["Strength"].default_value = strength
    nt.links.new(emit.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    bpy.ops.mesh.primitive_torus_add(major_radius=radius, minor_radius=thickness,
                                     major_segments=256, minor_segments=8)
    ring = bpy.context.active_object
    ring.name = "Orbit line"
    ring.data.materials.append(mat)
    ring.visible_shadow = False
    ring.parent = parent
    return ring


# ---------------------------------------------------------------- solar panel
PANEL = {
    "size": (0.03, 0.8, 0.55),   # thin, wide, short (metres)
    "cells": (6, 4),             # cell grid across and up
    "cell_line": "#1A1C1F",      # dark lines between cells
    "edge_glow": 1.6,            # thin bright cyan edge
    # A panel whose visible face catches the star's light: deeper cyan, less
    # shine, plus a gentle cyan glow -> brightest panel, but rich not washed out
    "sunlit_hex": "#0077A8", "sunlit_line": "#0A0B0D", "sunlit_glow": 0.55,
}


def solar_panel(name, sunlit=False):
    """Cyan solar panel: fine dark cell grid and a thin bright edge.
    Thin along local X, so its flat faces point along X."""
    P = PANEL
    cell_hex = P["sunlit_hex"] if sunlit else PALETTE["cyan"]
    mat = bpy.data.materials.new(f"{name} panel")
    mat.use_nodes = True
    nt = mat.node_tree
    L = nt.links.new
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.6 if sunlit else 0.35
    if sunlit:
        bsdf.inputs["Specular IOR Level"].default_value = 0.2  # less white sheen
    bsdf.inputs["Emission Color"].default_value = rgba(PALETTE["cyan"])

    # Generated coords run 0..1 across the panel's width (Y) and height (Z)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    L(tc.outputs["Generated"], sep.inputs[0])

    def near_line(axis, spacing, width):
        pp = _math(nt, "PINGPONG", b=spacing / 2)  # distance to nearest line
        lt = _math(nt, "LESS_THAN", b=width)
        L(sep.outputs[axis], pp.inputs[0])
        L(pp.outputs[0], lt.inputs[0])
        return lt

    def either(a, b):
        mx = _math(nt, "MAXIMUM")
        L(a.outputs[0], mx.inputs[0])
        L(b.outputs[0], mx.inputs[1])
        return mx

    cells = P["cells"]
    grid = either(near_line("Y", 1 / cells[0], 0.012), near_line("Z", 1 / cells[1], 0.016))
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].color = rgba(cell_hex)
    ramp.color_ramp.elements[1].position = 0.5
    ramp.color_ramp.elements[1].color = rgba(P["sunlit_line"] if sunlit else P["cell_line"])
    L(grid.outputs[0], ramp.inputs["Fac"])
    L(ramp.outputs["Color"], bsdf.inputs["Base Color"])

    edge = either(near_line("Y", 1.0, 0.03), near_line("Z", 1.0, 0.045))
    edge_glow = _math(nt, "MULTIPLY", b=P["edge_glow"])
    L(edge.outputs[0], edge_glow.inputs[0])
    glow = edge_glow
    if sunlit:
        cells_only = _math(nt, "SUBTRACT", a=1.0)
        L(grid.outputs[0], cells_only.inputs[1])
        cell_glow = _math(nt, "MULTIPLY_ADD")
        cell_glow.inputs[1].default_value = P["sunlit_glow"]
        L(cells_only.outputs[0], cell_glow.inputs[0])
        L(edge_glow.outputs[0], cell_glow.inputs[2])
        glow = cell_glow
    L(glow.outputs[0], bsdf.inputs["Emission Strength"])

    bpy.ops.mesh.primitive_cube_add(size=1)
    p = bpy.context.active_object
    p.name = name
    p.scale = P["size"]
    p.data.materials.append(mat)
    return p


# ---------------------------------------------------------------- parts on an orbit
ORBIT = {
    "radius": 1.5,          # metres from the centre of what they orbit
    "tilt_deg": 20,         # far side tipped up so a part behind the star shows above it
    "toward_camera_deg": 30,  # parts still face the centre, but turn this much toward
                              # the camera so none is ever seen edge-on as a thin line
    "camera_side_deg": -90,   # in the mount, the camera sits in this direction
    # Flights start off-screen: further out and high above the resting spot
    "fly_from_scale": 2.8, "fly_from_height": 5.0,
    "tumble_deg": (70, -40, 160),  # starting tumble (x, y, extra z)
}


def orbit_mount(radius=None, name="Panel ring"):
    """Mount for parts on an orbit: turned to face the camera halfway through
    its orbit, tipped up at the back, with the faint cyan orbit line on it.
    Returns (mount, orbit_line)."""
    scene = bpy.context.scene
    radius = radius or ORBIT["radius"]
    mount = empty(name)
    mount.rotation_euler = (math.radians(ORBIT["tilt_deg"]), 0,
                            math.radians(scene.get("ib_mid_orbit", 0.0)))
    mount["radius"] = radius
    line = orbit_line(radius, parent=mount)
    return mount, line


def even_angles(count, first=-60.0):
    """Evenly spaced slots around an orbit, as angles seen from the camera
    (0 = straight in front of the centre). Default for 3: -60, 60, 180."""
    out = []
    for i in range(count):
        a = (first + 360.0 * i / count + 180.0) % 360.0 - 180.0
        out.append(180.0 if a == -180.0 else a)
    return out


def sunlit_from_camera(angle_from_camera):
    """True for a slot behind the centre: we see the face that looks at the star."""
    return abs(angle_from_camera) > 90


def arrival_schedule(count, first_land=30, gap=38, flight=28, preroll=70):
    """(flight start, landing) frames for parts arriving one at a time.
    The first flight starts before frame 1 (preroll) so a part is already
    moving into the shot on frame 1."""
    out = []
    for i in range(count):
        land = first_land + gap * i
        start = land - (preroll if i == 0 else flight)
        out.append((start, land))
    return out


def fly_in_on_orbit(part, angle_from_camera, f_start, f_land):
    """Flies a part (already parented to an orbit_mount) to its slot: facing
    the centre, turned a little toward the camera; overshoot, settle, flash."""
    mount = part.parent
    radius = mount["radius"] if mount and "radius" in mount else ORBIT["radius"]
    cam_side = math.radians(ORBIT["camera_side_deg"])
    a = math.radians(angle_from_camera) + cam_side
    seen_face = a if math.cos(a - cam_side) > 0 else a + math.pi
    diff = math.atan2(math.sin(cam_side - seen_face), math.cos(cam_side - seen_face))
    turn = math.copysign(min(abs(diff), math.radians(ORBIT["toward_camera_deg"])), diff)
    end_rot = (0, 0, a + turn)
    target = Vector((radius * math.cos(a), radius * math.sin(a), 0))
    k = ORBIT["fly_from_scale"]
    start = Vector((target.x * k, target.y * k, ORBIT["fly_from_height"]))
    tx, ty, tz = ORBIT["tumble_deg"]
    tumble = (math.radians(tx), math.radians(ty), a + math.radians(tz))
    arrive(part, start, target, f_start, f_land, start_rot=tumble, end_rot=end_rot)


# ---------------------------------------------------------------- arrivals
class _interpolation:
    """Temporarily set the interpolation used for new keyframes."""
    def __init__(self, kind):
        self.kind = kind

    def __enter__(self):
        self.prefs = bpy.context.preferences.edit
        self.old = self.prefs.keyframe_new_interpolation_type
        self.prefs.keyframe_new_interpolation_type = self.kind

    def __exit__(self, *exc):
        self.prefs.keyframe_new_interpolation_type = self.old


def add_flash(obj, hex_color=PALETTE["cyan"]):
    """Gives obj its own copy of its materials with a 'Flash' glow control.
    Returns the sockets to keyframe (one per material)."""
    sockets = []
    for slot in obj.material_slots:
        if slot.material is None or not slot.material.use_nodes:
            continue
        mat = slot.material.copy()
        slot.material = mat
        nt = mat.node_tree
        bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is None:
            continue
        col = bsdf.inputs["Emission Color"]
        if not col.is_linked:
            col.default_value = rgba(hex_color)
        strength = bsdf.inputs["Emission Strength"]
        add = _math(nt, "ADD", b=0.0)
        add.name = "Flash"
        if strength.is_linked:
            nt.links.new(strength.links[0].from_socket, add.inputs[0])
        else:
            add.inputs[0].default_value = strength.default_value
        nt.links.new(add.outputs[0], strength)
        sockets.append(add.inputs[1])
    return sockets


def arrive(obj, start, target, f_start, f_land, start_rot=None, end_rot=None,
           overshoot=0.12, twist_deg=8.0, settle=6, flash=3.0, flash_frames=10):
    """House arrival: fly from start to target, overshoot a little past it
    (with a small extra twist), settle back, and flash once on landing.
    f_start may be before frame 1 so a part is already moving on frame 1.
    Locations/rotations are in the object's parent space."""
    start, target = Vector(start), Vector(target)
    end_rot = tuple(end_rot if end_rot is not None else obj.rotation_euler)
    start_rot = tuple(start_rot if start_rot is not None else end_rot)
    over = target + (target - start).normalized() * overshoot
    over_rot = (end_rot[0], end_rot[1], end_rot[2] + math.radians(twist_deg))
    first = bpy.context.scene.frame_start

    def key(frame, loc, rot):
        obj.location = loc
        obj.rotation_euler = rot
        obj.keyframe_insert("location", frame=frame)
        obj.keyframe_insert("rotation_euler", frame=frame)

    with _interpolation("BEZIER"):  # smooth ease in and out
        if f_start > first:
            key(first, start, start_rot)       # wait, hidden, until the flight starts
            obj.hide_render = True
            obj.keyframe_insert("hide_render", frame=first)
            obj.hide_render = False
            obj.keyframe_insert("hide_render", frame=f_start)
        key(f_start, start, start_rot)         # fly in...
        key(f_land - settle, over, over_rot)   # ...overshoot...
        key(f_land, target, end_rot)           # ...settle
        for sock in add_flash(obj):            # ...and flash once
            for frame, v in ((f_land - settle, 0.0), (f_land, flash),
                             (f_land + flash_frames, 0.0)):
                sock.default_value = v
                sock.keyframe_insert("default_value", frame=frame)


# ---------------------------------------------------------------- safe zone
# Fractions of the frame (0 = left/bottom, 1 = right/top). Shorts: keep clear
# of the buttons on the right and the title/caption area at the bottom.
SAFE_ZONE = {
    "short": {"left": 0.06, "right": 0.82, "bottom": 0.24, "top": 0.94},
    "long":  {"left": 0.05, "right": 0.95, "bottom": 0.08, "top": 0.95},
}


def safe_zone_report(objects, frames=None, fmt="short"):
    """Checks that each object stays inside the safe zone on the given frames
    (default: every 5th frame). Prints and returns a list of problems.
    Only checks frames where the object has arrived / is meant to be seen —
    pass those frames for parts that fly in from off-screen."""
    from bpy_extras.object_utils import world_to_camera_view
    scene = bpy.context.scene
    cam = scene.camera
    zone = SAFE_ZONE[fmt]
    frames = frames or range(scene.frame_start, scene.frame_end + 1, 5)
    problems = []
    for f in frames:
        scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        for obj in objects:
            ev = obj.evaluated_get(dg)
            pts = [world_to_camera_view(scene, cam, ev.matrix_world @ Vector(c))
                   for c in ev.bound_box]
            xs, ys = [p.x for p in pts], [p.y for p in pts]
            out = []
            if min(xs) < zone["left"]:   out.append(f"left {min(xs):.2f}")
            if max(xs) > zone["right"]:  out.append(f"right {max(xs):.2f}")
            if min(ys) < zone["bottom"]: out.append(f"bottom {min(ys):.2f}")
            if max(ys) > zone["top"]:    out.append(f"top {max(ys):.2f}")
            if out:
                problems.append((f, obj.name, out))
    for f, name, out in problems:
        print(f"SAFE ZONE: frame {f}: {name} outside ({', '.join(out)})")
    if not problems:
        print("SAFE ZONE: all clear")
    return problems


# ---------------------------------------------------------------- cutaway
def cutaway(parts, mode="quarter", ghost_material=None, step=0.006, size=6.0):
    """Cuts a piece out of every part to show the inside.
    parts: list of objects, OUTSIDE first. Each inner part is cut a hair
    less so the cut faces never flicker.
    mode: 'half' (front half), 'quarter' (one wedge), 'octant' (top wedge).
    ghost_material: if given, the removed piece of the outer part is kept
    as a see-through ghost (use look.mat("ghost")).
    Move/rotate the 'Cutaway' empty to change or animate the cut."""
    ctl = empty("Cutaway")
    h = size / 2
    corner = {
        "half":    (0, -h, 0),
        "quarter": (-h, -h, 0),
        "octant":  (-h, -h, h),
    }[mode]
    push = {"half": (0, -1, 0), "quarter": (-1, -1, 0), "octant": (-1, -1, 1)}[mode]

    def make_cutter(name, offset):
        bpy.ops.mesh.primitive_cube_add(size=size)
        c = bpy.context.active_object
        c.name = name
        c.parent = ctl
        c.location = tuple(corner[i] + push[i] * offset for i in range(3))
        c.hide_render = True
        c.hide_viewport = True
        return c

    def boolean(obj, cutter, op):
        mod = obj.modifiers.new("Cutaway", "BOOLEAN")
        mod.operation = op
        mod.object = cutter
        mod.solver = "EXACT"

    for i, part in enumerate(parts):
        boolean(part, make_cutter(f"Cutter {part.name}", step * i), "DIFFERENCE")

    if ghost_material and parts:
        outer = parts[0]
        ghost = outer.copy()
        ghost.data = outer.data.copy()
        ghost.modifiers.clear()
        ghost.name = "Ghost"
        ghost.data.materials.clear()
        ghost.data.materials.append(ghost_material)
        _link(ghost)
        boolean(ghost, make_cutter("Cutter Ghost", -step), "INTERSECT")
    return ctl


# ---------------------------------------------------------------- render
def render_settings(out_path, preview=True, fmt="short"):
    """Eevee, Standard view transform (exact palette colours).
    fmt: 'short' 1080x1920 or 'long' 1920x1080. preview = half size, fewer samples."""
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    ee = scene.eevee
    ee.taa_render_samples = 32 if preview else 128
    if hasattr(ee, "use_raytracing"):
        ee.use_raytracing = True  # soft contact shadows and reflections
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    w, h = (1080, 1920) if fmt == "short" else (1920, 1080)
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.resolution_percentage = 50 if preview else 100
    scene.render.filepath = out_path
    scene.render.image_settings.file_format = "PNG"


def render(out_path, stills=None):
    """Renders the scene: a list of frames -> PNGs in the out_path folder;
    a still shot (one frame) -> one PNG at out_path; otherwise the whole
    shot -> MP4 (H.264) at out_path."""
    import os
    import time
    scene = bpy.context.scene
    if not stills and scene.frame_end <= scene.frame_start:
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        print("Saved:", out_path)
        return
    if stills:
        os.makedirs(out_path, exist_ok=True)
        for f in stills:
            scene.frame_set(f)
            scene.render.filepath = os.path.join(out_path, f"frame_{f:03d}.png")
            bpy.ops.render.render(write_still=True)
            print("Saved:", scene.render.filepath)
        return
    settings = scene.render.image_settings
    if hasattr(settings, "media_type"):
        settings.media_type = "VIDEO"
    settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.filepath = out_path
    t0 = time.perf_counter()
    bpy.ops.render.render(animation=True)
    print("Saved:", out_path)
    print(f"Total render time: {time.perf_counter() - t0:.1f} s")
    import gpu
    print("GPU used:", gpu.platform.renderer_get())


def cli(script_file, default_name):
    """Reads the command line after '--':  [output] [--stills 1,30,150] [--final]
    Returns (out_path, stills or None, final). Default output sits next to the script."""
    import os
    import sys
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    final = "--final" in args
    args = [a for a in args if a != "--final"]
    stills = None
    if "--stills" in args:
        i = args.index("--stills")
        stills = [int(f) for f in args[i + 1].split(",")]
        del args[i:i + 2]
    here = os.path.dirname(os.path.abspath(script_file))
    out_path = args[0] if args else os.path.join(here, default_name)
    return out_path, stills, final


# ---------------------------------------------------------------- shots
FPS = 30
# Approved camera set-ups. distance/height in metres from the subject's centre
# (height/distance keeps the same ~21° look-down angle in "orbit").
SHOTS = {
    # The approved hero shot (reference.png): slow 30° orbit over 5 s, pulled
    # back so the whole build sits in the Shorts safe zone; floor 3.6 m below
    # the subject so a glowing part's halo stays even all round.
    "orbit": {"angle": -50, "orbit_end": -20, "distance": 12.5, "height": 4.75,
              "floor_z": -3.6, "seconds": 5},
    # Wide still for big builds (Dyson swarm test).
    "swarm_wide": {"angle": -35, "orbit_end": None, "distance": 14.5, "height": 5.5,
                   "floor_z": -3.6, "seconds": 0},
    # Close still for a cutaway resting on the floor (layered sphere test).
    "cutaway_closeup": {"angle": -35, "orbit_end": None, "distance": 6.5, "height": 3.0,
                        "floor_z": -1.0, "seconds": 0},
}


# ---------------------------------------------------------------- one call
def setup(out_path, shot="orbit", preview=True, fmt="short"):
    """Empty scene + camera rig (+ its orbit) + full look + render settings
    + timing, all from the approved shot. Returns (look, rig).
    Preview is the default; set preview=False only after the owner approves
    the preview."""
    s = SHOTS[shot]
    scene = reset_scene()
    shift = SHORTS_SHIFT if fmt == "short" else (0.0, 0.0)
    rig = camera_rig(angle=s["angle"], distance=s["distance"], height=s["height"],
                     shift=shift)
    look = apply_look(rig=rig, floor_z=s["floor_z"])
    render_settings(out_path, preview=preview, fmt=fmt)
    scene["ib_shot"] = shot
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = max(1, int(s["seconds"] * FPS))
    scene.render.use_motion_blur = True  # streaks fast fly-ins a little
    end = s["orbit_end"]
    scene["ib_mid_orbit"] = (s["angle"] + end) / 2 if end is not None else s["angle"]
    if end is not None:
        orbit(rig, s["angle"], end)  # slow, steady, linear
    return look, rig
