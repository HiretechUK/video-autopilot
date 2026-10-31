"""Paws & Claws Club test scene (Blender 3.6): Ziggy (cat) and Waffles (dog) sing and dance in the barn.

Characters and barn: Blender Studio "Pet Projects" / Wing It! production files (CC-BY, Blender Foundation |
studio.blender.org), from the free Blender 3.6 splash download.

Run: blender -b -y --python paws_scene.py -- LIB_DIR TIMING_JSON OUT_DIR START END PERCENT SAMPLES
Frames START..END (inclusive) are rendered as OUT_DIR/####.png. Every frame's pose is a pure function of time,
so separate machines can render separate frame ranges.
"""
import json
import math
import sys

import bpy

a = sys.argv[sys.argv.index("--") + 1:]
LIB, TIMING, OUT = a[0].rstrip("/") + "/", a[1], a[2].rstrip("/") + "/"
START, END, PCT, SAMPLES = int(a[3]), int(a[4]), int(a[5]), int(a[6])
T = json.load(open(TIMING))
FPS = T["fps"]
BEATS = T["beats"]
P = (BEATS[-1] - BEATS[0]) / (len(BEATS) - 1)

bpy.ops.wm.read_homefile(use_empty=True)
sc = bpy.context.scene
vl = bpy.context.view_layer


def link_char(name):
    with bpy.data.libraries.load(LIB + f"char/{name}/publish/{name}.v001.blend", link=True) as (src, dst):
        dst.collections = [f"CH-{name}"]
    col = dst.collections[0]
    sc.collection.children.link(col)
    ov = col.override_hierarchy_create(sc, vl, do_fully_editable=True)
    sc.collection.children.unlink(col)
    return [o for o in ov.all_objects if o.type == "ARMATURE"][0]


cat = link_char("cat")
dog = link_char("dog")
cat.scale = (1.5, 1.5, 1.5)
cat.location = (-0.6, 0.0, 0.0)
dog.location = (0.65, 0.2, 0.0)
cat.rotation_euler = (0, 0, math.radians(12))
dog.rotation_euler = (0, 0, math.radians(-10))

# outdoor meadow: soft rolling hills, lollipop trees, flowers (CoComelon-bright, Pixar-soft)
def mat(name, rgb, rough=0.6, sheen=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Sheen"].default_value = sheen
    return m


grass = mat("grass", (0.22, 0.55, 0.12), 0.9, 0.6)
bpy.ops.mesh.primitive_plane_add(size=80)
bpy.context.object.data.materials.append(grass)
import random
random.seed(4)
for i in range(7):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=random.uniform(5, 9), location=(random.uniform(-18, 18), random.uniform(14, 30), -3.5), segments=48, ring_count=24)
    h = bpy.context.object
    h.scale.z = 0.45
    bpy.ops.object.shade_smooth()
    h.data.materials.append(mat(f"hill{i}", random.choice([(0.36, 0.68, 0.24), (0.42, 0.74, 0.28), (0.30, 0.6, 0.22)]), 0.95, 0.5))
leaf = [mat("leaf1", (0.22, 0.55, 0.2), 0.7), mat("leaf2", (0.32, 0.65, 0.25), 0.7)]
bark = mat("bark", (0.45, 0.28, 0.15), 0.8)
for i, (x, y) in enumerate([(-4.5, 6), (5, 8), (-8, 12), (9, 14), (-2, 16), (3.5, 4.5)]):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=2.2, location=(x, y, 1.1))
    bpy.context.object.data.materials.append(bark)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.2 + 0.3 * (i % 3), location=(x, y, 2.9), segments=32, ring_count=16)
    bpy.ops.object.shade_smooth()
    bpy.context.object.data.materials.append(leaf[i % 2])
