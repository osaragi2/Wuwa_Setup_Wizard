from typing import Any

import bpy


# ========== UTILITIES ==========

# General utility functions for viewport, selection, and transform operations
class Utils:

    # ========== CONTEXT ==========

    # Ensures Blender is in OBJECT mode, returns the previous mode for restoration
    @staticmethod
    def ensure_object_mode() -> str:
        mode = bpy.context.mode
        if mode != 'OBJECT':
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except RuntimeError:
                pass
        return mode

    # ========== VIEWPORT ==========

    # Switches viewport shading mode (SOLID, RENDERED, etc)
    @staticmethod
    def set_viewport(mode: str) -> bool:
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = mode
                        return True
        return False

    # ========== SELECTION ==========

    # Deselects all objects and selects only the specified object, making it active
    @staticmethod
    def select_only(obj: bpy.types.Object) -> bool:
        try:
            if not obj or obj.name not in bpy.data.objects:
                return False

            if bpy.context.mode != 'OBJECT':
                try:
                    bpy.ops.object.mode_set(mode='OBJECT')
                except RuntimeError:
                    pass

            if bpy.context.view_layer.objects.active:
                bpy.context.view_layer.objects.active = None

            try:
                bpy.ops.object.select_all(action='DESELECT')
            except RuntimeError:
                for o in bpy.context.selected_objects:
                    try:
                        o.select_set(False)
                    except (ReferenceError, AttributeError):
                        pass

            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            return True

        except (ReferenceError, AttributeError, RuntimeError):
            return False

    # ========== TRANSFORM ==========

    # Caches current transform values and resets object to origin with identity transform
    @staticmethod
    def cache_and_reset_transform(obj: bpy.types.Object) -> dict[str, Any]:
        object_cache = {
            "location": obj.location.copy(),
            "rotation": obj.rotation_euler.copy(),
            "scale": obj.scale.copy()
        }

        pose_cache = {}
        if obj.type == 'ARMATURE':
            if obj.data.pose_position != 'POSE':
                obj.data.pose_position = 'POSE'

            for bone in obj.pose.bones:
                pose_cache[bone.name] = {
                    "location": bone.location.copy(),
                    "rotation_quaternion": bone.rotation_quaternion.copy(),
                    "scale": bone.scale.copy()
                }

                bone.location = (0, 0, 0)
                bone.rotation_quaternion = (1, 0, 0, 0)
                bone.scale = (1, 1, 1)

        obj.location = (0, 0, 0)
        obj.rotation_euler = (0, 0, 0)
        obj.scale = (1, 1, 1)

        bpy.context.view_layer.update()
        return {"object": object_cache, "pose": pose_cache}

    # Restores previously cached transform values to the object and its pose bones
    @staticmethod
    def restore_transform(obj: bpy.types.Object, cache: dict[str, Any]) -> None:
        if not obj or not cache:
            return

        if "pose" in cache and obj.type == 'ARMATURE':
            for bone_name, xform in cache["pose"].items():
                bone = obj.pose.bones.get(bone_name)
                if bone:
                    bone.location = xform["location"]
                    bone.rotation_quaternion = xform["rotation_quaternion"]
                    bone.scale = xform["scale"]

        if "object" in cache:
            obj.location = cache["object"]["location"]
            obj.rotation_euler = cache["object"]["rotation"]
            obj.scale = cache["object"]["scale"]

        bpy.context.view_layer.update()
