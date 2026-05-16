from math import radians

import bpy


# ========== CAMERA MANAGER ==========

# Handles smart camera positioning for character portraits
class CameraManager:

    # ========== CONSTANTS ==========

    Z_VALUES: dict[str, float] = {'M': 1.0, 'MS': 1.2, 'S': 1.3, 'XL': 1.4, 'XXL': 1.8}

    # ========== SMART CAMERA ==========

    # Creates or positions camera at preset height based on character mode
    @staticmethod
    def set_smart_camera(context: bpy.types.Context, mode: str) -> tuple[bool, str]:
        camera = context.scene.camera

        if not camera:
            camera = bpy.data.objects.new(
                "Camera", bpy.data.cameras.new("Camera"))
            context.collection.objects.link(camera)
            context.scene.camera = camera
            created = True
        else:
            created = False

        z = CameraManager.Z_VALUES.get(mode, 1.0)
        camera.location = (0, -1.5, z)
        camera.rotation_euler = (radians(90), 0, 0)

        context.scene.render.use_border = True
        context.scene.render.use_crop_to_border = True
        context.scene.render.fps = 60

        return created, mode