petal = [mat(f"pet{i}", c, 0.4) for i, c in enumerate([(1, .45, .7), (1, .82, .2), (1, 1, 1), (.7, .55, 1), (1, .55, .25)])]
for i in range(70):
    x, y = random.uniform(-6, 6), random.uniform(-1.5, 8)
    if abs(x) < 1.8 and y < 1.5:
        continue
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(x, y, 0.25), segments=12, ring_count=8)
    bpy.context.object.data.materials.append(petal[i % 5])
cloud = mat("cloud", (1, 1, 1), 0.9)
for i in range(5):
    for j in range(4):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.3 + 0.3 * (j % 2), location=(-14 + i * 7 + j * 1.3, 40, 11 + (i % 2) * 2 + math.sin(j) * 0.5), segments=24, ring_count=12)
        bpy.ops.object.shade_smooth()
        bpy.context.object.data.materials.append(cloud)

# light: warm key through the barn, cool sky fill, soft bounce
w = bpy.data.worlds.new("sky")
sc.world = w
w.use_nodes = True
bg = w.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.45, 0.7, 1.0, 1)
bg.inputs[1].default_value = 1.1
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(55), math.radians(8), math.radians(-35)))
sun = bpy.context.object
sun.data.energy = 4.5
sun.data.color = (1.0, 0.9, 0.75)
sun.data.angle = math.radians(8)
bpy.ops.object.light_add(type="AREA", location=(0, -4, 3.5), rotation=(math.radians(60), 0, 0))
fill = bpy.context.object
fill.data.energy = 600
fill.data.size = 6
fill.data.color = (0.85, 0.9, 1.0)

# camera: 9:16, eye level with the cat, slow drift
bpy.ops.object.camera_add()
cam = bpy.context.object
sc.camera = cam
cam.data.lens = 32
sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
sc.render.resolution_percentage = PCT
sc.render.fps = FPS
sc.render.engine = "CYCLES"
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True
sc.cycles.device = "CPU"
sc.render.use_motion_blur = False
sc.render.motion_blur_shutter = 0.4
sc.render.film_transparent = False
sc.view_settings.view_transform = "Filmic"
sc.view_settings.look = "High Contrast"
sc.view_settings.exposure = -0.35


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def beat_at(t):
    if t <= BEATS[0]:
        return (t - BEATS[0]) / P
    if t >= BEATS[-1]:
        return len(BEATS) - 1 + (t - BEATS[-1]) / P
    j = 0
    while BEATS[j + 1] < t:
        j += 1
    return j + (t - BEATS[j]) / (BEATS[j + 1] - BEATS[j])


def mouth(t):
    f = t * FPS
    i = int(f)
    k = f - i
    m = T["mouth"]
    x0 = m[i] if i < len(m) else 0
    x1 = m[i + 1] if i + 1 < len(m) else 0
    return x0 + (x1 - x0) * k


def pb(r, n):
    return r.pose.bones.get(n)


for r in (cat, dog):  # arms in FK so we can pose them directly
    for s in ("L", "R"):
        p = pb(r, f"PRP-UpperArm.{s}")
        if p:
            for k in list(p.keys()):
                if k.startswith("ik_") and not k.startswith(("ik_stretch", "ik_pole", "ik_parents")):
                    p[k] = 0.0
    for b in r.pose.bones:
        b.rotation_mode = "XYZ"


