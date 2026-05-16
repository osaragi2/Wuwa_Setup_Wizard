import random

import bpy

from .object_manager import ObjectManager

COLLECTION_COLORS = ['COLOR_01', 'COLOR_02', 'COLOR_03', 'COLOR_04',
                     'COLOR_05', 'COLOR_06', 'COLOR_07', 'COLOR_08']


# ========== COLLECTION MANAGER ==========

# Handles character collection organization
class CollectionManager:

    # ========== COLLECTION CREATION ==========

    # Creates a collection and moves mesh with all related objects into it
    @staticmethod
    def create_character_collection(mesh: bpy.types.Object, context: bpy.types.Context) -> str | None:
        cleaned_name_capitalized = ObjectManager._clean_mesh_name(
            mesh.name).capitalize()
        cleaned_name_original_case = ObjectManager._clean_mesh_name(mesh.name)

        new_coll = None

        if mesh.get("ww_collection_created") and mesh.users_collection:
            candidate = mesh.users_collection[0]
            if candidate != context.scene.collection and candidate.name != "Collection":
                new_coll = candidate

        if not new_coll:
            if cleaned_name_capitalized in bpy.data.collections:
                new_coll = bpy.data.collections[cleaned_name_capitalized]
            else:
                new_coll = bpy.data.collections.new(cleaned_name_capitalized)
                new_coll.color_tag = random.choice(COLLECTION_COLORS)
                context.scene.collection.children.link(new_coll)

        mesh["ww_collection_created"] = True

        objects_to_move = set()
        objects_to_move.add(mesh)

        rig_armature = ObjectManager.get_armature(mesh)
        if rig_armature:
            objects_to_move.add(rig_armature)

            if rig_armature.name.startswith("RIG-"):
                orig_armature_name = rig_armature.name.replace("RIG-", "")
                original_armature = bpy.data.objects.get(orig_armature_name)
                if original_armature:
                    objects_to_move.add(original_armature)

        helper_prefixes = ["Head Origin", "Light Direction",
                           "Head Forward", "Head Right",
                           "Head Controller", "Main Light"]
        for prefix in helper_prefixes:
            obj_name = f"{prefix} {cleaned_name_original_case}"
            obj_helper = bpy.data.objects.get(obj_name)
            if obj_helper:
                objects_to_move.add(obj_helper)

        if "face_panel_armature" in mesh:
            panel_armature = bpy.data.objects.get(mesh["face_panel_armature"])
            if panel_armature and panel_armature.users_collection:
                panel_collection = panel_armature.users_collection[0]
                for obj_panel in list(panel_collection.objects):
                    objects_to_move.add(obj_panel)

        for obj_to_move in objects_to_move:
            current_collections = [c for c in obj_to_move.users_collection]
            for coll in current_collections:
                if coll != new_coll:
                    coll.objects.unlink(obj_to_move)
            if obj_to_move.name not in new_coll.objects:
                new_coll.objects.link(obj_to_move)

        return new_coll.name
