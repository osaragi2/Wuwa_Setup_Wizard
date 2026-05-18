import bpy

from .object_manager import ObjectManager


# ========== CONSTANTS ==========

HEAD_ORIGIN_OFFSET = (0, 0, 0.3)
LIGHT_DIRECTION_OFFSET = (0, 0, 0.3)
HEAD_CONTROLLER_OFFSET = (0, 0, 0)
MAIN_LIGHT_OFFSET = (0, 0, 0.3)
HEAD_FORWARD_POSITION = (0, -0.1, 1.75)
HEAD_RIGHT_POSITION = (-0.1, 0, 1.75)

HELPER_BASE_NAMES = [
    "Head Origin", "Light Direction",
    "Head Forward", "Head Right", "Head Controller", "Main Light"
]


# ========== HELPER OBJECT MANAGER ==========

# Manages helper objects for shader setup (Head Origin, Light Direction, etc.)
class HelperObjectManager:

    # ========== NAME FORMATTING ==========

    # Formats object name with mesh name suffix
    @staticmethod
    def format_object_name(mesh: bpy.types.Object, base_name: str) -> str:
        cleaned_mesh_name = ObjectManager._clean_mesh_name(mesh.name)
        return f"{base_name} {cleaned_mesh_name}"

    # ========== DUPLICATE MANAGEMENT ==========

    # Removes duplicate helper objects with .001, .002 suffixes
    @staticmethod
    def remove_duplicate_objs(base_name: str, mesh_name: str) -> None:
        import re
        cleaned_mesh_name = ObjectManager._clean_mesh_name(mesh_name)
        target_name = f"{base_name} {cleaned_mesh_name}"

        duplicates = []
        for obj in bpy.data.objects:
            if re.match(rf"^{re.escape(base_name)}\.\d+$", obj.name):
                duplicates.append(obj)
            elif re.match(rf"^{re.escape(target_name)}\.\d+$", obj.name):
                duplicates.append(obj)

        for obj in duplicates:
            try:
                bpy.data.objects.remove(obj, do_unlink=True)
            except (ReferenceError, RuntimeError):
                pass

    # Renames imported helper objects to include mesh name
    @staticmethod
    def rename_imported_objects(mesh_name: str, exclude_names: list[str] | None = None) -> None:
        if exclude_names is None:
            exclude_names = []

        cleaned_mesh_name = ObjectManager._clean_mesh_name(mesh_name)

        for base_name in HELPER_BASE_NAMES:
            target_name = f"{base_name} {cleaned_mesh_name}"
            HelperObjectManager.remove_duplicate_objs(base_name, mesh_name)

            found_obj = next(
                (obj for obj in bpy.data.objects
                 if obj.name == base_name and obj.name not in exclude_names),
                None
            )

            if found_obj and target_name not in bpy.data.objects:
                found_obj.name = target_name

    # ========== CONSTRAINT SETUP ==========

    # Sets up Child Of constraint for helper object
    @staticmethod
    def _setup_child_of_constraint(obj: bpy.types.Object, armature: bpy.types.Object, head_bone: str) -> None:
        for c in obj.constraints:
            if c.type == 'CHILD_OF':
                obj.constraints.remove(c)

        constraint = obj.constraints.new(type='CHILD_OF')
        constraint.target = armature
        constraint.subtarget = head_bone
        constraint.use_rotation_x = True
        constraint.use_rotation_y = True
        constraint.use_rotation_z = True

        with bpy.context.temp_override(object=obj, constraint=constraint):
            bpy.ops.constraint.childof_set_inverse(constraint=constraint.name)

    # ========== OBJECT SETUP ==========

    # Positions helper at head bone location with offset and adds Child Of constraint
    @staticmethod
    def setup_object(object_name: str, mesh: bpy.types.Object, offset: tuple[float, float, float] = (0, 0, 0)) -> bool:
        obj = bpy.data.objects.get(object_name)
        if not obj:
            return False

        try:
            armature = ObjectManager.get_armature(mesh)
            if not armature:
                return False

            head_bone = ObjectManager.get_head_bone(armature)
            if not head_bone:
                return False

            head = armature.pose.bones.get(head_bone)
            if head:
                loc = (armature.matrix_world @ head.matrix).to_translation()
                obj.location = (loc.x + offset[0], loc.y + offset[1], loc.z + offset[2])

            HelperObjectManager._setup_child_of_constraint(obj, armature, head_bone)
            return True
        except ReferenceError:
            ObjectManager.clear_cache()
            return False

    # ========== WUTHERING WAVES HELPER SETUP ==========

    # Sets up Head Origin helper object
    @staticmethod
    def setup_head_origin(mesh: bpy.types.Object) -> bool:
        object_name = HelperObjectManager.format_object_name(mesh, "Head Origin")
        return HelperObjectManager.setup_object(object_name, mesh, HEAD_ORIGIN_OFFSET)

    # Sets up Light Direction helper object
    @staticmethod
    def setup_light_direction(mesh: bpy.types.Object) -> bool:
        object_name = HelperObjectManager.format_object_name(mesh, "Light Direction")
        return HelperObjectManager.setup_object(object_name, mesh, LIGHT_DIRECTION_OFFSET)

    # Sets up Head Forward helper object (fixed position)
    @staticmethod
    def setup_head_forward(mesh: bpy.types.Object) -> bool:
        object_name = HelperObjectManager.format_object_name(mesh, "Head Forward")
        obj = bpy.data.objects.get(object_name)
        if not obj:
            return False
        obj.location = HEAD_FORWARD_POSITION
        obj.rotation_euler = (0, 0, 0)
        return True

    # Sets up Head Right helper object (fixed position)
    @staticmethod
    def setup_head_right(mesh: bpy.types.Object) -> bool:
        object_name = HelperObjectManager.format_object_name(mesh, "Head Right")
        obj = bpy.data.objects.get(object_name)
        if not obj:
            return False
        obj.location = HEAD_RIGHT_POSITION
        obj.rotation_euler = (0, 0, 0)
        return True

    # ========== GATHERING WIVES HELPER SETUP ==========

    # Sets up Head Controller helper object
    @staticmethod
    def setup_head_controller(mesh: bpy.types.Object) -> bool:
        object_name = HelperObjectManager.format_object_name(mesh, "Head Controller")
        return HelperObjectManager.setup_object(object_name, mesh, HEAD_CONTROLLER_OFFSET)

    # Sets up Main Light helper object
    @staticmethod
    def setup_main_light(mesh: bpy.types.Object) -> bool:
        object_name = HelperObjectManager.format_object_name(mesh, "Main Light")
        return HelperObjectManager.setup_object(object_name, mesh, MAIN_LIGHT_OFFSET)
