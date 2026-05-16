import bpy
from bpy.props import (BoolProperty, EnumProperty, FloatProperty,
                       FloatVectorProperty, IntProperty, StringProperty)
from bpy.types import PropertyGroup


# ========== SHADER PERSISTENCE ==========

_restoring_shader = False
_save_timer_registered = False


# Saves user preferences after a short delay to avoid blocking the UI
def _deferred_save_prefs():
    global _save_timer_registered
    try:
        bpy.ops.wm.save_userpref()
    except Exception:
        pass
    _save_timer_registered = False
    return None


# Saves shader type to addon preferences when changed
def update_shader_type(self, context):
    global _restoring_shader, _save_timer_registered
    if _restoring_shader:
        return
    addon_name = '.'.join(__name__.split('.')[:-2])
    prefs = context.preferences.addons.get(addon_name)
    if prefs:
        prefs.preferences.last_shader_type = self.shader_type
        if not _save_timer_registered:
            bpy.app.timers.register(_deferred_save_prefs, first_interval=1.0)
            _save_timer_registered = True


# ========== GLOBAL SETTINGS UPDATE ==========

# Applies Expression settings (Face Blush, Face Shadow, Face Shadow Texture) when modified
def _update_expression(self, context):
    from ..core.global_settings_manager import GlobalSettingsManager
    from ..material.material_manager import MaterialManager

    mesh = context.active_object
    if not mesh or mesh.type != 'MESH' or not MaterialManager.has_ww_materials(mesh):
        return

    ww_props = context.scene.ww_properties
    GlobalSettingsManager.set_face_blush(mesh, ww_props.gs_face_blush)
    GlobalSettingsManager.set_face_shadow(mesh, ww_props.gs_face_shadow)
    GlobalSettingsManager.set_face_shadow_atlas(mesh, ww_props.gs_face_shadow_atlas)


# Applies Shadow settings (Shadow Offset, Shadow Smooth, Cast Shadows) when modified
def _update_shadow(self, context):
    from ..core.global_settings_manager import GlobalSettingsManager
    from ..material.material_manager import MaterialManager

    mesh = context.active_object
    if not mesh or mesh.type != 'MESH' or not MaterialManager.has_ww_materials(mesh):
        return

    ww_props = context.scene.ww_properties
    GlobalSettingsManager.set_shadow_offset(mesh, ww_props.gs_shadow_offset)
    GlobalSettingsManager.set_shadow_smooth(mesh, ww_props.gs_shadow_smooth)
    GlobalSettingsManager.set_cast_shadow(mesh, ww_props.gs_cast_shadow)


# Applies Skin Color settings (Skin Lit Color, Skin Shadow Color) when modified
def _update_skin_color(self, context):
    from ..core.global_settings_manager import GlobalSettingsManager
    from ..material.material_manager import MaterialManager

    mesh = context.active_object
    if not mesh or mesh.type != 'MESH' or not MaterialManager.has_ww_materials(mesh):
        return

    ww_props = context.scene.ww_properties
    GlobalSettingsManager.set_skin_lit_color(mesh, ww_props.gs_skin_lit_color)
    GlobalSettingsManager.set_skin_midtone_color(mesh, ww_props.gs_skin_midtone_color)
    GlobalSettingsManager.set_skin_shadow_color(mesh, ww_props.gs_skin_shadow_color)
    GlobalSettingsManager.set_skin_edge_color(mesh, ww_props.gs_skin_edge_color)


# ========== PROPERTIES ==========

