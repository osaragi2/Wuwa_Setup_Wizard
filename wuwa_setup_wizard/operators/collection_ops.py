import bpy
from bpy.types import Operator

from ..core.collection_manager import CollectionManager
from ..core.object_manager import ObjectManager
from ..rigging.bone_manager import BoneManager


# ========== CHARACTER COLLECTION ==========

# Organizes model and related objects into a collection
class WW_OT_CreateCollection(Operator):
    bl_idname = "ww.create_collection"
    bl_label = "Create Character Collection"
    bl_description = "Automatically organizes the model and its related objects into a dedicated collection."
    bl_options = {"REGISTER", "UNDO"}

    # Requires at least one mesh with shader materials in the scene
    @classmethod
    def poll(cls, context):
        return len(ObjectManager.get_processable_meshes()) > 0

    # Creates collections for all processable meshes and their related objects
    def execute(self, context):
        try:
            meshes_to_process = ObjectManager.get_processable_meshes()
            if not meshes_to_process:
                self.report(
                    {'ERROR'}, "No processable meshes found - apply Wuthering Waves shader first")
                return {'CANCELLED'}

            created_collections = []
            failed_count = 0
            for mesh in meshes_to_process:
                try:
                    collection_name = CollectionManager.create_character_collection(
                        mesh, context)
                    created_collections.append(collection_name)
                except Exception:
                    failed_count += 1
                    continue

            if created_collections:
                if len(created_collections) == 1:
                    self.report(
                        {'INFO'}, f"Collection '{created_collections[0]}' created successfully")
                else:
                    msg = f"Created {len(created_collections)} character collections"
                    if failed_count > 0:
                        msg += f" ({failed_count} failed)"
                    self.report({'INFO'}, msg)
                return {'FINISHED'}
            self.report({'ERROR'}, "Failed to create any collections")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Collection creation error: {str(e)}")
            return {'CANCELLED'}


# ========== PHYSICAL BONE ARRANGEMENT ==========

# Organizes physical bones into collections
class WW_OT_PhysicalBoneArrangement(Operator):
    bl_idname = "ww.physical_bone_arrangement"
    bl_label = "Physical Bone Arrangement"
    bl_description = "Organizes physical bones (Hair, Skirt, etc.) into collections for easier management."
    bl_options = {"REGISTER", "UNDO"}

    # Requires armature that has not been rigified
    @classmethod
    def poll(cls, context):
        active_obj = context.active_object
        if not active_obj or active_obj.type not in {"MESH", "ARMATURE"}:
            return False
        armature = None
        if active_obj.type == "ARMATURE":
            armature = active_obj
        elif active_obj.type == "MESH":
            armature = next(
                (mod.object for mod in active_obj.modifiers if mod.type == "ARMATURE" and mod.object), None)
        if not armature:
            return False
        return not armature.name.startswith("RIG-")

    # Distributes armature bones into categorized collections by keyword
    def execute(self, context):
        try:
            armatures = []
            active_obj = context.active_object

            if active_obj.type == "ARMATURE":
                armatures.append(active_obj)
            elif active_obj.type == "MESH":
                for mod in active_obj.modifiers:
                    if mod.type == "ARMATURE" and mod.object:
                        armatures.append(mod.object)

            if not armatures:
                self.report({'ERROR'}, "No armature found")
                return {'CANCELLED'}

            organized_count = 0
            processed_armatures = []

            for armature in armatures:
                if armature.name.startswith("RIG-"):
                    continue
                if BoneManager.arrange_physical_bones(armature):
                    organized_count += 1
                    processed_armatures.append(armature)

            if organized_count > 0:
                if len(processed_armatures) == 1:
                    mesh = ObjectManager.get_mesh_from_armature(
                        processed_armatures[0])
                    if mesh:
                        cleaned_name = ObjectManager._clean_mesh_name(
                            mesh.name)
                        self.report(
                            {'INFO'}, f"Physical bones organized for '{cleaned_name}'")
                    else:
                        self.report(
                            {'INFO'}, "Physical bones organized successfully")
                else:
                    self.report(
                        {'INFO'}, f"Physical bones organized for {organized_count} armatures")
                return {'FINISHED'}
            self.report({'WARNING'}, "No physical bones found to organize")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Bone arrangement error: {str(e)}")
            return {'CANCELLED'}
