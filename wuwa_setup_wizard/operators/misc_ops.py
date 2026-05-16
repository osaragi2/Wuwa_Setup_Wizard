import bpy
from bpy.props import EnumProperty
from bpy.types import Operator

from ..core.scene_manager import SceneManager


# Returns available shader items for EnumProperty
def _get_shader_items(self, context):
    from ..addon_info import get_available_shaders
    available = get_available_shaders()
    items = []
    if available.get('wuthering_waves'):
        items.append(('wuthering_waves', "Wuthering Waves",
                     "Wuthering Waves shader with Head Origin, Light Direction"))
    if available.get('gathering_wives'):
        items.append(('gathering_wives', "Gathering Wives",
                     "Gathering Wives shader with Head Controller, Main Light"))
    if not items:
        items.append(('none', "No Shader Found", ""))
    return items


# ========== SHADER SETTINGS ==========

# Opens shader selection dialog
class WW_OT_ShaderSettings(Operator):
    bl_idname = "ww.shader_settings"
    bl_label = "Shader Settings"
    bl_description = "Select shader type."
    bl_options = {'REGISTER', 'INTERNAL'}

    shader_type: EnumProperty(
        name="Shader",
        description="Select which shader to use",
        items=_get_shader_items
    )

    # Opens shader selection dialog with current preference pre-selected
    def invoke(self, context, event):
        from ..addon_info import get_available_shaders
        available = get_available_shaders()
        saved_type = context.scene.ww_properties.shader_type

        if saved_type == 'wuthering_waves' and available.get('wuthering_waves'):
            self.shader_type = 'wuthering_waves'
        elif saved_type == 'gathering_wives' and available.get('gathering_wives'):
            self.shader_type = 'gathering_wives'
        elif available.get('wuthering_waves'):
            self.shader_type = 'wuthering_waves'
        elif available.get('gathering_wives'):
            self.shader_type = 'gathering_wives'
        else:
            self.shader_type = 'none'

        return context.window_manager.invoke_props_dialog(self, width=240)

    # Draws the shader type selector with shader credit display
    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.prop(self, "shader_type", text="")

        if self.shader_type == 'wuthering_waves':
            credit = layout.row()
            credit.alignment = 'CENTER'
            credit.label(text="Shader by Akatsuki", icon='FUND')
        elif self.shader_type == 'gathering_wives':
            credit = layout.row()
            credit.alignment = 'CENTER'
            credit.label(text="Shader by Jonn", icon='FUND')

    # Applies the selected shader type to scene properties
    def execute(self, context):
        if self.shader_type == 'none':
            self.report({'ERROR'}, "No shader files available")
            return {'CANCELLED'}

        context.scene.ww_properties.shader_type = self.shader_type
        shader_names = {
            'wuthering_waves': 'Wuthering Waves',
            'gathering_wives': 'Gathering Wives'
        }
        self.report(
            {'INFO'}, f"Shader set to: {shader_names.get(self.shader_type, self.shader_type)}")
        return {'FINISHED'}


# ========== SHADOW CATCHER ==========

# Creates shadow catcher plane and sun light
class WW_OT_PlanetShadowCatcher(Operator):
    bl_idname = "ww.planet_shadow_catcher"
    bl_label = "Planet Shadow Catcher"
    bl_description = "Adds a shadow catcher plane and sun light to the scene."
    bl_options = {"REGISTER", "UNDO"}

    # Creates or updates the planet shadow catcher plane and sun light
    def execute(self, context):
        try:
            if SceneManager.create_planet_shadow_catcher():
                self.report(
                    {'INFO'}, "Planet Shadow Catcher created successfully")
                return {'FINISHED'}
            else:
                self.report(
                    {'ERROR'}, "Failed to create Planet Shadow Catcher")
                return {'CANCELLED'}
        except Exception as e:
            self.report(
                {'ERROR'}, f"Failed to create Planet Shadow Catcher: {str(e)}")
            return {'CANCELLED'}
