import bpy


# ========== BONE MANAGER ==========

# Handles bone collection organization for physical bones
class BoneManager:
    # Determines appropriate bone collection name based on bone name
    @staticmethod
    def _get_bone_collection_name(bone_name, is_rig_model=False):
        lower_name = bone_name.lower()

        if "skirt" in lower_name:
            return "Skirt"
        if "piao" in lower_name:
            return "Cloth"
        if "hair" in lower_name:
            return "Hair"
        if "chest" in lower_name:
            return "Chest"
        if "tail" in lower_name:
            return "Tail"

        if is_rig_model and lower_name.startswith("c_"):
            return "Body"

        return None

    # Assigns a bone to a specific bone collection
    @staticmethod
    def _assign_bone_to_collection(bone, collection, all_collections):
        for col in all_collections:
            if bone.name in col.bones:
                col.unassign(bone)
        collection.assign(bone)

    # Organizes physical bones (Hair, Skirt, etc) into collections
    @staticmethod
    def arrange_physical_bones(armature):
        data = armature.data
        bone_cols = data.collections

        is_rig_model = "rig" in armature.name.lower()
        created_collections = []

        if is_rig_model:
            collection_names_ordered = [
                "Body", "Skirt", "Cloth", "Hair", "Chest", "Tail", "Other"]
            default_collection_name = "Other"
            specific_collection_names = [
                "Body", "Skirt", "Cloth", "Hair", "Chest", "Tail"]
        else:
            collection_names_ordered = [
                "Body", "Skirt", "Cloth", "Hair", "Chest", "Tail"]
            default_collection_name = "Body"
            specific_collection_names = [
                "Skirt", "Cloth", "Hair", "Chest", "Tail"]

        for name in collection_names_ordered:
            if name not in bone_cols:
                bone_cols.new(name=name)
                created_collections.append(name)

        for i in range(len(collection_names_ordered)):
            name_to_move = collection_names_ordered[i]
            current_index = -1
            for j in range(len(bone_cols)):
                if bone_cols[j].name == name_to_move:
                    current_index = j
                    break

            if current_index != -1 and current_index != i:
                bone_cols.move(current_index, i)

        if default_collection_name in bone_cols:
            default_col = bone_cols[default_collection_name]
            for bone in data.bones:
                BoneManager._assign_bone_to_collection(
                    bone, default_col, bone_cols)

        organized_count = 0
        bones_by_collection = {name: [] for name in specific_collection_names}

        for bone in data.bones:
            collection_name = BoneManager._get_bone_collection_name(
                bone.name, is_rig_model=is_rig_model)
            if collection_name and collection_name in bones_by_collection:
                bones_by_collection[collection_name].append(bone)
                organized_count += 1

        for collection_name, bones in bones_by_collection.items():
            if bones:
                collection = bone_cols[collection_name]
                for bone in bones:
                    BoneManager._assign_bone_to_collection(
                        bone, collection, bone_cols)
            elif collection_name in created_collections and collection_name != "Body":
                bone_cols.remove(bone_cols[collection_name])

        for name in collection_names_ordered:
            if name in bone_cols:
                if name == "Body":
                    bone_cols[name].is_visible = True
                else:
                    bone_cols[name].is_visible = False

        armature.data.display_type = "STICK"
        return organized_count > 0
