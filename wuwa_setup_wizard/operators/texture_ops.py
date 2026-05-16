import bpy
from bpy.props import EnumProperty
from bpy.types import Operator

from ..core.object_manager import ObjectManager
from ..material.material_manager import MaterialManager
from ..texture.texture_processor import TextureProcessor


# ========== TEXTURE PIPELINE ==========

# Switches model textures between different states
class WW_OT_TexturePipeline(Operator):
    bl_idname = "ww.texture_pipeline"
    bl_label = "Texture Pipeline"
    bl_description = "Switch the model's textures between different states (Normal, Injured, Wet)"
    bl_options = {'REGISTER', 'UNDO'}

    pipeline_type: EnumProperty(
        name="Pipeline Type",
        items=[
            ('normal', "Normal", "Apply normal textures"),
            ('injured', "Injured", "Apply injured textures (Switch_D)"),
            ('wet', "Wet", "Apply wet textures (Switch02_D)")
        ]
    )

    # Applies the selected texture variant state to all mesh materials
    def execute(self, context):
        mesh = context.active_object
        if not mesh or mesh.type != 'MESH':
            self.report({'ERROR'}, "Please select a mesh object first")
            return {'CANCELLED'}

        if not MaterialManager.has_ww_materials(mesh):
            self.report({'ERROR'}, "Please apply Wuthering Waves shader first")
            return {'CANCELLED'}

        try:
            pipeline_names = {'normal': 'Normal',
                              'injured': 'Injured', 'wet': 'Wet'}
            availability = TextureProcessor.check_texture_availability(mesh)

            if not availability[self.pipeline_type]:
                self.report(
                    {'WARNING'}, f"{pipeline_names[self.pipeline_type]} textures not available for this mesh")
                return {'CANCELLED'}

            TextureProcessor.apply_texture_pipeline(mesh, self.pipeline_type)

            for region in context.area.regions:
                if region.type == 'UI':
                    region.tag_redraw()

            cleaned_name = ObjectManager._clean_mesh_name(mesh.name)
            self.report(
                {'INFO'}, f"Switched to {pipeline_names[self.pipeline_type]} textures for '{cleaned_name}'")

            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Texture pipeline error: {str(e)}")
            return {'CANCELLED'}


# ========== TEXTURE FORM ==========

# Cycles between texture form variants for multi-version textures
class WW_OT_TextureFormChange(Operator):
    bl_idname = "ww.texture_form_change"
    bl_label = "Change Texture Form"
    bl_description = "Cycle to the next texture form variant"
    bl_options = {'REGISTER', 'UNDO'}

    # Cycles to the next form variant and reports the result
    def execute(self, context):
        mesh = context.active_object
        if not mesh or mesh.type != 'MESH':
            self.report({'ERROR'}, "Please select a mesh object first")
            return {'CANCELLED'}

        if not MaterialManager.has_ww_materials(mesh):
            self.report({'ERROR'}, "Please apply Wuthering Waves shader first")
            return {'CANCELLED'}

        try:
            current, total = TextureProcessor.apply_texture_form_change(mesh)
            if total == 0:
                self.report({'WARNING'}, "No texture form variants available")
                return {'CANCELLED'}

            for region in context.area.regions:
                if region.type == 'UI':
                    region.tag_redraw()

            cleaned_name = ObjectManager._clean_mesh_name(mesh.name)
            self.report(
                {'INFO'}, f"Switched to form {current}/{total} for '{cleaned_name}'")

            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Texture form change error: {str(e)}")
            return {'CANCELLED'}
