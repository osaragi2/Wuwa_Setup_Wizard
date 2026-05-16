import math
import traceback

import bmesh
import bpy
import mathutils

from ..core.object_manager import ObjectManager
from ..core.shape_key_manager import ShapeKeyManager
from .eye_tracker_utils import EyeTrackerUtils


# ========== FACE PANEL CREATOR ==========

# Builds facial expression control panel with bones and drivers
class WW_OT_CreateFacePanel(bpy.types.Operator):
    bl_idname = "ww.create_face_panel"
    bl_label = "Create Face Panel"
    bl_description = "Builds a new facial expression control panel directly into the character's rig."
    bl_options = {'REGISTER', 'UNDO'}

    # Requires mesh with armature and shape keys for facial expressions
    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        obj = context.active_object
        if obj.type == 'MESH':
            has_armature = any(
                mod.type == 'ARMATURE' and mod.object
                for mod in obj.modifiers)
            if has_armature:
                return True
        elif obj.type == 'ARMATURE':
            return True
        return bool(
            obj.name.startswith("Face Panel")
            or (obj.users_collection and any(
                "Face Panel" in c.name
                for c in obj.users_collection)))

    # Finds character armature from Face Panel object
    @staticmethod
    def get_armature_from_face_panel(obj):

        if obj.name.startswith("Face Panel"):
            if hasattr(obj, 'constraints'):
                for con in obj.constraints:
                    if (con.type == 'CHILD_OF'
                            and con.target
                            and con.target.type == 'ARMATURE'):
                        return con.target

        panel_armature = None
        if obj.users_collection:
            for coll in obj.users_collection:
                if "Face Panel" in coll.name:
                    for o in coll.objects:
                        if o.type == 'ARMATURE':
                            panel_armature = o
                            break
                    break

        if panel_armature:
            for mesh_obj in bpy.data.objects:
                if mesh_obj.type == 'MESH' and mesh_obj.get("face_panel_armature") == panel_armature.name:
                    return ObjectManager.get_armature(mesh_obj)

        for o in bpy.data.objects:
            if o.name.startswith("Face Panel"):
                if hasattr(o, 'constraints'):
                    for con in o.constraints:
                        if (con.type == 'CHILD_OF'
                                and con.target
                                and con.target.type == 'ARMATURE'):
                            return con.target

        return None

    SHAPE_KEYS_TO_SPLIT = [
        "E_Close", "E_Anger", "E_Sad", "E_Focus", "E_Insipid",
        "P_M_Scale_Add",
        "Pupil_L", "Pupil_R", "Pupil_Up", "Pupil_Down"]

    # Splits bilateral shapekeys into .L and .R versions
    @staticmethod
    def split_shape_keys(mesh_obj):
        EyeTrackerUtils.split_shape_keys(
            mesh_obj, WW_OT_CreateFacePanel.SHAPE_KEYS_TO_SPLIT)

    # Restores initial selection state after operations
    @staticmethod
    def _restore_state(initial_active, initial_selected, initial_mode):
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except RuntimeError:
            pass
        bpy.context.view_layer.objects.active = initial_active
        bpy.ops.object.select_all(action='DESELECT')
        for obj in initial_selected:
            if obj.name in bpy.data.objects:
                obj.select_set(True)
        if initial_mode == 'POSE':
            try:
                bpy.ops.object.mode_set(mode='POSE')
            except RuntimeError:
                pass

    # Sets up drivers connecting face panel to shape keys
    def setup_face_drivers(self, context, armature_obj, CharacterMesh):
        shape_key_mappings = {
            "Smile.L": {"shape_key": "E_Smile_L", "var_type": "LOC_Y"},
            "Smile.R": {"shape_key": "E_Smile_R", "var_type": "LOC_Y"},
            "Anger.L": {"shape_key": "E_Anger.L", "var_type": "LOC_Y"},
            "Sad.L": {"shape_key": "E_Sad.L", "var_type": "LOC_Y"},
            "Focus.L": {"shape_key": "E_Focus.L", "var_type": "LOC_Y"},
            "Insipid.L": {"shape_key": "E_Insipid.L", "var_type": "LOC_Y"},
            "Anger.R": {"shape_key": "E_Anger.R", "var_type": "LOC_Y"},
            "Sad.R": {"shape_key": "E_Sad.R", "var_type": "LOC_Y"},
            "Focus.R": {"shape_key": "E_Focus.R", "var_type": "LOC_Y"},
            "Insipid.R": {"shape_key": "E_Insipid.R", "var_type": "LOC_Y"},
            "B_Anger": {"shape_key": "B_Anger", "var_type": "LOC_Y"},
            "B_Happy": {"shape_key": "B_Happy", "var_type": "LOC_Y"},
            "B_Cheerful": {"shape_key": "B_Cheerful", "var_type": "LOC_Y"},
            "B_Sad": {"shape_key": "B_Sad", "var_type": "LOC_Y"},
            "B_Flat": {"shape_key": "B_Flat", "var_type": "LOC_Y"},
            "B_Inside_Add": {"shape_key": "B_Inside_Add", "var_type": "LOC_Y"},
            "EyeScale": {"shape_key": "E_Blephar", "var_type": "LOC_Y"}
        }

        mouth_mappings = {
            "Mouth.L": {
                "positive_shape": "M_Smile_L",
                "negative_shape": "M_Ennui_L",
                "limit": 0.0075,
                "var_type": "LOC_Y"
            },
            "Mouth.R": {
                "positive_shape": "M_Smile_R",
                "negative_shape": "M_Ennui_R",
                "limit": 0.0075,
                "var_type": "LOC_Y"
            }
        }

        mouth_x_mappings = {
            "Mouth.L": {
                "negative_shape": "P_M_Scale_Add.L",
                "positive_shape": "P_M_L_Add"
            },
            "Mouth.R": {
                "negative_shape": "P_M_R_Add",
                "positive_shape": "P_M_Scale_Add.R"
            }
        }

        for bone_name, mapping in shape_key_mappings.items():
            if bone_name not in armature_obj.pose.bones:
                continue
            bone = armature_obj.pose.bones[bone_name]
            if not CharacterMesh.data.shape_keys:
                continue
            shape_key = CharacterMesh.data.shape_keys.key_blocks.get(
                mapping["shape_key"])
            if not shape_key:
                continue
            driver = shape_key.driver_add('value').driver
            driver.type = 'SCRIPTED'
            var = driver.variables.new()
            var.name = 'bone_var'
            var.targets[0].id = armature_obj
            var.targets[0].data_path = (
                f'pose.bones["{bone.name}"].location.y' if mapping["var_type"] == "LOC_Y"
                else f'pose.bones["{bone.name}"].location.x'
            )
            driver.expression = "bone_var * 100" if bone_name == "EyeScale" else "bone_var * 50"

        for bone_name, mapping in mouth_mappings.items():
            if bone_name not in armature_obj.pose.bones:
                continue
            bone = armature_obj.pose.bones[bone_name]
            limit = mapping["limit"]
            if mapping["positive_shape"]:
                shape_key = CharacterMesh.data.shape_keys.key_blocks.get(
                    mapping["positive_shape"])
                if shape_key:
                    driver = shape_key.driver_add('value').driver
                    driver.type = 'SCRIPTED'
                    var = driver.variables.new()
                    var.name = 'mouth_y'
                    var.targets[0].id = armature_obj
                    var.targets[0].data_path = f'pose.bones["{bone.name}"].location.y'
                    driver.expression = f'max(min(mouth_y / {limit}, 1), 0)'
            if mapping["negative_shape"]:
                shape_key = CharacterMesh.data.shape_keys.key_blocks.get(
                    mapping["negative_shape"])
                if shape_key:
                    driver = shape_key.driver_add('value').driver
                    driver.type = 'SCRIPTED'
                    var = driver.variables.new()
                    var.name = 'mouth_y'
                    var.targets[0].id = armature_obj
                    var.targets[0].data_path = f'pose.bones["{bone.name}"].location.y'
                    driver.expression = f'max(min(-mouth_y / {limit}, 1), 0)'

        for bone_name, mapping in mouth_x_mappings.items():
            if bone_name not in armature_obj.pose.bones:
                continue
            bone = armature_obj.pose.bones[bone_name]
            x_data_path = f'pose.bones["{bone.name}"].location.x'
            pos_shape = CharacterMesh.data.shape_keys.key_blocks.get(
                mapping["positive_shape"])
            if pos_shape:
                driver = pos_shape.driver_add('value').driver
                driver.type = 'SCRIPTED'
                var = driver.variables.new()
                var.name = 'x_pos'
                var.targets[0].id = armature_obj
                var.targets[0].data_path = x_data_path
                driver.expression = 'max(min(x_pos / 0.0075, 1), 0)'
            neg_shape = CharacterMesh.data.shape_keys.key_blocks.get(
                mapping["negative_shape"])
            if neg_shape:
                driver = neg_shape.driver_add('value').driver
                driver.type = 'SCRIPTED'
                var = driver.variables.new()
                var.name = 'x_neg'
                var.targets[0].id = armature_obj
                var.targets[0].data_path = x_data_path
                driver.expression = 'max(min(-x_neg / 0.0075, 1), 0)'

        eye_scale_mappings = {
            "EyeTracker": "E_Close",
            "Eye.L": "E_Close.L",
            "Eye.R": "E_Close.R",
            "EyeScale": "Pupil_Scale",
        }

        for bone_name, shape_key_name in eye_scale_mappings.items():
            if bone_name not in armature_obj.pose.bones:
                continue
            shape_key = CharacterMesh.data.shape_keys.key_blocks.get(
                shape_key_name)
            if not shape_key:
                continue
            driver = shape_key.driver_add('value').driver
            driver.type = 'SCRIPTED'
            var = driver.variables.new()
            var.name = 'scaleval'
            var.targets[0].id = armature_obj
            if bone_name == "EyeScale":
                var.targets[0].data_path = f'pose.bones["{bone_name}"].scale.x'
                driver.expression = '(1 - scaleval) * 2'
            else:
                var.targets[0].data_path = f'pose.bones["{bone_name}"].scale.y'
                driver.expression = '(1 - scaleval) * 2'

        bone_name = "EyeTracker"
        shape_key_name = "E_Stare"
        if bone_name in armature_obj.pose.bones:
            shape_key = CharacterMesh.data.shape_keys.key_blocks.get(
                shape_key_name)
            if shape_key:
                driver = shape_key.driver_add('value').driver
                driver.type = 'SCRIPTED'
                var = driver.variables.new()
                var.name = 'yscale'
                var.targets[0].id = armature_obj
                var.targets[0].data_path = f'pose.bones["{bone_name}"].scale.y'
                driver.expression = 'max(min((yscale - 1) * 2, 1), 0)'

        EyeTrackerUtils.setup_pupil_drivers(
            armature_obj, CharacterMesh)

        vowel_shapes = {
            "E": {"axis": "x", "direction": -1, "max_value": 0.015},
            "I": {"axis": "x", "direction": 1, "max_value": 0.015},
            "A": {"axis": "y", "direction": 1, "max_value": 0.015},
            "U": {"axis": "y", "direction": -1, "max_value": 0.015},
        }

        mouth_bone = armature_obj.pose.bones.get("Mouth")
        if mouth_bone:
            for shape_key_name, info in vowel_shapes.items():
                shape_key = CharacterMesh.data.shape_keys.key_blocks.get(
                    shape_key_name)
                if not shape_key:
                    continue
                driver = shape_key.driver_add('value').driver
                driver.type = 'SCRIPTED'
                var_main = driver.variables.new()
                var_main.name = 'coord'
                var_main.targets[0].id = armature_obj
                var_main.targets[0].data_path = f'pose.bones["Mouth"].location.{info["axis"]}'
                var_o = driver.variables.new()
                var_o.name = 'oval'
                var_o.targets[0].id_type = 'KEY'
                var_o.targets[0].id = CharacterMesh.data.shape_keys
                var_o.targets[0].data_path = 'key_blocks["O"].value'
                if shape_key_name in ["E", "I"]:
                    var_y = driver.variables.new()
                    var_y.name = 'yval'
                    var_y.targets[0].id = armature_obj
                    var_y.targets[0].data_path = 'pose.bones["Mouth"].location.y'
                    driver.expression = (
                        f"(1 - oval * 0.6) * "
                        f"(1 - min(abs(yval) / 0.015, 1)) * "
                        f"max(min(({info['direction']} * coord) / {info['max_value']}, 1), 0)"
                    )
                else:
                    driver.expression = (
                        f"(1 - oval * 0.6) * "
                        f"max(min(({info['direction']} * coord) / {info['max_value']}, 1), 0)"
                    )

            o_shape = CharacterMesh.data.shape_keys.key_blocks.get("O")
            if o_shape:
                driver = o_shape.driver_add('value').driver
                driver.type = 'SCRIPTED'
                for axis in ["x", "y", "z"]:
                    var = driver.variables.new()
                    var.name = f"s_{axis}"
                    var.targets[0].id = armature_obj
                    var.targets[0].data_path = f'pose.bones["Mouth"].scale.{axis}'
                driver.expression = (
                    "max(min(((abs(s_x) + abs(s_y) + abs(s_z)) / 3 - 1) / 0.5, 1), 0)"
                )

        shape_map = {
            "M_OpenSmall": "M_OpenSmall",
            "M_Laugh": "M_Laugh",
            "M_Scared": "M_Scared",
            "M_ScaredTooth": "M_ScaredTooth",
            "M_Anger": "M_Anger",
            "M_Trapezoid": "M_Trapezoid",
            "M_Nutcracker": "M_Nutcracker",
            "Aa": "Aa",
            "M_A": "M_A",
            "M_O": "M_O",
        }

        for bone_name, shape_name in shape_map.items():
            shape_key = CharacterMesh.data.shape_keys.key_blocks.get(
                shape_name)
            if not shape_key:
                continue
            driver = shape_key.driver_add('value').driver
            driver.type = 'SCRIPTED'
            var = driver.variables.new()
            var.name = 'yval'
            var.targets[0].id = armature_obj
            var.targets[0].data_path = f'pose.bones["{bone_name}"].location.y'
            driver.expression = "max(min(yval / 0.015, 1), 0)"

        bone_name = "Eyebrows"
        y_mappings = {
            "B_Up_Add": {"direction": 1, "shape_key": "B_Up_Add"},
            "B_Down_Add": {"direction": -1, "shape_key": "B_Down_Add"},
        }

        for _, data in y_mappings.items():
            shape_key = CharacterMesh.data.shape_keys.key_blocks.get(
                data["shape_key"])
            if not shape_key:
                continue
            driver = shape_key.driver_add('value').driver
            driver.type = 'SCRIPTED'
            var = driver.variables.new()
            var.name = 'yval'
            var.targets[0].id = armature_obj
            var.targets[0].data_path = f'pose.bones["{bone_name}"].location.y'
            dir = data["direction"]
            driver.expression = f"max(min(({dir} * yval) / 0.01, 1), 0)"

        z_mappings = {
            "B_AH_L": {"direction": -1, "angle_deg": 10},
            "B_AH_R": {"direction": 1, "angle_deg": 10}
        }

        for key, info in z_mappings.items():
            shape_key = CharacterMesh.data.shape_keys.key_blocks.get(key)
            if not shape_key:
                continue
            driver = shape_key.driver_add('value').driver
            driver.type = 'SCRIPTED'
            var = driver.variables.new()
            var.name = 'zrot'
            var.targets[0].id = armature_obj
            var.targets[0].data_path = f'pose.bones["{bone_name}"].rotation_euler.z'
            max_radians = math.radians(info["angle_deg"])
            direction = info["direction"]
            driver.expression = f"max(min(({direction} * zrot) / {max_radians:.5f}, 1), 0)"

    # Creates outline mesh for face panel visualization
    def create_outline(self, name, verts_2d, collection):
        full_name = f"Custom{name}"
        if full_name in bpy.data.objects:
            return bpy.data.objects[full_name]
        mesh = bpy.data.meshes.new(full_name)
        obj = bpy.data.objects.new(full_name, mesh)
        collection.objects.link(obj)
        obj.hide_viewport = True
        obj.hide_render = True
        bm = bmesh.new()
        verts = []
        for x, y in verts_2d:
            verts.append(bm.verts.new((x, y, 0)))
        bm.verts.ensure_lookup_table()
        for i in range(len(verts)):
            bm.edges.new((verts[i], verts[(i + 1) % len(verts)]))
        bm.to_mesh(mesh)
        bm.free()
        return obj

    # Creates line geometry for face panel guides
    def create_lines(self, name, line_pairs, collection):
        full_name = f"Custom{name}"
        if full_name in bpy.data.objects:
            return bpy.data.objects[full_name]
        mesh = bpy.data.meshes.new(full_name)
        obj = bpy.data.objects.new(full_name, mesh)
        collection.objects.link(obj)
        obj.hide_viewport = True
        obj.hide_render = True
        bm = bmesh.new()
        for (x1, y1), (x2, y2) in line_pairs:
            v1 = bm.verts.new((x1, y1, 0))
            v2 = bm.verts.new((x2, y2, 0))
            bm.edges.new((v1, v2))
        bm.to_mesh(mesh)
        bm.free()
        return obj

    # Creates face panel bones, fan layout, shape key drivers, and constraints
    def execute(self, context):
        initial_active_object = context.active_object
        initial_selected_objects = context.selected_objects[:]
        initial_mode = context.mode
        obj = context.active_object

        if initial_mode == 'POSE':
            bpy.ops.object.mode_set(mode='OBJECT')

        armature_obj = None

        if obj.type == 'MESH':
            is_panel_mesh = (
                obj.name.startswith("Face Panel")
                or (obj.users_collection and any(
                    "Face Panel" in c.name
                    for c in obj.users_collection)))
            if is_panel_mesh:
                armature_obj = self.get_armature_from_face_panel(obj)
            else:
                armature_obj = ObjectManager.get_armature(obj)
        elif obj.type == 'ARMATURE':
            is_panel_armature = (
                obj.name.startswith("Face Panel")
                or (obj.users_collection and any(
                    "Face Panel" in c.name
                    for c in obj.users_collection))
            )
            if is_panel_armature:
                armature_obj = self.get_armature_from_face_panel(obj)
            else:
                armature_obj = obj
        else:
            armature_obj = self.get_armature_from_face_panel(obj)

        if not armature_obj:
            return {'CANCELLED'}

        CharacterMesh = ObjectManager.get_mesh_from_armature(armature_obj)

        if not CharacterMesh:
            return {'CANCELLED'}

        cleaned_name = ObjectManager._clean_mesh_name(CharacterMesh.name)

        try:
            if armature_obj.get('face_panel_created', False):
                if "FacePanelRoot" in armature_obj.data.bones:
                    self.split_shape_keys(CharacterMesh)
                    ShapeKeyManager.clear_shape_key_drivers(
                        CharacterMesh, ShapeKeyManager.protected_shape_keys)
                    self.setup_face_drivers(
                        context, armature_obj, CharacterMesh)

                    msg = (f"Face Panel drivers reset for '{cleaned_name}'")
                    self.report({'INFO'}, msg)
                    self._restore_state(
                        initial_active_object,
                        initial_selected_objects, initial_mode)
                    return {'FINISHED'}
                else:
                    del armature_obj['face_panel_created']

            if not armature_obj.get('face_panel_created', False):
                # Returns existing collection by name or creates a new hidden one
                def get_or_create_collection(name):
                    if name in bpy.data.collections:
                        return bpy.data.collections[name]
                    else:
                        coll = bpy.data.collections.new(name)
                        bpy.context.scene.collection.children.link(coll)
                        coll.hide_viewport = True
                        return coll

                custom_shapes_coll = get_or_create_collection("CustomShapes")
                bpy.context.view_layer.objects.active = armature_obj
                bpy.ops.object.mode_set(mode='EDIT')
                edit_bones = armature_obj.data.edit_bones
                eye_tracker_bone = edit_bones.get("EyeTracker")
                if not eye_tracker_bone:
                    meshes = EyeTrackerUtils.get_meshes_for_armature(
                        armature_obj)
                    eye_tracker_bone = (
                        EyeTrackerUtils.create_eye_tracker_bones(
                            armature_obj, edit_bones, meshes))
                    if not eye_tracker_bone:
                        raise Exception()
                eye_tracker_pos = eye_tracker_bone.head.copy()
                face_panel_root = edit_bones.new("FacePanelRoot")
                face_panel_root.head = eye_tracker_pos
                face_panel_root.tail = eye_tracker_pos + \
                    mathutils.Vector((0.0, 0.0, 0.02))
                face_panel_root.use_connect = False
                head_bone_name = ObjectManager.get_head_bone(
                    armature_obj)
                parent_bone = edit_bones.get(
                    head_bone_name) if head_bone_name else None
                if parent_bone:
                    face_panel_root.parent = parent_bone
                face_panel = edit_bones.new("FacePanel")
                face_panel.head = eye_tracker_pos
                face_panel.tail = eye_tracker_pos + \
                    mathutils.Vector((0.0, 0.0, 0.01))
                face_panel.use_connect = False
                face_panel.parent = face_panel_root
                eye_scale = edit_bones.new("EyeScale")
                eye_scale.head = face_panel.head - \
                    mathutils.Vector((0.0, 0.0, 0.01))
                eye_scale.tail = eye_scale.head + \
                    mathutils.Vector((0.0, 0.0, 0.01))
                eye_scale.use_connect = False
                eye_scale.parent = face_panel
                for bone_name in ["Eye.L", "Eye.R"]:
                    bone = edit_bones.get(bone_name)
                    if bone:
                        bone.parent = eye_tracker_bone
                eye_tracker_bone.parent = face_panel_root
                bpy.ops.object.mode_set(mode='OBJECT')
                pose_bones = armature_obj.pose.bones
                if "FacePanel" in pose_bones and "EyeTracker" in pose_bones:
                    face_panel_pose = pose_bones["FacePanel"]
                    constraint = face_panel_pose.constraints.new(
                        type='COPY_LOCATION')
                    constraint.name = "FollowEyeTracker"
                    constraint.target = armature_obj
                    constraint.subtarget = "EyeTracker"
                bpy.ops.object.mode_set(mode='EDIT')

                # Creates fan-arranged face control bones around a base bone position
                def create_fan_bones(base_bone_name, custom_bone_names, side_suffix):
                    base_bone = edit_bones.get(base_bone_name)
                    if not base_bone:
                        raise Exception()
                    fan_center = base_bone.head
                    radius = 0.035
                    bone_length = 0.02
                    num_bones = len(custom_bone_names)
                    arc_angle = math.radians(120)
                    angle_start = -arc_angle / 2
                    for i in range(num_bones):
                        angle = angle_start + i * (arc_angle / (num_bones - 1))
                        direction_multiplier = -1 if side_suffix == ".R" else 1
                        head_x = math.cos(angle) * radius * \
                            direction_multiplier
                        head_z = math.sin(angle) * radius
                        head = fan_center + \
                            mathutils.Vector((head_x, 0, head_z))
                        tail = head + \
                            (head - fan_center).normalized() * bone_length
                        bone_name = custom_bone_names[i].replace(
                            ".L", side_suffix)
                        fan_bone = edit_bones.new(bone_name)
                        fan_bone.head = head
                        fan_bone.tail = tail
                        fan_bone.parent = edit_bones["FacePanel"]
                        fan_bone.use_connect = False

                # Sets custom roll angles for facial expression bones on both sides
                def adjust_bone_roll():
                    bone_rolls = {
                        "Smile.L": 30,
                        "Anger.L": 60,
                        "Sad.L": 90,
                        "Focus.L": 120,
                        "Insipid.L": 150,
                    }
                    for bone_name, roll_deg in bone_rolls.items():
                        bone = edit_bones.get(bone_name)
                        if bone:
                            bone.roll = math.radians(roll_deg)
                        bone_R = edit_bones.get(bone_name.replace(".L", ".R"))
                        if bone_R:
                            bone_R.roll = -math.radians(roll_deg)

                custom_bone_names_L = ["Insipid.L",
                                       "Focus.L", "Sad.L", "Anger.L", "Smile.L"]
                custom_bone_names_R = [name.replace(
                    ".L", ".R") for name in custom_bone_names_L]
                create_fan_bones("Eye.L", custom_bone_names_L, ".L")
                create_fan_bones("Eye.R", custom_bone_names_R, ".R")
                adjust_bone_roll()
                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.mode_set(mode='EDIT')
                edit_bones = bpy.context.object.data.edit_bones
                face_panel = edit_bones.get("FacePanel")
                if not face_panel:
                    raise Exception()
                eyebrows_bone = edit_bones.new("Eyebrows")
                eyebrows_head = face_panel.head + \
                    mathutils.Vector((0, 0, 0.05))
                eyebrows_bone.head = eyebrows_head
                eyebrows_bone.tail = eyebrows_head + \
                    mathutils.Vector((0, 0, 0.01))
                eyebrows_bone.parent = face_panel
                eyebrows_bone.use_connect = False
                b_names = ["B_Anger", "B_Happy", "B_Cheerful",
                           "B_Sad", "B_Flat", "B_Inside_Add"]
                spacing = 0.015
                start_x = -spacing * (len(b_names) - 1) / 2
                y = eyebrows_head.y
                z = eyebrows_bone.tail.z
                for i, name in enumerate(b_names):
                    b = edit_bones.new(name)
                    head = mathutils.Vector((start_x + i * spacing, y, z))
                    tail = head + mathutils.Vector((0, 0, 0.02))
                    b.head = head
                    b.tail = tail
                    b.parent = eyebrows_bone
                    b.use_connect = False
                mouth_panel_bone = edit_bones.new("MouthPanel")
                mouth_panel_head = face_panel.head - \
                    mathutils.Vector((0, 0, 0.04))
                mouth_panel_bone.head = mouth_panel_head
                mouth_panel_bone.tail = mouth_panel_head + \
                    mathutils.Vector((0, 0, 0.01))
                mouth_panel_bone.parent = face_panel
                mouth_panel_bone.use_connect = False
                mouth_bone = edit_bones.new("Mouth")
                mouth_bone.head = mouth_panel_head
                mouth_bone.tail = mouth_bone.head + \
                    mathutils.Vector((0, 0, 0.02))
                mouth_bone.parent = mouth_panel_bone
                mouth_bone.use_connect = False
                offset_x = 0.034
                y = mouth_bone.head.y
                z = mouth_bone.head.z
                length = 0.02
                for side in [("Mouth.L", offset_x), ("Mouth.R", -offset_x)]:
                    name, x_offset = side
                    b = edit_bones.new(name)
                    head = mathutils.Vector(
                        (mouth_bone.head.x + x_offset, y, z))
                    tail = head + mathutils.Vector((0, 0, length))
                    b.head = head
                    b.tail = tail
                    b.parent = mouth_panel_bone
                    b.use_connect = False
                expressions = ["Aa", "M_OpenSmall", "M_Laugh", "M_Scared",
                               "M_ScaredTooth", "M_Anger", "M_Trapezoid", "M_Nutcracker", "M_O", "M_A"]
                num = len(expressions)
                spacing = 0.0075
                total_width = (num - 1) * spacing
                start_x = mouth_panel_head.x - total_width / 2
                y = mouth_panel_head.y
                z = mouth_panel_head.z - 0.025
                for i, name in enumerate(expressions):
                    b = edit_bones.new(name)
                    head = mathutils.Vector((start_x + i * spacing, y, z))
                    tail = head - mathutils.Vector((0, 0, 0.02))
                    b.head = head
                    b.tail = tail
                    b.parent = mouth_panel_bone
                    b.use_connect = False
                bpy.ops.object.mode_set(mode='OBJECT')

                triangle_points = [(0, 1), (-1, -1), (1, -1)]
                diamond_points = [(0, 1), (-1, 0), (0, -1), (1, 0)]
                square_points = [(-1, 1), (1, 1), (1, -1), (-1, -1)]
                plus_cross_lines = [[(-1, 0), (1, 0)], [(0, -1), (0, 1)]]

                self.create_outline(
                    "Triangle", triangle_points, custom_shapes_coll)
                self.create_outline(
                    "Diamond", diamond_points, custom_shapes_coll)
                self.create_outline(
                    "Square", square_points, custom_shapes_coll)
                self.create_lines(
                    "Cross", plus_cross_lines, custom_shapes_coll)

                EyeTrackerUtils.create_capsule_widget(
                    "WGT-rig_eyes", custom_shapes_coll)
                EyeTrackerUtils.create_circle_widget(
                    "WGT-rig_eye.L", custom_shapes_coll)
                EyeTrackerUtils.create_circle_widget(
                    "WGT-rig_eye.R", custom_shapes_coll)

                bpy.ops.object.mode_set(mode='POSE')
                bone_shape_map = {
                    "EyeTracker": "WGT-rig_eyes",
                    "Eye.L": "WGT-rig_eye.L",
                    "Eye.R": "WGT-rig_eye.R",
                    "Eyebrows": "CustomSquare",
                    "Mouth": "WGT-rig_eyes",
                    "Mouth.L": "CustomDiamond",
                    "Mouth.R": "CustomDiamond",
                    "Smile.L": "CustomTriangle",
                    "Anger.L": "CustomTriangle",
                    "Sad.L": "CustomTriangle",
                    "Focus.L": "CustomTriangle",
                    "Insipid.L": "CustomTriangle",
                    "Smile.R": "CustomTriangle",
                    "Anger.R": "CustomTriangle",
                    "Sad.R": "CustomTriangle",
                    "Focus.R": "CustomTriangle",
                    "Insipid.R": "CustomTriangle",
                    "B_Anger": "CustomTriangle",
                    "B_Happy": "CustomTriangle",
                    "B_Cheerful": "CustomTriangle",
                    "B_Sad": "CustomTriangle",
                    "B_Flat": "CustomTriangle",
                    "B_Inside_Add": "CustomTriangle",
                    "M_OpenSmall": "CustomTriangle",
                    "M_Laugh": "CustomTriangle",
                    "M_Scared": "CustomTriangle",
                    "M_ScaredTooth": "CustomTriangle",
                    "M_Anger": "CustomTriangle",
                    "M_Trapezoid": "CustomTriangle",
                    "M_Nutcracker": "CustomTriangle",
                    "MouthPanel": "CustomCross",
                    "EyeScale": "CustomSquare",
                    "Aa": "CustomTriangle",
                    "M_A": "CustomTriangle",
                    "M_O": "CustomTriangle",
                }

                for bone_name, shape_name in bone_shape_map.items():
                    pbone = armature_obj.pose.bones.get(bone_name)
                    shape_obj = bpy.data.objects.get(shape_name)
                    if not pbone or not shape_obj:
                        continue
                    pbone.custom_shape = shape_obj
                    if bone_name in {"EyeTracker", "Eye.L", "Eye.R"}:
                        pbone.custom_shape_scale_xyz = (4.0, 4.0, 4.0)
                    elif bone_name == "EyeScale":
                        pbone.custom_shape_scale_xyz = (1.0, 0.1, 1.0)
                    elif shape_name == "CustomTriangle":
                        if bone_name.startswith(("Aa", "M_")):
                            pbone.custom_shape_scale_xyz = (0.15, 0.15, 1.0)
                        else:
                            pbone.custom_shape_scale_xyz = (0.2, 0.2, 1.0)
                    elif shape_name == "CustomSquare":
                        pbone.custom_shape_scale_xyz = (4.5, 0.2, 1.0)
                    elif shape_name == "CustomDiamond":
                        if bone_name in ["Mouth.L", "Mouth.R"]:
                            pbone.custom_shape_scale_xyz = (0.2, 0.2, 1.0)
                        else:
                            pbone.custom_shape_scale_xyz = (0.5, 0.5, 1.0)
                    elif shape_name == "WGT-rig_eyes":
                        pbone.custom_shape_scale_xyz = (1.5, 1.5, 0.75)
                    elif shape_name == "CustomCross":
                        pbone.custom_shape_scale_xyz = (3.0, 1.875, 0.75)

                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.mode_set(mode='POSE')
                eye_bones = {"EyeTracker", "Eye.L", "Eye.R"}
                for pbone in armature_obj.pose.bones:
                    if pbone.name in eye_bones:
                        has_limit_scale = any(
                            c.type == 'LIMIT_SCALE'
                            for c in pbone.constraints)
                        if not has_limit_scale:
                            pbone.lock_location = (False, False, True)
                            pbone.lock_rotation = (True, True, True)
                            pbone.lock_rotations_4d = True
                            pbone.lock_scale = (True, False, True)
                            con = pbone.constraints.new(
                                type='LIMIT_SCALE')
                            con.use_min_x = True
                            con.use_max_x = True
                            con.min_x = 1.0
                            con.max_x = 1.0
                            con.use_min_y = True
                            con.use_max_y = True
                            con.owner_space = 'LOCAL'
                            con.use_transform_limit = True
                            con_loc = pbone.constraints.new(
                                type='LIMIT_LOCATION')
                            con_loc.use_min_x = True
                            con_loc.use_max_x = True
                            con_loc.use_min_y = True
                            con_loc.use_max_y = True
                            con_loc.owner_space = 'LOCAL'
                            con_loc.use_transform_limit = True
                            if pbone.name == "EyeTracker":
                                con_loc.min_x = -0.1
                                con_loc.max_x = 0.1
                                con_loc.min_y = -0.1
                                con_loc.max_y = 0.1
                                con.min_y = 0.5
                                con.max_y = 1.5
                            else:
                                con_loc.min_x = -0.05
                                con_loc.max_x = 0.05
                                con_loc.min_y = -0.05
                                con_loc.max_y = 0.05
                                con.min_y = 0.5
                                con.max_y = 1.0
                        continue
                    shape = pbone.custom_shape
                    pbone.lock_location = (False, False, False)
                    pbone.lock_rotation = (False, False, False)
                    pbone.lock_scale = (False, False, False)
                    for con in list(pbone.constraints):
                        if con.type in {'LIMIT_LOCATION', 'LIMIT_ROTATION', 'LIMIT_SCALE'}:
                            pbone.constraints.remove(con)
                    shape_name = shape.name if shape else ""
                    if shape_name == "CustomTriangle":
                        pbone.lock_location = (True, False, True)
                        pbone.lock_rotation = (True, True, True)
                        pbone.lock_scale = (True, True, True)
                        con = pbone.constraints.new(type='LIMIT_LOCATION')
                        con.use_min_y = True
                        con.use_max_y = True
                        con.min_y = 0.0
                        con.max_y = 0.015 if pbone.name.startswith(("Aa", "M_")) else 0.02
                        con.owner_space = 'LOCAL'
                        con.use_transform_limit = True
                    elif pbone.name == "EyeScale":
                        pbone.lock_location = (True, False, True)
                        pbone.lock_rotation = (True, True, True)
                        pbone.lock_scale = (False, True, True)
                        con_loc = pbone.constraints.new(type='LIMIT_LOCATION')
                        con_loc.use_min_y = con_loc.use_max_y = True
                        con_loc.min_y = 0.0
                        con_loc.max_y = 0.01
                        con_loc.owner_space = 'LOCAL'
                        con_loc.use_transform_limit = True
                        con_scale = pbone.constraints.new(type='LIMIT_SCALE')
                        con_scale.use_min_x = con_scale.use_max_x = True
                        con_scale.min_x = 0.5
                        con_scale.max_x = 1
                        con_scale.owner_space = 'LOCAL'
                        con_scale.use_transform_limit = True
                    elif shape_name == "CustomSquare":
                        pbone.lock_location = (True, False, True)
                        pbone.lock_rotation = (True, True, False)
                        pbone.lock_scale = (True, True, True)
                        pbone.rotation_mode = 'XYZ'
                        con_loc = pbone.constraints.new(type='LIMIT_LOCATION')
                        con_loc.use_min_y = True
                        con_loc.use_max_y = True
                        con_loc.min_y = -0.01
                        con_loc.max_y = 0.01
                        con_loc.owner_space = 'LOCAL'
                        con_loc.use_transform_limit = True
                        con_rot = pbone.constraints.new(type='LIMIT_ROTATION')
                        con_rot.use_limit_z = True
                        con_rot.min_z = -math.radians(10)
                        con_rot.max_z = math.radians(10)
                        con_rot.owner_space = 'LOCAL'
                        con_rot.use_transform_limit = True
                    elif pbone.name == "Mouth":
                        pbone.lock_location = (False, False, True)
                        pbone.lock_rotation = (True, True, True)
                        con = pbone.constraints.new(type='LIMIT_LOCATION')
                        con.use_min_x = con.use_max_x = True
                        con.use_min_y = con.use_max_y = True
                        con.min_x = -0.015
                        con.max_x = 0.015
                        con.min_y = -0.015
                        con.max_y = 0.015
                        con.owner_space = 'LOCAL'
                        con.use_transform_limit = True
                        con_scale = pbone.constraints.new(type='LIMIT_SCALE')
                        con_scale.use_min_x = con_scale.use_max_x = True
                        con_scale.use_min_y = con_scale.use_max_y = True
                        con_scale.use_min_z = con_scale.use_max_z = True
                        con_scale.min_x = con_scale.min_y = con_scale.min_z = 1.0
                        con_scale.max_x = con_scale.max_y = con_scale.max_z = 1.5
                        con_scale.owner_space = 'LOCAL'
                        con_scale.use_transform_limit = True
                    elif pbone.name in {"Mouth.L", "Mouth.R"}:
                        pbone.lock_location = (False, False, True)
                        pbone.lock_rotation = (True, True, True)
                        pbone.lock_scale = (True, True, True)
                        con = pbone.constraints.new(type='LIMIT_LOCATION')
                        con.use_min_x = con.use_max_x = True
                        con.use_min_y = con.use_max_y = True
                        con.min_x = -0.0075
                        con.max_x = 0.0075
                        con.min_y = -0.0075
                        con.max_y = 0.0075
                        con.owner_space = 'LOCAL'
                        con.use_transform_limit = True

                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.select_all(action='DESELECT')
                self.split_shape_keys(CharacterMesh)

                bpy.context.view_layer.objects.active = armature_obj
                armature_obj.select_set(True)
                ShapeKeyManager.clear_shape_key_drivers(
                    CharacterMesh, ShapeKeyManager.protected_shape_keys)
                self.setup_face_drivers(
                    context, armature_obj, CharacterMesh)

                bpy.ops.object.mode_set(mode='POSE')
                if 'Face Panel' not in armature_obj.data.collections:
                    armature_obj.data.collections.new(name='Face Panel')
                    # Reposition: move "Face Panel" before "Root" if Rigify layout exists
                    collections = armature_obj.data.collections
                    fp_idx = collections.find('Face Panel')
                    root_idx = collections.find('Root')
                    if root_idx >= 0 and fp_idx > root_idx:
                        collections.move(fp_idx, root_idx)
                theme_bones = {
                    "THEME01": [
                        "MouthPanel", "Mouth", "Eyebrows",
                        "B_Anger", "B_Happy", "B_Cheerful", "B_Sad", "B_Flat", "B_Inside_Add"
                    ],
                    "THEME09": [
                        "EyeTracker", "EyeScale", "Eye.L", "Eye.R",
                        "Smile.L", "Anger.L", "Sad.L", "Focus.L", "Insipid.L",
                        "Smile.R", "Anger.R", "Sad.R", "Focus.R", "Insipid.R"
                    ],
                    "THEME03": [
                        "Mouth.R", "Mouth.L", "M_OpenSmall", "M_Laugh",
                        "M_Scared", "M_ScaredTooth", "M_Anger", "M_Trapezoid", "M_Nutcracker", "Aa", "M_A", "M_O"
                    ],
                }
                for theme_name, bone_names in theme_bones.items():
                    for bone_name in bone_names:
                        pbone = armature_obj.pose.bones.get(bone_name)
                        if pbone:
                            pbone.color.palette = theme_name
                            pbone.bone.select = True
                facepanel_index = armature_obj.data.collections.find(
                    'Face Panel')
                bpy.ops.armature.move_to_collection(
                    collection_index=facepanel_index)
                bpy.ops.pose.select_all(action='DESELECT')
                for bone_name in ["FacePanel", "FacePanelRoot"]:
                    pbone = armature_obj.pose.bones.get(bone_name)
                    if pbone:
                        pbone.bone.select = True
                if 'Others' not in armature_obj.data.collections:
                    armature_obj.data.collections.new(name='Others')
                others_index = armature_obj.data.collections.find('Others')
                bpy.ops.armature.move_to_collection(
                    collection_index=others_index)
                bpy.ops.pose.select_all(action='DESELECT')
                bpy.ops.object.mode_set(mode='OBJECT')
                bone = armature_obj.data.bones.get("MouthPanel")
                if bone:
                    bone.hide_select = True
                fp_root_bone = armature_obj.data.bones.get("FacePanelRoot")
                if fp_root_bone:
                    fp_root_bone.hide = True
                armature_obj.data.collections_all["Face Panel"].is_visible = True
                if "Others" in armature_obj.data.collections_all:
                    armature_obj.data.collections_all["Others"].is_visible = False
                bpy.ops.object.select_all(action='DESELECT')
                view_layer = bpy.context.view_layer
                collection = bpy.context.scene.collection
                mesh_names_to_delete = [
                    "CustomTriangle", "CustomSquare", "CustomDiamond", "CustomCross",
                    "WGT-rig_eyes", "WGT-rig_eye.L", "WGT-rig_eye.R"]
                for name in mesh_names_to_delete:
                    obj = bpy.data.objects.get(name)
                    if obj and obj.type == 'MESH':
                        if obj.name not in view_layer.objects:
                            collection.objects.link(obj)
                        obj.select_set(True)
                        view_layer.objects.active = obj
                        bpy.ops.object.delete()

                if "CustomShapes" in bpy.data.collections:
                    custom_coll = bpy.data.collections["CustomShapes"]
                    bpy.data.collections.remove(custom_coll)

                armature_obj['face_panel_created'] = True
                self.report(
                    {'INFO'}, f"Create Face Panel for '{cleaned_name}' completed")

                try:
                    bpy.ops.ww.create_collection()
                except RuntimeError:
                    pass

            result = {'FINISHED'}
        except Exception:
            self.report({'ERROR'}, traceback.format_exc())
            result = {'CANCELLED'}
        finally:
            self._restore_state(
                initial_active_object,
                initial_selected_objects, initial_mode)
        return result
