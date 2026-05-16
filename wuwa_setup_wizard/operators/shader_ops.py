import bpy
from bpy.types import Operator

from ..addon_info import get_shader_path
from ..core.object_manager import ObjectManager
from ..core.scene_manager import SceneManager
from ..material.material_manager import MaterialManager
from ..material.shader_importer import ShaderImporter


# ========== SHADER APPLICATION ==========

# Applies Wuthering Waves shader and material system to selected model
class WW_OT_ApplyShader(Operator):
    bl_idname = "ww.apply_shader"
    bl_label = "Apply Shader"
    bl_description = "Applies the Wuthering Waves shader and material system to the selected model."
    bl_options = {'REGISTER', 'UNDO'}

    # Imports the shader blend file and applies materials to the selected mesh
    def execute(self, context):
        mesh = context.active_object
        if not mesh or mesh.type != 'MESH':
            self.report({'ERROR'}, "Please select a mesh object first")
            return {'CANCELLED'}

        filepath = get_shader_path()

        if not filepath:
            self.report(
                {'ERROR'}, "Shader file not found. Set path in addon preferences")
            return {'CANCELLED'}

        if MaterialManager.has_ww_materials(mesh):
            cleaned_name = ObjectManager._clean_mesh_name(mesh.name)
            self.report(
                {'INFO'}, f"'{cleaned_name}' already has Wuthering Waves shader applied")
            return {'CANCELLED'}

        try:
            SceneManager.setup_scene_settings(context)
            shader_type = context.scene.ww_properties.shader_type
            if shader_type == 'gathering_wives':
                is_first = "[GW] Outlines" not in bpy.data.node_groups
            else:
                is_first = "[WW] Outlines" not in bpy.data.node_groups

            if ShaderImporter.import_shader(filepath, mesh, is_first):
                cleaned_name = ObjectManager._clean_mesh_name(mesh.name)
                self.report({'INFO'}, f"Shader applied to '{cleaned_name}'")
                bpy.ops.ww.import_texture('INVOKE_DEFAULT')
                return {'FINISHED'}
            self.report({'ERROR'}, "Shader import failed")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Shader application error: {str(e)}")
            return {'CANCELLED'}
