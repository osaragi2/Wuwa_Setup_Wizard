import bpy
from bpy.types import Operator

from ..core.global_settings_manager import GlobalSettingsManager
from ..material.material_manager import MaterialManager


# ========== GLOBAL SETTINGS OPERATOR ==========

# Applies all Global Settings values to the active mesh's shader node groups
class WW_OT_ApplyGlobalSettings(Operator):
    bl_idname = "ww.apply_global_settings"
    bl_label = "Apply Global Settings"
    bl_description = "Applies Expression, Shadow, and Skin Color settings to all applicable shader materials."
    bl_options = {'REGISTER', 'UNDO'}

    # Requires active mesh with Wuthering Waves shader materials
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and MaterialManager.has_ww_materials(obj)

    # Reads property values and dispatches to GlobalSettingsManager
    def execute(self, context):
        mesh = context.active_object
        ww_props = context.scene.ww_properties

        try:
            # Expression
            GlobalSettingsManager.set_face_blush(mesh, ww_props.gs_face_blush)
            GlobalSettingsManager.set_face_shadow(mesh, ww_props.gs_face_shadow)
            GlobalSettingsManager.set_face_shadow_atlas(mesh, ww_props.gs_face_shadow_atlas)

            # Shadow
            GlobalSettingsManager.set_shadow_offset(mesh, ww_props.gs_shadow_offset)
            GlobalSettingsManager.set_shadow_smooth(mesh, ww_props.gs_shadow_smooth)
            GlobalSettingsManager.set_cast_shadow(mesh, ww_props.gs_cast_shadow)

            # Skin Color
            GlobalSettingsManager.set_skin_lit_color(mesh, ww_props.gs_skin_lit_color)
            GlobalSettingsManager.set_skin_midtone_color(mesh, ww_props.gs_skin_midtone_color)
            GlobalSettingsManager.set_skin_shadow_color(mesh, ww_props.gs_skin_shadow_color)
            GlobalSettingsManager.set_skin_edge_color(mesh, ww_props.gs_skin_edge_color)

            # GW Shadow
            GlobalSettingsManager.set_gw_shadow_position(mesh, ww_props.gs_gw_shadow_position)
            GlobalSettingsManager.set_gw_shadow_softness(mesh, ww_props.gs_gw_shadow_softness)
            GlobalSettingsManager.set_gw_cast_shadow(mesh, ww_props.gs_gw_cast_shadow)

            # GW Skin Color
            GlobalSettingsManager.set_gw_base_color(mesh, ww_props.gs_gw_base_color)
            GlobalSettingsManager.set_gw_shadow_color(mesh, ww_props.gs_gw_shadow_color)
            GlobalSettingsManager.set_gw_skin_color_multiplier(mesh, ww_props.gs_gw_skin_color_multiplier)

            self.report({'INFO'}, "Global Settings applied")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to apply Global Settings: {str(e)}")
            return {'CANCELLED'}


# ========== RESET GLOBAL SETTINGS ==========

# Resets all Global Settings to their default values and applies them to the active mesh
class WW_OT_ResetGlobalSettings(Operator):
    bl_idname = "ww.reset_global_settings"
    bl_label = "Reset Global Settings"
    bl_description = "Resets all Global Settings (Expression, Shadow, Skin Color) to their default values."
    bl_options = {'REGISTER', 'UNDO'}

    # Requires active mesh with Wuthering Waves shader materials
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and MaterialManager.has_ww_materials(obj)

    # Resets all properties to defaults and applies to active mesh
    def execute(self, context):
        ww_props = context.scene.ww_properties

        try:
            # Expression defaults
            ww_props.gs_face_blush = 0.0
            ww_props.gs_face_shadow = 0.0
            ww_props.gs_face_shadow_atlas = 0

            # Shadow defaults
            ww_props.gs_shadow_offset = 0.0
            ww_props.gs_shadow_smooth = 15.0
            ww_props.gs_cast_shadow = 0.0

            # Skin Color defaults
            ww_props.gs_skin_lit_color = (1.0, 1.0, 1.0, 1.0)
            ww_props.gs_skin_midtone_color = (0.8, 0.48, 0.48, 1.0)
            ww_props.gs_skin_shadow_color = (0.4, 0.24, 0.24, 1.0)
            ww_props.gs_skin_edge_color = (1.0, 0.6, 0.6, 1.0)

            # GW Shadow defaults
            ww_props.gs_gw_shadow_position = 0.5
            ww_props.gs_gw_shadow_softness = 0.075
            ww_props.gs_gw_cast_shadow = 0.0

            # GW Skin Color defaults
            ww_props.gs_gw_base_color = (1.0, 1.0, 1.0, 1.0)
            ww_props.gs_gw_shadow_color = (0.485, 0.490, 0.5, 1.0)
            ww_props.gs_gw_skin_color_multiplier = (1.0, 1.0, 1.0, 1.0)

            self.report({'INFO'}, "Global Settings reset to defaults")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to reset Global Settings: {str(e)}")
            return {'CANCELLED'}
