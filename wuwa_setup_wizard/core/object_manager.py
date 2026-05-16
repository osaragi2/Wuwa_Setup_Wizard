import re
import time
import bpy

from .utils import Utils


# ========== CONSTANTS ==========

CACHE_CLEAR_INTERVAL = 1.0
CACHE_TTL = 5.0
MAX_CACHE_SIZE = 50
MAX_MESH_NAME_LENGTH = 12
HEAD_BONE_NAMES = ["Bip001Head", "c_head.x", "head", "頭"]
HELPER_PREFIXES = ["Head Origin", "Light Direction", "Head Forward", "Head Right"]


# ========== OBJECT MANAGER ==========

# Manages Blender objects and caching for Wuthering Waves shader addon
class ObjectManager:

    _cache = {"armature": {}, "head_bone": {}, "mesh_from_armature": {}}
    _last_cache_clear_time = 0

    # ========== NAME UTILITIES ==========

    # Cleans mesh name by removing file extensions and appends costume variant number
    @staticmethod
    def _clean_mesh_name(mesh_name: str) -> str:

        costume_suffix = ""
        md_match = re.search(r'Md(\d)', mesh_name, re.IGNORECASE)
        if md_match:
            variant_num = int(md_match.group(1))
            if variant_num >= 2:
                costume_suffix = str(variant_num)
            mesh_name = mesh_name[:md_match.start()]

        mesh_name = re.sub(r'R2T1|NHT1', '', mesh_name, flags=re.IGNORECASE)

        if len(mesh_name) > MAX_MESH_NAME_LENGTH:
            mesh_name = mesh_name[:MAX_MESH_NAME_LENGTH]

        mesh_name = mesh_name + costume_suffix

        return mesh_name

    # Validates if object reference is still valid
    @staticmethod
    def is_valid_object(obj) -> bool:
        try:
            _ = obj.name
            return obj.name in bpy.data.objects and bpy.data.objects[obj.name] == obj
        except (ReferenceError, AttributeError):
            return False

    # ========== CACHE MANAGEMENT ==========

    # Clears all cached object lookups
    @staticmethod
    def clear_cache() -> None:
        ObjectManager._cache = {"armature": {}, "head_bone": {}, "mesh_from_armature": {}}

    # Updates the view layer and reselects the active object
    @staticmethod
    def refresh_context() -> None:
        bpy.context.view_layer.update()
        if bpy.context.active_object and ObjectManager.is_valid_object(bpy.context.active_object):
            Utils.ensure_object_mode()
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.active_object.select_set(True)

    # Returns cached result or runs lookup_fn, with TTL expiry and LRU eviction
    @staticmethod
    def _get_cached_value(cache_key: str, obj_name: str, lookup_fn):
        current_time = time.monotonic()
        cache = ObjectManager._cache.get(cache_key, {})

        if obj_name in cache:
            cached_value, timestamp = cache[obj_name]
            if (current_time - timestamp) < CACHE_TTL:
                if cached_value is None:
                    return None
                try:
                    _ = cached_value.name
                    return cached_value
                except (ReferenceError, AttributeError, UnicodeDecodeError):
                    pass

        result = lookup_fn()

        if len(ObjectManager._cache[cache_key]) >= MAX_CACHE_SIZE:
            sorted_entries = sorted(
                ObjectManager._cache[cache_key].items(),
                key=lambda x: x[1][1]
            )
            ObjectManager._cache[cache_key] = dict(sorted_entries[MAX_CACHE_SIZE // 2:])

        ObjectManager._cache[cache_key][obj_name] = (result, current_time)
        return result

    # ========== ARMATURE AND BONE LOOKUPS ==========

    # Returns the head bone name from armature or None if not found
    @staticmethod
    def get_head_bone(armature) -> str | None:
        if not armature:
            return None

        try:
            armature_name = armature.name
        except (ReferenceError, AttributeError):
            return None

        current_time = time.monotonic()
        if armature_name in ObjectManager._cache["head_bone"]:
            cached_bone, timestamp = ObjectManager._cache["head_bone"][armature_name]
            if (current_time - timestamp) < CACHE_TTL:
                return cached_bone

        bone = next(
            (name for name in HEAD_BONE_NAMES if name in armature.pose.bones),
            None
        )

        ObjectManager._cache["head_bone"][armature_name] = (bone, current_time)
        return bone

    # Returns the armature associated with a mesh object
    @staticmethod
    def get_armature(mesh) -> bpy.types.Object | None:
        if not mesh:
            return None

        try:
            mesh_name = mesh.name
        except (ReferenceError, AttributeError):
            return None

        # Searches modifiers for the first armature reference
        def find_armature():
            return next(
                (m.object for m in mesh.modifiers if m.type == 'ARMATURE' and m.object),
                None
            )

        return ObjectManager._get_cached_value("armature", mesh_name, find_armature)

    # ========== MESH LOOKUPS ==========

    # Returns the main mesh (non-seethrough) associated with an armature
    @staticmethod
    def get_mesh_from_armature(armature) -> bpy.types.Object | None:
        if not armature:
            return None

        try:
            armature_name = armature.name
        except (ReferenceError, AttributeError):
            return None

        # Searches all mesh objects for one using this armature
        def find_mesh():
            for obj in bpy.data.objects:
                if obj.type != "MESH":
                    continue
                if ObjectManager.get_armature(obj) == armature:
                    return obj
            return None

        return ObjectManager._get_cached_value("mesh_from_armature", armature_name, find_mesh)

    # Finds the associated mesh from a helper object
    @staticmethod
    def get_mesh_from_helper_object(helper_obj) -> bpy.types.Object | None:
        from ..material.material_manager import MaterialManager

        for constraint in helper_obj.constraints:
            if constraint.type == 'CHILD_OF' and constraint.target:
                if constraint.target.type == 'ARMATURE':
                    return ObjectManager.get_mesh_from_armature(constraint.target)

        parts = helper_obj.name.split(" ", 2)
        if len(parts) >= 3:
            mesh_name = parts[-1]
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and mesh_name in obj.name:
                    if MaterialManager.has_ww_materials(obj):
                        return obj
        return None

    # Returns all mesh objects in the scene
    @staticmethod
    def get_mesh_list() -> list[bpy.types.Object]:
        return [obj for obj in bpy.data.objects if obj.type == 'MESH']

    # Returns meshes with Wuthering Waves materials that are not in Parts collections
    @staticmethod
    def get_processable_meshes() -> list[bpy.types.Object]:
        from ..material.material_manager import MaterialManager

        parts_collections = {
            coll for coll in bpy.data.collections if coll.name.endswith(" Parts")
        }
        objects_in_parts_colls = {
            obj for coll in parts_collections for obj in coll.objects
        }

        return [
            obj for obj in bpy.data.objects
            if obj.type == 'MESH'
            and MaterialManager.has_ww_materials(obj)
            and obj not in objects_in_parts_colls
        ]

    # ========== CLEANUP ==========

    # Removes default Light and Cube objects and purges orphans
    @staticmethod
    def cleanup() -> None:
        for name in ["Light", "Cube"]:
            obj = bpy.data.objects.get(name)
            if obj:
                bpy.data.objects.remove(obj, do_unlink=True)
        try:
            bpy.ops.outliner.orphans_purge()
        except RuntimeError:
            pass

    # Removes character assets by base name
    @staticmethod
    def cleanup_character_assets(base_name: str, exclude_objects: set = None) -> None:
        if exclude_objects is None:
            exclude_objects = set()

        objects_to_remove = ObjectManager._collect_objects_to_remove(base_name, exclude_objects)
        ObjectManager._remove_parts_collection(base_name, objects_to_remove, exclude_objects)
        ObjectManager._perform_cleanup(objects_to_remove, exclude_objects, base_name)

    # Finds matching mesh, armature, and helper objects for removal by base name
    @staticmethod
    def _collect_objects_to_remove(base_name: str, exclude_objects: set) -> set:
        objects_to_remove = set()
        base_name_cap = base_name.capitalize()

        for obj in bpy.data.objects:
            if obj in exclude_objects:
                continue

            cleaned_obj_name = ObjectManager._clean_mesh_name(obj.name).capitalize()

            if cleaned_obj_name == base_name_cap and obj.type == 'MESH':
                ObjectManager._add_mesh_and_related(obj, objects_to_remove)

            for prefix in HELPER_PREFIXES:
                if obj.name.startswith(f"{prefix} {ObjectManager._clean_mesh_name(base_name)}"):
                    objects_to_remove.add(obj)

        return objects_to_remove

    # Adds mesh, its armature, original armature, and face panel objects to removal set
    @staticmethod
    def _add_mesh_and_related(mesh_obj, objects_to_remove: set) -> None:
        objects_to_remove.add(mesh_obj)
        armature = ObjectManager.get_armature(mesh_obj)
        if armature:
            objects_to_remove.add(armature)
            if armature.name.startswith("RIG-"):
                orig_armature = bpy.data.objects.get(armature.name.replace("RIG-", ""))
                if orig_armature:
                    objects_to_remove.add(orig_armature)

        if "face_panel_armature" in mesh_obj:
            panel_armature = bpy.data.objects.get(mesh_obj["face_panel_armature"])
            if panel_armature and panel_armature.users_collection:
                panel_collection = panel_armature.users_collection[0]
                for panel_obj in list(panel_collection.objects):
                    objects_to_remove.add(panel_obj)

    # Adds all objects from the character's Parts collection to removal set
    @staticmethod
    def _remove_parts_collection(base_name: str, objects_to_remove: set, exclude_objects: set) -> None:
        parts_collection_name = f"{base_name.capitalize()} Parts"
        parts_collection = bpy.data.collections.get(parts_collection_name)
        if parts_collection:
            for obj in list(parts_collection.objects):
                objects_to_remove.add(obj)

    # Deletes collected objects, removes Parts collection, clears cache, and purges orphans
    @staticmethod
    def _perform_cleanup(objects_to_remove: set, exclude_objects: set, base_name: str) -> None:
        for obj in objects_to_remove:
            if obj in exclude_objects:
                continue
            try:
                bpy.data.objects.remove(obj, do_unlink=True)
            except ReferenceError:
                pass

        parts_collection_name = f"{base_name.capitalize()} Parts"
        parts_collection = bpy.data.collections.get(parts_collection_name)
        if parts_collection:
            try:
                bpy.data.collections.remove(parts_collection)
            except ReferenceError:
                pass

        ObjectManager.clear_cache()
        try:
            bpy.ops.outliner.orphans_purge()
        except RuntimeError:
            pass
