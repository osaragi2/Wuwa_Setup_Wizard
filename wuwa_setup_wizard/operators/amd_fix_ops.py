import bpy
from bpy.props import EnumProperty

from ..texture.texture_interpolation import TextureInterpolationManager


# ========== AMD FIX ==========

# Fixes AMD GPU viewport wireframe issue by changing texture interpolation
class WW_OT_AMDMaterialFix(bpy.types.Operator):
    bl_idname = "ww.amd_material_fix"
    bl_label = "AMD Material Fix"
    bl_description = "Fixes mesh appearing wireframe-like in viewport on AMD GPUs. Try Cubic mode to fix the issue."
    bl_options = {'REGISTER', 'UNDO'}

    mode: EnumProperty(
        name="Mode",
        items=[
            ('Linear', "Linear", "Set all textures to Linear interpolation"),
            ('Cubic', "Cubic", "Set all textures to Cubic interpolation")
        ],
        default='Cubic'
    )

    # Applies the selected interpolation mode to all texture nodes
    def execute(self, context):
        count = TextureInterpolationManager.set_interpolation_mode(self.mode)
        self.report({'INFO'}, f"Changed {count} textures to {self.mode}")
        return {'FINISHED'}
