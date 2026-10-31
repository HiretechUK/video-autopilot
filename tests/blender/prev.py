import bpy, sys
s = bpy.context.scene
print("PREV scenes", [x.name for x in bpy.data.scenes], "camera", s.camera, "frame", s.frame_current)
print("PREV armatures", [(o.name, len(o.data.bones)) for o in bpy.data.objects if o.type == 'ARMATURE'])
print("PREV missing libs", [l.filepath for l in bpy.data.libraries if l.is_missing])
if s.camera is None:
    cams = [o for o in bpy.data.objects if o.type == 'CAMERA']
    if cams:
        s.camera = cams[0]
s.render.engine = 'CYCLES'; s.cycles.samples = 16; s.cycles.use_denoising = True; s.cycles.device = 'CPU'
s.render.use_simplify = True; s.render.simplify_subdivision_render = 1; s.render.simplify_child_particles_render = float(sys.argv[-3])
s.render.resolution_percentage = int(sys.argv[-2]); s.render.filepath = sys.argv[-1]; s.render.image_settings.file_format = 'JPEG'
s.render.use_compositing = False
bpy.ops.render.render(write_still=True)
print("PREV done")