# Main addon property group
class WW_Properties(PropertyGroup):
    shader_type: EnumProperty(
        name="Shader Type",
        description="Select shader to use for character setup",
        items=[
            ('wuthering_waves', "Wuthering Waves",
             "Legacy shader with Head Origin and Light Direction"),
            ('gathering_wives', "Gathering Wives",
             "New shader with Head Controller and Main Light")
        ],
        default='wuthering_waves',
        update=update_shader_type
    )
    face_panel_file_path: StringProperty(
        name="Face Panel File Path",
        description="Path to the face panel blend file",
        default="",
        subtype='FILE_PATH'
    )
    quick_setup_rigify: BoolProperty(
        name="Rigify Armature",
        description="Automatically run Rigify after setup",
        default=False
    )
    quick_setup_create_face: BoolProperty(
        name="Create Face Panel",
        description="Automatically create the face panel after setup",
        default=False
    )
    quick_setup_import_face: BoolProperty(
        name="Import Face Panel",
        description="Automatically import the face panel after setup",
        default=False
    )
    smart_camera_mode: EnumProperty(
        name="Smart Camera Mode",
        description="Current smart camera mode",
        items=[
            ('NONE', "None", "No mode selected"),
            ('M', "M", "Camera at z=1m"),
            ('MS', "MS", "Camera at z=1.2m"),
            ('S', "S", "Camera at z=1.3m"),
            ('XL', "XL", "Camera at z=1.4m"),
            ('XXL', "XXL", "Camera at z=1.8m")
        ],
        default='NONE'
    )
    show_character_setup: BoolProperty(name="Set Up Character", default=True)
    show_material_pipeline: BoolProperty(name="Material Pipeline", default=True)
    show_texture_pipeline: BoolProperty(name="Texture Pipeline", default=True)
    show_character_rig: BoolProperty(name="Character Rig", default=True)
    show_global_settings: BoolProperty(name="Global Settings", default=False)
    show_vfx: BoolProperty(name="Visual Effects", default=True)
    show_advanced_tools: BoolProperty(name="Advanced Tools", default=True)
    show_smart_camera: BoolProperty(name="Smart Camera System", default=True)
    show_amd_fix: BoolProperty(name="AMD Material Fix", default=False)
    tacet_mark_driver_expression: StringProperty(
        name="Driver Expression",
        description="The driver expression for the Tacet Mark animation",
        default="(frame - 1) / 23"
    )

    # ========== GLOBAL SETTINGS PROPERTIES ==========

    # Expression settings (applied to Face material only)
    gs_face_blush: FloatProperty(
        name="Face Blush",
        description="Controls the intensity of the face blush effect",
        min=0.0, max=1.0, default=0.0,
        update=_update_expression
    )
    gs_face_shadow: FloatProperty(
        name="Face Shadow",
        description="Controls the intensity of the face shadow overlay",
        min=0.0, max=1.0, default=0.0,
        update=_update_expression
    )
    gs_face_shadow_atlas: IntProperty(
        name="Face Shadow Atlas",
        description="Selects the face shadow atlas variant index",
        min=0, max=5, default=0,
        update=_update_expression
    )

    # Shadow settings (applied to all shader materials)
    gs_shadow_offset: FloatProperty(
        name="Shadow Offset",
        description="Offsets the shadow boundary position across all materials",
        min=-10000.0, max=10000.0, default=0.0,
        update=_update_shadow
    )
    gs_shadow_smooth: FloatProperty(
        name="Shadow Smooth",
        description="Controls the shadow edge smoothness across all materials",
        min=-10000.0, max=10000.0, default=15.0,
        update=_update_shadow
    )
    gs_cast_shadow: FloatProperty(
        name="Cast Shadows",
        description="Controls cast shadow intensity on Body Shader materials",
        min=0.0, max=1.0, default=0.0,
        update=_update_shadow
    )

    # Skin Color settings (applied to all materials except Bangs and Hair)
    gs_skin_lit_color: FloatVectorProperty(
        name="Skin Lit Color",
        description="Sets the lit skin color on all applicable materials",
        subtype='COLOR', size=4,
        min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0, 1.0),
        update=_update_skin_color
    )
    gs_skin_midtone_color: FloatVectorProperty(
        name="Skin Midtone Color",
        description="Sets the midtone skin color on all applicable materials",
        subtype='COLOR', size=4,
        min=0.0, max=1.0,
        default=(0.8, 0.48, 0.48, 1.0),
        update=_update_skin_color
    )
    gs_skin_shadow_color: FloatVectorProperty(
        name="Skin Shadow Color",
        description="Sets the shadow skin color on all applicable materials",
        subtype='COLOR', size=4,
        min=0.0, max=1.0,
        default=(0.4, 0.24, 0.24, 1.0),
        update=_update_skin_color
    )
    gs_skin_edge_color: FloatVectorProperty(
        name="Skin Edge Color",
        description="Sets the edge skin color on all applicable materials",
        subtype='COLOR', size=4,
        min=0.0, max=1.0,
        default=(1.0, 0.6, 0.6, 1.0),
        update=_update_skin_color
    )
