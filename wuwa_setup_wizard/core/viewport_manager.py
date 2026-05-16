import bpy

from .utils import Utils
from ..geometry.effect_manager import EffectManager


# ========== VIEWPORT MANAGER ==========

# Handles viewport mode switching and material preview
class ViewportManager:

    # ========== SOLID MODE ==========

    # Switches viewport to Solid mode and activates D texture nodes
    @staticmethod
    def set_solid_mode(context: bpy.types.Context, meshes: list[bpy.types.Object]) -> bool:
        if EffectManager.get_outlines_state():
            EffectManager.toggle_outlines(False)
        Utils.set_viewport('SOLID')
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.color_type = 'TEXTURE'
                        break
        material_processed = False
        for mesh in meshes:
            if not mesh.material_slots:
                continue
            for slot in mesh.material_slots:
                mat = slot.material
                if mat and mat.use_nodes and mat.node_tree:
                    d_node = next((node for node in mat.node_tree.nodes if node.type ==
                                  'TEX_IMAGE' and node.name == 'D'), None)
                    if d_node:
                        mat.node_tree.nodes.active = d_node
                        material_processed = True
        return material_processed
