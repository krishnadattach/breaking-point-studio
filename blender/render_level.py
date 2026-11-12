# One shot of "The Breaking Point": the object on the grid, tinted by level,
# with a SURVIVES or DESTROYED moment. Rendered with Eevee via the grid kit.
#
#   blender.exe -b -P blender/render_level.py -- <params.json>
#
# params.json: out, level (0 = hook), shape, verdict, seconds, fps, samples, verdict_at
# SKELETON VERSION: simple shapes, low res. Better visuals come later (see PROGRESS.md).
import json
import math
import os
import random
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(HERE, "kit"))
import grid_kit as kit  # noqa: E402

P = json.load(open(sys.argv[sys.argv.index("--") + 1], encoding="utf-8"))
level, shape, verdict = P["level"], P["shape"], P.get("verdict")
fps, seconds = P["fps"], P["seconds"]
frames = max(4, round(seconds * fps))
random.seed(level)  # same level -> same shake/fragments every time

# ---- scene from the kit: camera orbit, grid floor, lights, Eevee settings ----
HALF = {"sphere": 0.8, "cube": 0.7, "cone": 0.7}[shape]
kit.FPS = fps                                   # kit uses this for frame maths
kit.SHOTS["level"] = {"angle": -35, "orbit_end": -20, "distance": 7.0, "height": 2.6,
                      "floor_z": -HALF, "seconds": frames / fps}
look, rig = kit.setup(P["out"], shot="level", preview=True)
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, frames
scene.eevee.taa_render_samples = P["samples"]
scene.render.use_motion_blur = False

# ---- colour ramp: cyan (calm) -> orange -> red (extreme) as the level rises ----
STOPS = [(0.0, (0x00, 0xC2, 0xFF)), (0.55, (0xFF, 0x6B, 0x2C)), (1.0, (0xFF, 0x1E, 0x1E))]


def ramp(t):
    for (t0, c0), (t1, c1) in zip(STOPS, STOPS[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0)
            return "#%02X%02X%02X" % tuple(round(a + (b - a) * k) for a, b in zip(c0, c1))
    return "#%02X%02X%02X" % STOPS[-1][1]


colour = ramp(max(0, level - 1) / 9)

# ---- the object ----
if shape == "cube":
    bpy.ops.mesh.primitive_cube_add(size=1.4)
elif shape == "cone":
    bpy.ops.mesh.primitive_cone_add(radius1=0.8, depth=1.4)
else:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.8, segments=32, ring_count=16)
    bpy.ops.object.shade_smooth()
obj = bpy.context.active_object
obj.name = "Subject"
mat = kit.mat_solid("Subject", colour, 0.3)
obj.data.materials.append(mat)
bsdf = mat.node_tree.nodes.get("Principled BSDF")


def hexrgba(h):
    return kit.rgba(h)


def set_glow(strength, hex_colour=None, frame=None):
    """Emission = the object lights up. Keyframed when frame is given."""
    if bsdf is None:
        return
    if hex_colour:
        bsdf.inputs["Emission Color"].default_value = hexrgba(hex_colour)
    bsdf.inputs["Emission Strength"].default_value = strength
    if frame is not None:
        bsdf.inputs["Emission Color"].keyframe_insert("default_value", frame=frame)
        bsdf.inputs["Emission Strength"].keyframe_insert("default_value", frame=frame)


f_v = round(frames * P["verdict_at"])           # frame of the verdict moment
base_glow = 0.15 + 0.5 * level / 10

# ---- build-up: the object shakes harder as the level rises ----
amp = 0.01 + 0.012 * level
set_glow(base_glow, colour, frame=1)
for f in range(1, f_v, 2):
    obj.rotation_euler = (random.uniform(-amp, amp), random.uniform(-amp, amp), random.uniform(-amp, amp) * 2)
    obj.location = (random.uniform(-amp, amp) * 0.4, random.uniform(-amp, amp) * 0.4, 0)
    obj.keyframe_insert("rotation_euler", frame=f)
    obj.keyframe_insert("location", frame=f)
set_glow(base_glow, colour, frame=f_v - 1)

if verdict == "SURVIVES":
    # green flash + a proud pulse, then calm
    obj.scale = (1, 1, 1)
    obj.keyframe_insert("scale", frame=f_v)
    obj.scale = (1.25, 1.25, 1.25)
    obj.keyframe_insert("scale", frame=f_v + 3)
    obj.scale = (1, 1, 1)
    obj.keyframe_insert("scale", frame=f_v + 10)
    set_glow(6.0, "#3CFF8A", frame=f_v + 3)
    set_glow(base_glow + 0.4, "#3CFF8A", frame=min(frames, f_v + 14))
elif verdict == "DESTROYED":
    # red flash, the object vanishes and bursts into fragments that fall to the floor
    set_glow(8.0, "#FF3030", frame=f_v + 2)
    obj.hide_render = False
    obj.keyframe_insert("hide_render", frame=f_v + 2)
    obj.hide_render = True
    obj.keyframe_insert("hide_render", frame=f_v + 3)
    frag_mat = kit.mat_solid("Fragment", colour, 0.5)
    for i in range(16):
        bpy.ops.mesh.primitive_cube_add(size=random.uniform(0.15, 0.32), location=(0, 0, 0))
        fr = bpy.context.active_object
        fr.name = f"Fragment{i}"
        fr.data.materials.append(frag_mat)
        a = random.uniform(0, 2 * math.pi)
        r = random.uniform(1.2, 3.2)
        fr.hide_render = True
        fr.keyframe_insert("hide_render", frame=1)
        fr.hide_render = False
        fr.keyframe_insert("hide_render", frame=f_v + 3)
        fr.location = (random.uniform(-.2, .2), random.uniform(-.2, .2), 0.1)
        fr.keyframe_insert("location", frame=f_v + 3)
        fr.location = (math.cos(a) * r, math.sin(a) * r, -HALF + 0.12)
        fr.keyframe_insert("location", frame=min(frames, f_v + 16))
        fr.rotation_euler = (0, 0, 0)
        fr.keyframe_insert("rotation_euler", frame=f_v + 3)
        fr.rotation_euler = (random.uniform(0, 6), random.uniform(0, 6), random.uniform(0, 6))
        fr.keyframe_insert("rotation_euler", frame=min(frames, f_v + 16))
else:
    # hook shot: calm gentle breathing
    for f, s in ((1, 1.0), (frames // 2, 1.06), (frames, 1.0)):
        obj.scale = (s, s, s)
        obj.keyframe_insert("scale", frame=f)

kit.render(P["out"])
