import bpy, sys
s=bpy.context.scene
s.render.engine='CYCLES'; s.cycles.samples=16; s.cycles.use_denoising=True; s.cycles.device='CPU'
s.render.use_simplify=True; s.render.simplify_subdivision_render=1; s.render.simplify_child_particles_render=float(sys.argv[-3])
s.render.resolution_percentage=int(sys.argv[-2]); s.render.filepath=sys.argv[-1]; s.render.image_settings.file_format='JPEG'
bpy.ops.render.render(write_still=True)
