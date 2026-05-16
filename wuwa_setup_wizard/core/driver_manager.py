import bpy

from .helper_object_manager import HelperObjectManager
from .object_manager import ObjectManager


# ========== CONSTANTS ==========

FACE_PANEL_OFFSET = (0.1, 0.0, -0.1)


# ========== DRIVER MANAGER ==========

# Handles driver setup for helper objects and face panel
class DriverManager:

    # ========== MAIN DRIVER SETUP ==========

    # Sets up helper object drivers based on shader type
    @staticmethod
    def set_drivers(mesh) -> bool:
        cleaned_mesh_name = ObjectManager._clean_mesh_name(mesh.name)
        is_gw_shader = DriverManager._is_gathering_wives_shader(cleaned_mesh_name)

        if is_gw_shader:
            count = DriverManager._setup_gw_helpers(mesh)
        else:
            count = DriverManager._setup_ww_helpers(mesh)

        count += DriverManager._setup_face_panel(mesh)
        return count > 0

    # ========== SHADER DETECTION ==========

    # Checks if mesh uses Gathering Wives shader by helper object presence
    @staticmethod
    def _is_gathering_wives_shader(cleaned_mesh_name: str) -> bool:
        head_controller = bpy.data.objects.get(f"Head Controller {cleaned_mesh_name}")
        main_light = bpy.data.objects.get(f"Main Light {cleaned_mesh_name}")
        return bool(head_controller and main_light)

    # ========== HELPER SETUP ==========

    # Sets up Head Controller and Main Light helpers for Gathering Wives shader
    @staticmethod
    def _setup_gw_helpers(mesh: bpy.types.Object) -> int:
        count = 0
        count += int(HelperObjectManager.setup_head_controller(mesh))
        count += int(HelperObjectManager.setup_main_light(mesh))
        return count

    # Sets up Head Origin, Light Direction, and Head Forward/Right helpers for Wuthering Waves shader
    @staticmethod
    def _setup_ww_helpers(mesh: bpy.types.Object) -> int:
        count = 0
        count += int(HelperObjectManager.setup_head_origin(mesh))
        count += int(HelperObjectManager.setup_light_direction(mesh))
        count += int(HelperObjectManager.setup_head_forward(mesh))
        count += int(HelperObjectManager.setup_head_right(mesh))
        return count

    # ========== FACE PANEL ==========

    # Positions face panel relative to head bone
    @staticmethod
    def _setup_face_panel(mesh: bpy.types.Object) -> int:
        armature = ObjectManager.get_armature(mesh)
        if not armature:
            return 0

        if "face_panel_armature" not in mesh:
            return 0

        face_panel_obj = DriverManager._find_face_panel_object(armature)
        if not face_panel_obj:
            return 0

        return DriverManager._position_face_panel(face_panel_obj, armature)

    # Finds face panel object constrained to the armature
    @staticmethod
    def _find_face_panel_object(armature: bpy.types.Object) -> bpy.types.Object | None:
        for obj in bpy.data.objects:
            if not obj.name.startswith("Face Panel"):
                continue
            for c in obj.constraints:
                if c.type == 'CHILD_OF' and c.target == armature:
                    return obj
        return None

    # Positions face panel at head bone and sets inverse constraint
    @staticmethod
    def _position_face_panel(face_panel_obj: bpy.types.Object, armature: bpy.types.Object) -> int:
        try:
            head_bone_name = ObjectManager.get_head_bone(armature)
            if not head_bone_name or head_bone_name not in armature.data.bones:
                return 0

            head_pos = armature.data.bones[head_bone_name].head_local
            face_panel_obj.location = (
                head_pos.x + FACE_PANEL_OFFSET[0],
                FACE_PANEL_OFFSET[1],
                head_pos.z + FACE_PANEL_OFFSET[2]
            )

            constraint = DriverManager._get_face_panel_constraint(face_panel_obj, armature)
            if constraint:
                with bpy.context.temp_override(object=face_panel_obj, constraint=constraint):
                    bpy.ops.constraint.childof_set_inverse(constraint=constraint.name)
                return 1
        except (ReferenceError, RuntimeError):
            pass
        return 0

    # Returns the Child Of constraint targeting the armature
    @staticmethod
    def _get_face_panel_constraint(face_panel_obj: bpy.types.Object,
                                   armature: bpy.types.Object) -> bpy.types.Constraint | None:
        for c in face_panel_obj.constraints:
            if c.type == 'CHILD_OF' and c.target == armature:
                return c
        return None
