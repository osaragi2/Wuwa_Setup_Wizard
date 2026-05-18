# Wuthering Waves Setup Wizard - Main Entry Point

import bpy
from bpy.props import StringProperty
from bpy.types import AddonPreferences

from .operators.amd_fix_ops import WW_OT_AMDMaterialFix
from .operators.camera_ops import WW_OT_SetSmartCamera
from .operators.collection_ops import (
    WW_OT_CreateCollection,
    WW_OT_PhysicalBoneArrangement,
)
from .operators.effect_ops import (
    WW_OT_AddTacetMark,
    WW_OT_AnimateTacetMark,
    WW_OT_ToggleOutlines,
    WW_OT_ToggleTwoColoredEyes,
)
from .operators.global_settings_ops import (
    WW_OT_ApplyGlobalSettings,
    WW_OT_ResetGlobalSettings,
)
from .operators.import_export import WW_OT_ImportModel, WW_OT_ImportTexture
from .operators.mesh_ops import WW_OT_Join
from .operators.misc_ops import WW_OT_PlanetShadowCatcher, WW_OT_ShaderSettings
from .operators.quick_setup import WW_OT_QuickSetup
from .operators.setup_ops import (
    WW_OT_SetDriver,
    WW_OT_SetupGeometryNodes,
    WW_OT_ToggleAnimationMode,
)
from .operators.shader_ops import WW_OT_ApplyShader
from .operators.texture_ops import WW_OT_TextureFormChange, WW_OT_TexturePipeline
from .rigging.face_panel_creator import WW_OT_CreateFacePanel
from .rigging.face_panel_importer import WW_OT_ImportFacePanel
from .rigging.rigify_operator import WW_OT_Rigify
from .ui.panel import WW_PT_ShaderPanel
from .ui.properties import WW_Properties

bl_info = {
    "name": "Wuthering Waves Setup Wizard",
    "author": "Wuwa Community",
    "version": (1, 0, 1),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Wuthering Waves",
    "description": "A toolkit to import and set up shaders, materials, and rigs for Wuthering Waves characters.",
    "category": "Wuthering Waves",
    "support": "COMMUNITY"
}


# Addon preferences for storing shader type and configuration
class WW_AddonPreferences(AddonPreferences):
    bl_idname = __name__

    last_shader_type: StringProperty(
        name="Last Shader Type",
        default='gathering_wives'
    )

    face_panel_file_path: StringProperty(
        name="Face Panel File Path",
        description="Persistent path to the face panel blend file",
        default="",
        subtype='FILE_PATH'
    )

    # Draws the preferences UI layout
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "last_shader_type")
        layout.prop(self, "face_panel_file_path")


classes = [
    WW_AddonPreferences,
    WW_Properties,
    WW_OT_QuickSetup,
    WW_OT_ImportModel,
    WW_OT_ApplyShader,
    WW_OT_ImportTexture,
    WW_OT_TexturePipeline,
    WW_OT_TextureFormChange,
    WW_OT_ShaderSettings,
    WW_OT_Rigify,
    WW_OT_CreateFacePanel,
    WW_OT_ImportFacePanel,
    WW_OT_SetDriver,
    WW_OT_ToggleAnimationMode,
    WW_OT_ToggleOutlines,
    WW_OT_ToggleTwoColoredEyes,
    WW_OT_AnimateTacetMark,
    WW_OT_AddTacetMark,
    WW_OT_Join,
    WW_OT_CreateCollection,
    WW_OT_SetupGeometryNodes,
    WW_OT_PhysicalBoneArrangement,
    WW_OT_PlanetShadowCatcher,
    WW_OT_SetSmartCamera,
    WW_OT_AMDMaterialFix,
    WW_OT_ApplyGlobalSettings,
    WW_OT_ResetGlobalSettings,
    WW_PT_ShaderPanel
]


# Restores shader type from preferences after file load
def _restore_shader_from_prefs():
    try:
        from .ui import properties
        prefs = bpy.context.preferences.addons.get(__name__)
        if prefs and hasattr(prefs.preferences, 'last_shader_type'):
            saved_type = prefs.preferences.last_shader_type
            if saved_type in ['wuthering_waves', 'gathering_wives'] and hasattr(bpy.context.scene, 'ww_properties'):
                properties._restoring_shader = True
                bpy.context.scene.ww_properties.shader_type = saved_type
                properties._restoring_shader = False
    except Exception:
        pass
    return None


# Handles file load event to restore preferences
@bpy.app.handlers.persistent
def _on_file_load(dummy):
    bpy.app.timers.register(_restore_shader_from_prefs, first_interval=0.1)


# Registers all addon classes, properties, and load handlers
def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ww_properties = bpy.props.PointerProperty(
        type=WW_Properties)
    bpy.app.handlers.load_post.append(_on_file_load)


# Unregisters all addon classes, properties, and load handlers
def unregister():
    if _on_file_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_file_load)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.ww_properties


if __name__ == "__main__":
    register()