def pose(r, t, who):
    """Choreography: 8-beat blocks cycling sway-wave, arm pumps, clap, big open arms; head and tail follow."""
    beat = beat_at(t)
    ph = beat * math.pi
    lag = 0.35 if who == "dog" else 0.0          # the dog is half a step behind the cat (reads as two characters)
    ph2 = ph - lag
    hop = 0.5 - 0.5 * math.cos(2 * ph2)          # smooth hop, 0 on each beat
    blk = int(max(0.0, beat) // 8) % 4
    last = t > T["duration"] - 4.0
    if last:
        blk = 3
    rt = pb(r, "root")
    rt.location = (math.sin(ph2 / 2) * (0.06 if blk == 0 else 0.0), 0, (0.10 if who == "cat" else 0.07) * hop)
    tor = pb(r, "MSTR-Torso")
    tor.rotation_euler = (0, math.sin(ph2) * 0.06, math.sin(ph2 / 2) * 0.12)
    head = pb(r, "FK-Head")
    head.rotation_euler = (math.sin(2 * ph2 - 0.9) * 0.10, 0, math.sin(ph2 / 2 - 0.6) * 0.22)
    for s, sg in (("L", -1), ("R", 1)):
        u = pb(r, f"FK-UpperArm.{s}")
        fa = pb(r, f"FK-Forearm.{s}")
        down = math.radians(70) * sg            # arms resting at the sides (rig default is a T-pose)
        if blk == 0:      # sway with a little wave on the beat
            z = down * 0.8 - sg * math.radians(10 * hop)
            x = math.radians(-15)
            fz = -sg * math.radians(25 + 35 * hop)
        elif blk == 1:    # pump the arms up and down, alternating
            alt = math.sin(ph2 + (math.pi if s == "L" else 0))
            z = -sg * math.radians(35 + 45 * max(0.0, alt))
            x = 0.0
            fz = -sg * math.radians(30)
        elif blk == 2:    # clap in front of the chest on every beat
            c = abs(math.sin(ph2))
            z = down - sg * math.radians(40)
            x = math.radians(-70)
            fz = -sg * math.radians(15 + 35 * (1 - c))
        else:             # big open arms, celebrating
            o = ease((t - (T["duration"] - 4.0)) / 1.0) if last else 1.0
            z = down - sg * math.radians(70 + 60 * o) + sg * math.radians(8) * hop
            x = 0.0
            fz = -sg * math.radians(10)
        if u:
            u.rotation_euler = (x, 0, z)
        if fa:
            fa.rotation_euler = (0, 0, fz)
    for i, n in enumerate(("FK-Tail1", "FK-Tail2", "FK-Tail3")):
        tb = pb(r, n)
        if tb:
            tb.rotation_euler = (0, 0, math.sin(ph2 * 1.5 - i * 0.7) * 0.35)
    for s, sg in (("L", 1), ("R", -1)):
        for n in (f"FK-Ear1.{s}", f"FK-Ear2.{s}"):
            eb = pb(r, n)
            if eb:
                eb.rotation_euler = (0, 0, sg * 0.25 * math.exp(-((math.sin(ph2)) ** 2) / 0.05))
    mm = pb(r, "ACT-Mouth_Move")
    if mm:
        mm.location = (0, -(0.09 if who == "cat" else 0.08) * mouth(t), 0)


def camera(t):
    d = T["duration"]
    push = ease(t / 3.0)
    dist = 5.6 - 1.4 * push
    if t > d - 3.0:
        dist += 1.4 * ease((t - (d - 3.0)) / 3.0)
    orbit = math.sin(t * 0.25) * 0.12
    cam.location = (math.sin(orbit) * dist + 0.05, -math.cos(orbit) * dist, 1.15 + 0.05 * math.sin(t * 0.8))
    tx, ty, tz = 0.05, 0.1, 1.55
    dx, dy, dz = tx - cam.location.x, ty - cam.location.y, tz - cam.location.z
    cam.rotation_euler = (math.atan2(math.hypot(dx, dy), -dz), 0, math.atan2(dy, dx) - math.pi / 2)


sc.render.image_settings.file_format = "PNG"
for f in range(START, END + 1):
    t = f / FPS
    sc.frame_set(f)
    pose(cat, t, "cat")
    pose(dog, t, "dog")
    camera(t)
    vl.update()
    sc.render.filepath = OUT + f"{f:04d}.png"
    bpy.ops.render.render(write_still=True)
    print("FRAME", f, flush=True)
print("RANGE DONE", START, END)
