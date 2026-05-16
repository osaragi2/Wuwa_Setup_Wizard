import bpy

from ..core.utils import Utils


# ========== VERTEX PROCESSOR ==========

# Handles vertex color manipulation for eye materials
class VertexProcessor:

    # ========== EYE COLORS ==========

    # Processes vertex colors for eye materials - sets black color on eye polys
    @staticmethod
    def process_eye_colors(mesh: bpy.types.Object) -> bool:
        if not mesh.data.vertex_colors:
            mesh.data.vertex_colors.new()
        vc_layer = mesh.data.vertex_colors.active
        eye_indices: set[int] = {i for i, slot in enumerate(mesh.material_slots)
                                 if slot.material and "Eye" in slot.material.name}

        if not eye_indices:
            return True

        orig_mode = bpy.context.mode
        if orig_mode != 'VERTEX_PAINT':
            Utils.ensure_object_mode()
            bpy.context.view_layer.objects.active = mesh
            bpy.ops.object.mode_set(mode='VERTEX_PAINT')

        for poly in mesh.data.polygons:
            if poly.material_index in eye_indices:
                for loop_idx in poly.loop_indices:
                    vc_layer.data[loop_idx].color = (0, 0, 0, 1)

        if orig_mode != 'VERTEX_PAINT':
            bpy.ops.object.mode_set(mode='OBJECT')
        return True
