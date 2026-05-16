import bpy
from bpy.props import EnumProperty
from bpy.types import Operator

from ..core.camera_manager import CameraManager


# ========== SMART CAMERA ==========

# Moves camera to preset positions for character portrait shots
class WW_OT_SetSmartCamera(Operator):
    bl_idname = "ww.set_smart_camera"
    bl_label = "Set Smart Camera"
    bl_description = "Moves the camera to preset positions for character portrait shots."
    bl_options = {'REGISTER', 'UNDO'}

    mode: EnumProperty(
        name="Mode",
        description="Smart camera mode",
        items=[
            ('M', "M", "Camera at z=1m"),
            ('MS', "MS", "Camera at z=1.2m"),
            ('S', "S", "Camera at z=1.3m"),
            ('XL', "XL", "Camera at z=1.4m"),
            ('XXL', "XXL", "Camera at z=1.8m")
        ]
    )

    # Creates or repositions camera at the selected portrait mode height
    def execute(self, context):
        try:
            created, mode = CameraManager.set_smart_camera(context, self.mode)
            context.scene.ww_properties.smart_camera_mode = mode

            for region in context.area.regions:
                if region.type == 'UI':
                    region.tag_redraw()

            if created:
                self.report(
                    {'INFO'}, f"Camera created and positioned for mode '{mode}'")
            else:
                self.report({'INFO'}, f"Camera positioned for mode '{mode}'")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Smart camera setup failed: {str(e)}")
            return {'CANCELLED'}
