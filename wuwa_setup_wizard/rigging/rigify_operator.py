import math

import bpy
import mathutils

from ..core.object_manager import ObjectManager
from .eye_tracker_utils import EyeTrackerUtils


# ========== RIGIFY OPERATOR ==========

# Generates Rigify control rig with bone adjustments and weight remapping
class WW_OT_Rigify(bpy.types.Operator):
    bl_idname = "ww.rigify_armature"
    bl_label = "Rigify Armature"
    bl_description = "Generates a Rigify control rig for the selected character's armature."
    bl_options = {'REGISTER', 'UNDO'}

    left_bone_pairs = [
        ("Bip001LFinger1", "Bip001LFinger11"),
        ("Bip001LFinger11", "Bip001LFinger12"),
        ("Bip001LFinger12", "Bip001LFinger13"),
        ("Bip001LFinger2", "Bip001LFinger21"),
        ("Bip001LFinger21", "Bip001LFinger22"),
        ("Bip001LFinger22", "Bip001LFinger23"),
        ("Bip001LFinger3", "Bip001LFinger31"),
        ("Bip001LFinger31", "Bip001LFinger32"),
        ("Bip001LFinger32", "Bip001LFinger33"),
        ("Bip001LFinger4", "Bip001LFinger41"),
        ("Bip001LFinger41", "Bip001LFinger42"),
        ("Bip001LFinger42", "Bip001LFinger43"),
    ]

    right_bone_pairs = [
        ("Bip001RFinger1", "Bip001RFinger11"),
        ("Bip001RFinger11", "Bip001RFinger12"),
        ("Bip001RFinger12", "Bip001RFinger13"),
        ("Bip001RFinger2", "Bip001RFinger21"),
        ("Bip001RFinger21", "Bip001RFinger22"),
        ("Bip001RFinger22", "Bip001RFinger23"),
        ("Bip001RFinger3", "Bip001RFinger31"),
        ("Bip001RFinger31", "Bip001RFinger32"),
        ("Bip001RFinger32", "Bip001RFinger33"),
        ("Bip001RFinger4", "Bip001RFinger41"),
        ("Bip001RFinger41", "Bip001RFinger42"),
        ("Bip001RFinger42", "Bip001RFinger43"),
    ]

    skip_if_finger13 = [
        ("Bip001LFinger1", "Bip001LFinger11"),
        ("Bip001LFinger2", "Bip001LFinger21"),
        ("Bip001LFinger3", "Bip001LFinger31"),
        ("Bip001LFinger4", "Bip001LFinger41"),
        ("Bip001RFinger1", "Bip001RFinger11"),
        ("Bip001RFinger2", "Bip001RFinger21"),
        ("Bip001RFinger3", "Bip001RFinger31"),
        ("Bip001RFinger4", "Bip001RFinger41"),
    ]

    ALIGN_THRESHOLD = math.radians(5)
    TARGET_ANGLE = math.radians(5)
    STEP_SIZE = 0.001
    MAX_ITER = 50
    move_amount = 0.0001

    # Requires mesh with an armature modifier attached
    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        return context.active_object.type in {'MESH', 'ARMATURE'}

    # Ensures Blender is in Object mode before operations
    def ensure_object_mode(self, context):
        if context.mode != 'OBJECT':
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except RuntimeError:
                pass
        if not context.active_object:
            objects = [obj for obj in context.scene.objects if obj.type in {
                'MESH', 'ARMATURE'}]
            if objects:
                context.view_layer.objects.active = objects[0]

    # Safely switches Blender mode with error handling
    def safe_mode_set(self, context, mode):
        try:
            self.ensure_object_mode(context)
            if context.active_object:
                bpy.ops.object.mode_set(mode=mode)
        except RuntimeError:
            self.ensure_object_mode(context)
            if context.active_object:
                try:
                    bpy.ops.object.mode_set(mode=mode)
                except RuntimeError:
                    return False
        return True

    # Gets local X axis vector for a bone
    def get_local_x(self, bone):
        return bone.matrix.to_3x3().col[0].normalized()

    # Calculates angle between two vectors
    def angle_between(self, v1, v2):
        if v1.length == 0 or v2.length == 0:
            return math.pi
        return v1.angle(v2)

    # Returns all bone pairs for rigify setup
    def all_bone_pairs(self):
        return self.left_bone_pairs + self.right_bone_pairs

    # Checks bone alignment for proper rigify configuration
    def check_alignment(self, edit_bones, finger13_exists_left, finger13_exists_right):
        for name1, name2 in self.all_bone_pairs():
            if (finger13_exists_left and (name1, name2) in self.skip_if_finger13) or \
               (finger13_exists_right and (name1, name2) in self.skip_if_finger13):
                continue
            b1 = edit_bones.get(name1)
            b2 = edit_bones.get(name2)
            if b1 and b2:
                x1 = self.get_local_x(b1)
                x2 = self.get_local_x(b2)
                angle = self.angle_between(x1, x2)
                if angle < self.ALIGN_THRESHOLD:
                    return True
        return False

    # Applies bone position adjustments for rigify
    def apply_adjustment(self, edit_bones, finger13_exists_left, finger13_exists_right):
        if finger13_exists_left or finger13_exists_right:
            outward_bones = [
                "Bip001LFinger11", "Bip001LFinger21", "Bip001LFinger31", "Bip001LFinger41",
                "Bip001RFinger11", "Bip001RFinger21", "Bip001RFinger31", "Bip001RFinger41"
            ]
            inward_bones = [
                "Bip001LFinger13", "Bip001LFinger23", "Bip001LFinger33", "Bip001LFinger43",
                "Bip001RFinger13", "Bip001RFinger23", "Bip001RFinger33", "Bip001RFinger43"
            ]
        else:
            outward_bones = [
                "Bip001LFinger1", "Bip001LFinger2", "Bip001LFinger3", "Bip001LFinger4",
                "Bip001RFinger1", "Bip001RFinger2", "Bip001RFinger3", "Bip001RFinger4"
            ]
            inward_bones = [
                "Bip001LFinger12", "Bip001LFinger22", "Bip001LFinger32", "Bip001LFinger42",
                "Bip001RFinger12", "Bip001RFinger22", "Bip001RFinger32", "Bip001RFinger42"
            ]

        for bone_name in outward_bones:
            bone = edit_bones.get(bone_name)
            if bone:
                x_axis = self.get_local_x(bone)
                bone.tail += x_axis * self.move_amount

        for bone_name in inward_bones:
            bone = edit_bones.get(bone_name)
            if bone:
                x_axis = self.get_local_x(bone)
                bone.tail -= x_axis * self.move_amount

    # Removes existing bone collections before rigify
    def remove_bone_collections(self, armature):
        if armature.data.collections:
            for collection in armature.data.collections[:]:
                armature.data.collections.remove(collection)

    # Adjusts bone head/tail positions for rigify compatibility
    def adjust_bone_positions(self, armature, bone_pairs):
        for bone1_name, bone2_name in bone_pairs:
            if bone1_name in armature.data.edit_bones and bone2_name in armature.data.edit_bones:
                bone1 = armature.data.edit_bones[bone1_name]
                bone2 = armature.data.edit_bones[bone2_name]
                bone1.tail = bone2.head

    # Sets bone connection flags for proper hierarchy
    def set_bone_connect(self, armature, bone_names):
        for bone_name in bone_names:
            if bone_name in armature.data.edit_bones:
                armature.data.edit_bones[bone_name].use_connect = True

    # Adjusts bone roll for face panel bones
    def adjust_bone_roll(self, armature, bones_to_adjust_roll):
        for bone_name in bones_to_adjust_roll:
            if bone_name in armature.data.edit_bones:
                armature.data.edit_bones[bone_name].roll = 0

    # Processes bone collections and assigns rigify types
    def process_bone_collections_and_rigify(self, armature, bone_data):
        for collection_name, index, row in bone_data:
            bpy.ops.armature.collection_add()
            new_collection = armature.data.collections[-1]
            new_collection.name = collection_name
            bpy.ops.armature.rigify_collection_set_ui_row(index=index, row=row)

    # Modifies rigify rig type for specific bones
    def modify_bone_rig_type(self, armature, bones_and_rig_types):
        for bone_name, rig_type, widget_type in bones_and_rig_types:
            bone = armature.pose.bones.get(bone_name)
            if not bone:
                continue
            armature.data.bones[bone_name].select = True
            armature.data.bones.active = armature.data.bones[bone_name]
            if not hasattr(bone, 'rigify_type'):
                try:
                    import addon_utils, sys, io
                    old_out, old_err = sys.stdout, sys.stderr
                    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
                    try:
                        addon_utils.disable("rigify", default_set=False)
                        addon_utils.enable("rigify", default_set=True)
                    finally:
                        sys.stdout, sys.stderr = old_out, old_err
                except Exception:
                    pass
            if hasattr(bone, 'rigify_type'):
                bone.rigify_type = rig_type
                if widget_type and hasattr(bone, 'rigify_parameters') and bone.rigify_parameters:
                    bone.rigify_parameters.super_copy_widget_type = widget_type
            else:
                print(f"[WuWa] WARNING: rigify_type not found on bone '{bone_name}' — skipping")

    # Creates heel bone from foot bone for IK setup
    def duplicate_and_adjust_heel_bone(self, armature, foot_bone_name, toe_bone_name,
                                       heel_bone_name, rotation_angle=1.5708):
        if toe_bone_name in armature.data.edit_bones:
            toe_bone = armature.data.edit_bones[toe_bone_name]
            heel_bone = armature.data.edit_bones.new(name=heel_bone_name)
            heel_bone.head = toe_bone.head
            heel_bone.tail = toe_bone.tail
            heel_bone.roll = toe_bone.roll

            rotation_matrix = mathutils.Matrix.Rotation(rotation_angle, 4, 'Y')
            heel_bone.tail = heel_bone.head + \
                rotation_matrix @ (heel_bone.tail - heel_bone.head)

            if foot_bone_name in armature.data.edit_bones:
                foot_bone = armature.data.edit_bones[foot_bone_name]
                foot_head_y = foot_bone.head[1]
                heel_bone.head[1] = foot_head_y
                heel_bone.tail[1] = foot_head_y

            heel_bone.parent = armature.data.edit_bones[foot_bone_name]

    # Locks bone location, rotation, scale transforms
    def lock_bone_transformations(self, bone):
        bone.lock_location[0] = False
        bone.lock_location[1] = False
        bone.lock_location[2] = False
        bone.lock_rotation_w = False
        bone.lock_rotation[0] = False
        bone.lock_rotation[1] = False
        bone.lock_rotation[2] = False
        bone.lock_scale[0] = False
        bone.lock_scale[1] = False
        bone.lock_scale[2] = False

    # Selects bones by keyword and moves to collection
    def select_and_move_bones(self, armature, keyword, collection_index):
        bpy.ops.pose.select_all(action='DESELECT')
        selected_bones = []
        for bone in armature.pose.bones:
            if keyword in bone.name:
                selected_bones.append(bone)
                bone.bone.select = True
                self.lock_bone_transformations(bone)

        if selected_bones:
            bpy.ops.armature.move_to_collection(
                collection_index=collection_index)
        return len(selected_bones)

    # Remaps vertex weights between bone pairs
    def remap_vertex_weights(self, weight_mappings, obj):
        if obj is None or obj.type != 'MESH':
            return

        vgroups = obj.vertex_groups

        if bpy.context.mode != 'OBJECT':
            self.safe_mode_set(bpy.context, 'OBJECT')

        for source_group_name, target_group_name in weight_mappings.items():
            if source_group_name not in vgroups:
                continue

            source_group = vgroups[source_group_name]

            if target_group_name not in vgroups:
                target_group = vgroups.new(name=target_group_name)
            else:
                target_group = vgroups[target_group_name]

            for vert in obj.data.vertices:
                new_weight = 0.0
                has_source_weight = False

                for group in vert.groups:
                    if group.group == source_group.index:
                        new_weight += group.weight
                        has_source_weight = True
                        break

                if has_source_weight:
                    for group in vert.groups:
                        if group.group == target_group.index:
                            new_weight += group.weight
                            break

                    target_group.add([vert.index], new_weight, 'REPLACE')
                    source_group.remove([vert.index])

    # Generates Rigify rig, remaps vertex weights, and creates eye tracker controls
    def execute(self, context):
        try:
            import addon_utils
            import sys
            import io
            old_stdout, old_stderr = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
            try:
                addon_utils.enable("rigify", default_set=True)
            finally:
                sys.stdout, sys.stderr = old_stdout, old_stderr

            try:
                test_bone = next(
                    (b for arm in bpy.data.armatures
                     for b in bpy.data.objects
                     if b.type == 'ARMATURE' and b.data == arm
                     for b in b.pose.bones),
                    None
                )
                if test_bone is not None and not hasattr(test_bone, 'rigify_type'):
                    old_stdout2, old_stderr2 = sys.stdout, sys.stderr
                    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
                    try:
                        addon_utils.disable("rigify", default_set=False)
                        addon_utils.enable("rigify", default_set=True)
                    finally:
                        sys.stdout, sys.stderr = old_stdout2, old_stderr2
            except Exception:
                pass

            ObjectManager.clear_cache()
            ObjectManager.refresh_context()

            selected_object = context.active_object
            if not selected_object:
                return {"CANCELLED"}

            original_selected_object_type = selected_object.type
            original_selected_object_name = selected_object.name

            if selected_object.type == 'MESH':
                for modifier in selected_object.modifiers:
                    if modifier.type == 'ARMATURE' and modifier.object:
                        armature_obj = modifier.object
                        if armature_obj.hide_get():
                            armature_obj.hide_set(False)
                        context.view_layer.objects.active = armature_obj
                        selected_object = armature_obj
                        break
            elif selected_object.type != 'ARMATURE':
                for obj in context.scene.objects:
                    if obj.type == 'ARMATURE':
                        if obj.hide_get():
                            obj.hide_set(False)
                        context.view_layer.objects.active = obj
                        selected_object = obj
                        break

            if selected_object.type != 'ARMATURE':
                return {"CANCELLED"}

            OrigArmature = selected_object.name
            RigArmature = "RIG-" + OrigArmature

            if RigArmature in bpy.data.objects:
                return {"CANCELLED"}

            if selected_object.get('rigify_generated'):
                return {"CANCELLED"}

            CharacterMeshes = []
            for obj in context.scene.objects:
                if obj.type == 'MESH':
                    for modifier in obj.modifiers:
                        if modifier.type == 'ARMATURE' and modifier.object and modifier.object.name == OrigArmature:
                            CharacterMeshes.append(obj)
                            break

            if not CharacterMeshes:
                return {"CANCELLED"}

            CharacterMesh = CharacterMeshes[0]

            if selected_object.hide_viewport:
                selected_object.hide_viewport = False
            if selected_object.hide_get():
                selected_object.hide_set(False)

            original_location = selected_object.location.copy()
            original_rotation = selected_object.rotation_euler.copy()
            original_scale = selected_object.scale.copy()

            selected_object.location = (0, 0, 0)
            selected_object.rotation_euler = (0, 0, 0)
            selected_object.scale = (1, 1, 1)

            if not self.safe_mode_set(context, 'EDIT'):
                return {"CANCELLED"}

            edit_bones = selected_object.data.edit_bones
            finger13_exists_left = "Bip001LFinger13" in edit_bones
            finger13_exists_right = "Bip001RFinger13" in edit_bones

            alignment_iterations = 0
            while self.check_alignment(edit_bones, finger13_exists_left, finger13_exists_right):
                self.apply_adjustment(
                    edit_bones, finger13_exists_left, finger13_exists_right)
                alignment_iterations += 1
                if alignment_iterations > self.MAX_ITER:
                    break

            if not self.safe_mode_set(context, 'OBJECT'):
                return {"CANCELLED"}

            bpy.ops.object.transform_apply(scale=True)

            rig_armature_object = context.view_layer.objects.active
            if rig_armature_object and rig_armature_object.type == 'ARMATURE':
                if not self.safe_mode_set(context, 'EDIT'):
                    return {"CANCELLED"}

                spine_bone = rig_armature_object.data.edit_bones.get(
                    "Bip001Spine2")
                if spine_bone:
                    bone_length = (spine_bone.tail - spine_bone.head).length
                    if bone_length < 0.06:
                        direction = spine_bone.tail - spine_bone.head
                        direction.normalize()
                        spine_bone.tail = spine_bone.head + direction * 0.15
                        spine_bone.tail.y = spine_bone.head.y
                        spine_bone.head.z += 0.03
                        spine_bone.tail.z += 0.03

                if not self.safe_mode_set(context, 'OBJECT'):
                    return {"CANCELLED"}

            armature = context.object
            self.remove_bone_collections(armature)

            if not self.safe_mode_set(context, 'EDIT'):
                return {"CANCELLED"}

            bone_pairs = [
                ('Bip001Spine1', 'Bip001Spine2'),
                ('Bip001Pelvis', 'Bip001Spine'),
                ('Bip001RThigh', 'Bip001RCalf'),
                ('Bip001LThigh', 'Bip001LCalf'),
                ('Bip001RCalf', 'Bip001RFoot'),
                ('Bip001LCalf', 'Bip001LFoot'),
                ('Bip001LUpperArm', 'Bip001LForearm'),
                ('Bip001RUpperArm', 'Bip001RForearm'),
                ('Bip001LForearm', 'Bip001LHand'),
                ('Bip001RForearm', 'Bip001RHand'),
                ('Bip001LThigh', 'Bip001LCalf'),
                ('Bip001LCalf', 'Bip001LFoot'),
                ('Bip001LFoot', 'Bip001LToe0'),
                ('Bip001RThigh', 'Bip001RCalf'),
                ('Bip001RCalf', 'Bip001RFoot'),
                ('Bip001RFoot', 'Bip001RToe0'),
            ]

            self.adjust_bone_positions(armature, bone_pairs)

            twist_bones = {
                'Bip001RForeTwist': 'Bip001RForearm',
                'Bip001LForeTwist': 'Bip001LForearm'
            }

            for twist_bone, correct_parent in twist_bones.items():
                if twist_bone in armature.data.edit_bones and correct_parent in armature.data.edit_bones:
                    bone = armature.data.edit_bones[twist_bone]
                    if bone.parent != armature.data.edit_bones[correct_parent]:
                        bone.parent = armature.data.edit_bones[correct_parent]

            spine_bones = [
                'Bip001Spine', 'Bip001Spine1', 'Bip001Spine2',
                'Bip001LForearm', 'Bip001LHand', 'Bip001LFinger01',
                'Bip001LFinger02', 'Bip001LFinger11', 'Bip001LFinger12',
                'Bip001LFinger21', 'Bip001LFinger22', 'Bip001LFinger31',
                'Bip001LFinger32', 'Bip001LFinger41', 'Bip001LFinger42',
                'Bip001RForearm', 'Bip001RHand', 'Bip001RFinger01',
                'Bip001RFinger02', 'Bip001RFinger11', 'Bip001RFinger12',
                'Bip001RFinger21', 'Bip001RFinger22', 'Bip001RFinger31',
                'Bip001RFinger32', 'Bip001RFinger41', 'Bip001RFinger42',
                'Bip001LCalf', 'Bip001LFoot', 'Bip001LToe0',
                'Bip001RCalf', 'Bip001RFoot', 'Bip001RToe0',
                'Bip001Head',
                'Bip001LFinger13', 'Bip001LFinger23', 'Bip001LFinger33', 'Bip001LFinger43',
                'Bip001RFinger13', 'Bip001RFinger23', 'Bip001RFinger33', 'Bip001RFinger43',
            ]

            self.set_bone_connect(armature, spine_bones)

            bones_to_adjust_roll = [
                'Bip001Pelvis', 'Bip001Spine', 'Bip001Spine1',
                'Bip001Spine2', 'Bip001LClavicle', 'Bip001RClavicle'
            ]

            self.adjust_bone_roll(armature, bones_to_adjust_roll)

            if not self.safe_mode_set(context, 'OBJECT'):
                return {"CANCELLED"}

            if not self.safe_mode_set(context, 'POSE'):
                return {"CANCELLED"}

            bone_data = [
                ('Torso', 0, 1),
                ('Torso (Tweak)', 1, 2),
                ('Fingers', 2, 3),
                ('Fingers (Details)', 3, 4),
                ('Arm.L (IK)', 4, 5),
                ('Arm.R (IK)', 5, 5),
                ('Arm.L (FK)', 6, 6),
                ('Arm.R (FK)', 7, 6),
                ('Arm.L (Tweak)', 8, 7),
                ('Arm.R (Tweak)', 9, 7),
                ('Leg.L (IK)', 10, 8),
                ('Leg.R (IK)', 11, 8),
                ('Leg.L (FK)', 12, 9),
                ('Leg.R (FK)', 13, 9),
                ('Leg.L (Tweak)', 14, 10),
                ('Leg.R (Tweak)', 15, 10),
                ('Hair', 16, 11),
                ('Cloth', 17, 11),
                ('Skirt', 18, 11),
                ('Chest', 19, 11),
                ('Face Panel', 20, 12),
                ('Root', 21, 13),
            ]

            self.process_bone_collections_and_rigify(armature, bone_data)

            bpy.ops.armature.collection_add()
            new_collection = armature.data.collections[-1]
            new_collection.name = 'Others'

            bpy.ops.armature.rigify_collection_add_ui_row(row=3, add=True)
            bpy.ops.armature.rigify_collection_add_ui_row(row=6, add=True)
            bpy.ops.armature.rigify_collection_add_ui_row(row=10, add=True)
            bpy.ops.armature.rigify_collection_add_ui_row(row=14, add=True)
            bpy.ops.armature.rigify_collection_add_ui_row(row=16, add=True)

            bones_and_rig_types = [
                ('Bip001Pelvis', 'spines.basic_spine', None),
                ('Bip001LClavicle', 'basic.super_copy', 'shoulder'),
                ('Bip001RClavicle', 'basic.super_copy', 'shoulder'),
                ('Bip001LUpperArm', 'limbs.arm', None),
                ('Bip001RUpperArm', 'limbs.arm', None),
                ('Bip001LThigh', 'limbs.leg', None),
                ('Bip001RThigh', 'limbs.leg', None),
                ('Bip001RFinger0', 'limbs.super_finger', None),
                ('Bip001LFinger0', 'limbs.super_finger', None),
                ('Bip001Neck', 'spines.super_head', None),
            ]

            if 'Bip001LFinger13' in armature.pose.bones:
                bones_and_rig_types.extend([
                    ('Bip001LFinger11', 'limbs.super_finger', None),
                    ('Bip001LFinger21', 'limbs.super_finger', None),
                    ('Bip001LFinger31', 'limbs.super_finger', None),
                    ('Bip001LFinger41', 'limbs.super_finger', None),
                    ('Bip001RFinger11', 'limbs.super_finger', None),
                    ('Bip001RFinger21', 'limbs.super_finger', None),
                    ('Bip001RFinger31', 'limbs.super_finger', None),
                    ('Bip001RFinger41', 'limbs.super_finger', None),
                ])
            else:
                bones_and_rig_types.extend([
                    ('Bip001LFinger1', 'limbs.super_finger', None),
                    ('Bip001LFinger2', 'limbs.super_finger', None),
                    ('Bip001LFinger3', 'limbs.super_finger', None),
                    ('Bip001LFinger4', 'limbs.super_finger', None),
                    ('Bip001RFinger1', 'limbs.super_finger', None),
                    ('Bip001RFinger2', 'limbs.super_finger', None),
                    ('Bip001RFinger3', 'limbs.super_finger', None),
                    ('Bip001RFinger4', 'limbs.super_finger', None),
                ])

            self.modify_bone_rig_type(armature, bones_and_rig_types)

            if not self.safe_mode_set(context, 'EDIT'):
                return {"CANCELLED"}

            self.duplicate_and_adjust_heel_bone(
                armature, 'Bip001LFoot', 'Bip001LToe0', 'Bip001LHeel0', rotation_angle=1.5708)
            self.duplicate_and_adjust_heel_bone(
                armature, 'Bip001RFoot', 'Bip001RToe0', 'Bip001RHeel0', rotation_angle=-1.5708)

            if not self.safe_mode_set(context, 'OBJECT'):
                return {"CANCELLED"}

            if context.object and context.object.type == 'ARMATURE':
                armature = context.object
                if not self.safe_mode_set(context, 'EDIT'):
                    return {"CANCELLED"}

                for bone in armature.data.edit_bones:
                    if bone.name.startswith("Bip001R") and not bone.name.endswith(".R"):
                        bone.name += ".R"
                    elif bone.name.startswith("Bip001L") and not bone.name.endswith(".L"):
                        bone.name += ".L"

                for bone in armature.data.edit_bones:
                    if bone.name.startswith("Bip001R"):
                        bone.name = bone.name.replace("Bip001R", "Bip001", 1)
                    elif bone.name.startswith("Bip001L"):
                        bone.name = bone.name.replace("Bip001L", "Bip001", 1)

                import sys
                import io
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = io.StringIO()
                sys.stderr = io.StringIO()
                try:
                    bpy.ops.pose.rigify_generate()
                except Exception:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    return {"CANCELLED"}
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr

                rig_obj = context.scene.objects.get(RigArmature)
                if rig_obj:
                    rig_obj.location = original_location
                    rig_obj.rotation_euler = original_rotation
                    rig_obj.scale = original_scale

                if not self.safe_mode_set(context, 'POSE'):
                    return {"CANCELLED"}

                armature = context.object

                pose_bone_neck = armature.pose.bones.get("neck")
                if pose_bone_neck:
                    pose_bone_neck.custom_shape_scale_xyz = (0.75, 0.75, 0.75)
                    pose_bone_neck.color.palette = 'THEME09'

                pose_bone_head = armature.pose.bones.get("head")
                if pose_bone_head:
                    pose_bone_head.custom_shape_scale_xyz = (2, 2, 2)
                    pose_bone_head.custom_shape_translation = (0, -0.05, 0)
                    pose_bone_head.color.palette = 'THEME09'
                    if "head_follow" in pose_bone_head:
                        pose_bone_head["head_follow"] = 1.0

                if not self.safe_mode_set(context, 'OBJECT'):
                    return {"CANCELLED"}

                context.object.pose.bones["Bip001UpperArm_parent.L"]["IK_Stretch"] = 0.000
                context.object.pose.bones["Bip001UpperArm_parent.R"]["IK_Stretch"] = 0.000
                context.object.pose.bones["Bip001Thigh_parent.L"]["IK_Stretch"] = 0.000
                context.object.pose.bones["Bip001Thigh_parent.R"]["IK_Stretch"] = 0.000

                obj = context.active_object
                if obj and obj.type == 'ARMATURE':
                    if not self.safe_mode_set(context, 'EDIT'):
                        return {"CANCELLED"}

                    for bone in obj.data.edit_bones:
                        if bone.name.startswith('ORG-'):
                            bone.use_deform = True

                    if not self.safe_mode_set(context, 'OBJECT'):
                        return {"CANCELLED"}

                for mesh_part in CharacterMeshes:
                    bpy.ops.object.select_all(action='DESELECT')
                    context.view_layer.objects.active = mesh_part
                    mesh_part.select_set(True)

                    for group in mesh_part.vertex_groups:
                        if not group.name.startswith("ORG-"):
                            new_name = "ORG-" + group.name
                            group.name = new_name

                weight_mappings = {
                    "ORG-Bip001UpArmTwist.L": "DEF-Bip001UpperArm.L",
                    "ORG-Bip001UpArmTwist1.L": "DEF-Bip001UpperArm.L",
                    "ORG-Bip001UpArmTwist2.L": "DEF-Bip001UpperArm.L.001",
                    "ORG-Bip001UpperArm.L": "DEF-Bip001UpperArm.L.001",
                    "ORG-Bip001Forearm.L": "DEF-Bip001Forearm.L",
                    "ORG-Bip001ForeTwist.L": "DEF-Bip001Forearm.L.001",
                    "ORG-Bip001ForeTwist1.L": "DEF-Bip001Forearm.L.001",
                    "ORG-Bone_HandTwist_L": "DEF-Bip001Forearm.L.001",
                    "ORG-Bip001ForeTwist2.L": "DEF-Bip001Forearm.L.001",
                    "ORG-Bip001_L_Elbow_F": "DEF-Bip001UpperArm.L.001",
                    "ORG-Bip001_L_Elbow_B": "DEF-Bip001UpperArm.L.001",
                    "ORG-Bip001UpArmTwist.R": "DEF-Bip001UpperArm.R",
                    "ORG-Bip001UpArmTwist1.R": "DEF-Bip001UpperArm.R",
                    "ORG-Bip001UpArmTwist2.R": "DEF-Bip001UpperArm.R.001",
                    "ORG-Bip001UpperArm.R": "DEF-Bip001UpperArm.R.001",
                    "ORG-Bip001Forearm.R": "DEF-Bip001Forearm.R",
                    "ORG-Bip001ForeTwist.R": "DEF-Bip001Forearm.R.001",
                    "ORG-Bip001ForeTwist1.R": "DEF-Bip001Forearm.R.001",
                    "ORG-Bone_HandTwist_R": "DEF-Bip001Forearm.R.001",
                    "ORG-Bip001ForeTwist2.R": "DEF-Bip001Forearm.R.001",
                    "ORG-Bip001_R_Elbow_F": "DEF-Bip001UpperArm.R.001",
                    "ORG-Bip001_R_Elbow_B": "DEF-Bip001UpperArm.R.001",
                    "ORG-Bip001ThighTwist.L": "DEF-Bip001Thigh.L",
                    "ORG-Bip001Thigh.L": "DEF-Bip001Thigh.L.001",
                    "ORG-Bip001_L_Calf": "DEF-Bip001Calf.L",
                    "ORG-Bip001_L_Knee_B": "DEF-Bip001Thigh.L.001",
                    "ORG-Bip001_L_Knee_F": "DEF-Bip001Thigh.L.001",
                    "ORG-Bip001ThighTwist1.L": "DEF-Bip001Thigh.L",
                    "ORG-Bip001_L_CalfTwist": "DEF-Bip001Calf.L.001",
                    "ORG-Bip001ThighTwist.R": "DEF-Bip001Thigh.R",
                    "ORG-Bip001Thigh.R": "DEF-Bip001Thigh.R.001",
                    "ORG-Bip001_R_Calf": "DEF-Bip001Calf.R",
                    "ORG-Bip001_R_Knee_B": "DEF-Bip001Thigh.R.001",
                    "ORG-Bip001_R_Knee_F": "DEF-Bip001Thigh.R.001",
                    "ORG-Bip001ThighTwist1.R": "DEF-Bip001Thigh.R",
                    "ORG-Bip001_R_CalfTwist": "DEF-Bip001Calf.R.001",
                }

                for mesh_part in CharacterMeshes:
                    self.remap_vertex_weights(weight_mappings, mesh_part)

                rig_armature_object = context.scene.objects.get(RigArmature)
                for mesh_part in CharacterMeshes:
                    for modifier in mesh_part.modifiers:
                        if modifier.type == 'ARMATURE' and modifier.object and modifier.object.name == OrigArmature:
                            if rig_armature_object:
                                modifier.object = rig_armature_object
                            break

                for mesh_part in CharacterMeshes:
                    armature_mod = next(
                        (mod for mod in mesh_part.modifiers if mod.type == 'ARMATURE'), None)
                    if armature_mod and armature_mod.object:
                        armature_obj = armature_mod.object
                        mesh_part.parent = armature_obj

                obj = CharacterMesh

                source_shape_keys = ["Pupil_R",
                                     "Pupil_L", "Pupil_Up", "Pupil_Down"]

                if obj and obj.type == 'MESH' and obj.data.shape_keys:
                    self.ensure_object_mode(context)
                    EyeTrackerUtils.split_shape_keys(
                        obj, source_shape_keys)

                bpy.ops.object.select_all(action='DESELECT')
                rig_armature_object = context.scene.objects.get(RigArmature)

                if rig_armature_object:
                    bpy.ops.object.select_all(action='DESELECT')
                    context.view_layer.objects.active = rig_armature_object
                    rig_armature_object.select_set(True)

                    eye_tracker_location = rig_armature_object.location.copy()
                    eye_tracker_rotation = rig_armature_object.rotation_euler.copy()
                    eye_tracker_scale = rig_armature_object.scale.copy()

                    rig_armature_object.location = (0, 0, 0)
                    rig_armature_object.rotation_euler = (0, 0, 0)
                    rig_armature_object.scale = (1, 1, 1)

                    meshes = EyeTrackerUtils.get_meshes_for_armature(
                        rig_armature_object)

                    if not self.safe_mode_set(context, 'EDIT'):
                        return {"CANCELLED"}

                    edit_bones = rig_armature_object.data.edit_bones
                    EyeTrackerUtils.create_eye_tracker_bones(
                        rig_armature_object, edit_bones, meshes)

                    context.scene.cursor.location = mathutils.Vector(
                        (0, 0, 0))

                    if not self.safe_mode_set(context, 'OBJECT'):
                        return {"CANCELLED"}

                    rig_armature_object.location = eye_tracker_location
                    rig_armature_object.rotation_euler = (
                        eye_tracker_rotation)
                    rig_armature_object.scale = eye_tracker_scale

                    EyeTrackerUtils.create_circle_widget(
                        "WGT-rig_eye.L",
                        location=(-0.3, 0, 0))
                    EyeTrackerUtils.create_circle_widget(
                        "WGT-rig_eye.R",
                        location=(0.3, 0, 0))
                    EyeTrackerUtils.create_capsule_widget(
                        "WGT-rig_eyes")

                    if CharacterMesh is None or rig_armature_object is None:
                        pass
                    else:
                        bpy.ops.object.select_all(action='DESELECT')
                        last_selected_mesh = None
                        for obj in context.scene.objects:
                            if obj.type == 'MESH':
                                for modifier in obj.modifiers:
                                    if modifier.type == 'ARMATURE' and modifier.object == rig_armature_object:
                                        obj.select_set(True)
                                        last_selected_mesh = obj

                        if last_selected_mesh:
                            context.view_layer.objects.active = last_selected_mesh

                            self.ensure_object_mode(context)

                            last_selected_mesh.select_set(False)
                            context.view_layer.objects.active = rig_armature_object

                            EyeTrackerUtils.setup_pupil_drivers(
                                rig_armature_object, CharacterMesh)

                            self.ensure_object_mode(context)

                            context.view_layer.objects.active = rig_armature_object

                            if not self.safe_mode_set(context, 'POSE'):
                                return {"CANCELLED"}

                            bones_to_lock = ["EyeTracker", "Eye.L", "Eye.R"]
                            for bone_name in bones_to_lock:
                                if bone_name not in rig_armature_object.pose.bones:
                                    continue
                                pbone = rig_armature_object.pose.bones[bone_name]
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
                                if bone_name == "EyeTracker":
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

                            self.ensure_object_mode(context)

                            context.view_layer.objects.active = rig_armature_object

                            if not self.safe_mode_set(context, 'POSE'):
                                return {"CANCELLED"}

                            pose_bones = rig_armature_object.pose.bones
                            custom_shapes = {
                                "EyeTracker": "WGT-rig_eyes",
                                "Eye.L": "WGT-rig_eye.L",
                                "Eye.R": "WGT-rig_eye.R"
                            }

                            for bone_name, shape_name in custom_shapes.items():
                                if bone_name in pose_bones and shape_name in bpy.data.objects:
                                    bone = pose_bones[bone_name]
                                    bone.custom_shape = bpy.data.objects[shape_name]
                                    bone.custom_shape_scale_xyz = (
                                        4.0, 4.0, 4.0)

                            self.ensure_object_mode(context)

                            mesh_names_to_delete = ["WGT-rig_eyes",
                                                    "WGT-rig_eye.R", "WGT-rig_eye.L"]

                            bpy.ops.object.select_all(action='DESELECT')
                            for name in mesh_names_to_delete:
                                obj = bpy.data.objects.get(name)
                                if obj and obj.type == 'MESH':
                                    if obj.name in context.view_layer.objects:
                                        obj.select_set(True)

                            bpy.ops.object.delete()

                            if not self.safe_mode_set(context, 'POSE'):
                                return {"CANCELLED"}

                            armature = context.view_layer.objects.active

                            bones_to_move = {
                                0: [
                                    "torso", "chest", "Bip001Clavicle.L", "Bip001Clavicle.R",
                                    "hips", "neck", "head",
                                ],
                                1: [
                                    "Bip001Spine_fk", "Bip001Spine1_fk", "Bip001Spine2_fk",
                                    "tweak_Bip001Spine1", "tweak_Bip001Spine2", "tweak_Bip001Spine2.001",
                                    "tweak_Bip001Spine", "tweak_Bip001Pelvis", "Bip001Pelvis_fk",
                                    "tweak_Bip001Neck", "tweak_Bip001Head",
                                ],
                                2: [
                                    "Bip001Finger0_master.L", "Bip001Finger1_master.L",
                                    "Bip001Finger2_master.L", "Bip001Finger3_master.L",
                                    "Bip001Finger4_master.L",
                                    "Bip001Finger0_master.R", "Bip001Finger1_master.R",
                                    "Bip001Finger2_master.R", "Bip001Finger3_master.R",
                                    "Bip001Finger4_master.R",
                                    "Bip001Finger11_master.L", "Bip001Finger21_master.L",
                                    "Bip001Finger21_master.L", "Bip001Finger31_master.L",
                                    "Bip001Finger41_master.L",
                                    "Bip001Finger11_master.R", "Bip001Finger21_master.R",
                                    "Bip001Finger21_master.R", "Bip001Finger31_master.R",
                                    "Bip001Finger41_master.R",
                                ],
                                3: [
                                    "Bip001Finger01.L", "Bip001Finger02.L", "Bip001Finger0.L.001",
                                    "Bip001Finger1.L", "Bip001Finger11.L", "Bip001Finger12.L",
                                    "Bip001Finger1.L.001",
                                    "Bip001Finger2.L", "Bip001Finger21.L", "Bip001Finger22.L",
                                    "Bip001Finger2.L.001",
                                    "Bip001Finger3.L", "Bip001Finger31.L", "Bip001Finger32.L",
                                    "Bip001Finger3.L.001",
                                    "Bip001Finger4.L", "Bip001Finger41.L", "Bip001Finger42.L",
                                    "Bip001Finger4.L.001", "Bip001Finger0.L",
                                    "Bip001Finger01.R", "Bip001Finger02.R", "Bip001Finger0.R.001",
                                    "Bip001Finger1.R", "Bip001Finger11.R", "Bip001Finger12.R",
                                    "Bip001Finger1.R.001",
                                    "Bip001Finger2.R", "Bip001Finger21.R", "Bip001Finger22.R",
                                    "Bip001Finger2.R.001",
                                    "Bip001Finger3.R", "Bip001Finger31.R", "Bip001Finger32.R",
                                    "Bip001Finger3.R.001",
                                    "Bip001Finger4.R", "Bip001Finger41.R", "Bip001Finger42.R",
                                    "Bip001Finger4.R.001", "Bip001Finger0.R",
                                    "Bip001Finger13.L", "Bip001Finger11.L.001",
                                    "Bip001Finger23.L", "Bip001Finger21.L.001",
                                    "Bip001Finger33.L", "Bip001Finger31.L.001",
                                    "Bip001Finger43.L", "Bip001Finger41.L.001",
                                    "Bip001Finger13.R", "Bip001Finger11.R.001",
                                    "Bip001Finger23.R", "Bip001Finger21.R.001",
                                    "Bip001Finger33.R", "Bip001Finger31.R.001",
                                    "Bip001Finger43.R", "Bip001Finger41.R.001",
                                ],
                                4: ["Bip001UpperArm_parent.L", "Bip001UpperArm_ik.L", "Bip001Hand_ik.L"],
                                5: ["Bip001UpperArm_parent.R", "Bip001UpperArm_ik.R", "Bip001Hand_ik.R"],
                                6: ["Bip001UpperArm_fk.L", "Bip001Forearm_fk.L", "Bip001Hand_fk.L"],
                                7: ["Bip001UpperArm_fk.R", "Bip001Forearm_fk.R", "Bip001Hand_fk.R"],
                                8: [
                                    "Bip001UpperArm_tweak.L", "Bip001UpperArm_tweak.L.001",
                                    "Bip001Forearm_tweak.L", "Bip001Forearm_tweak.L.001",
                                    "Bip001Hand_tweak.L",
                                ],
                                9: [
                                    "Bip001UpperArm_tweak.R", "Bip001UpperArm_tweak.R.001",
                                    "Bip001Forearm_tweak.R", "Bip001Forearm_tweak.R.001",
                                    "Bip001Hand_tweak.R",
                                ],
                                10: [
                                    "Bip001Thigh_parent.L", "Bip001Thigh_ik.L",
                                    "Bip001Foot_heel_ik.L", "Bip001Foot_spin_ik.L",
                                    "Bip001Toe0.L", "Bip001Foot_ik.L",
                                ],
                                11: [
                                    "Bip001Thigh_parent.R", "Bip001Thigh_ik.R",
                                    "Bip001Foot_heel_ik.R", "Bip001Foot_spin_ik.R",
                                    "Bip001Toe0.R", "Bip001Foot_ik.R",
                                ],
                                12: ["Bip001Thigh_fk.L", "Bip001Calf_fk.L", "Bip001Foot_fk.L"],
                                13: ["Bip001Thigh_fk.R", "Bip001Calf_fk.R", "Bip001Foot_fk.R"],
                                14: [
                                    "Bip001Thigh_tweak.L", "Bip001Thigh_tweak.L.001",
                                    "Bip001Calf_tweak.L", "Bip001Calf_tweak.L.001",
                                    "Bip001Foot_tweak.L",
                                ],
                                15: [
                                    "Bip001Thigh_tweak.R", "Bip001Thigh_tweak.R.001",
                                    "Bip001Calf_tweak.R", "Bip001Calf_tweak.R.001",
                                    "Bip001Foot_tweak.R",
                                ],
                            }

                            theme_for_groups = {
                                0: 'THEME09', 1: 'THEME04', 2: 'THEME14', 3: 'THEME03',
                                4: 'THEME01', 5: 'THEME01', 6: 'THEME03', 7: 'THEME03',
                                8: 'THEME04', 9: 'THEME04', 10: 'THEME01', 11: 'THEME01',
                                12: 'THEME03', 13: 'THEME03', 14: 'THEME04', 15: 'THEME04',
                            }

                            for group_index, bone_names in bones_to_move.items():
                                theme = theme_for_groups.get(group_index)
                                for bone_name in bone_names:
                                    bone = armature.pose.bones.get(bone_name)
                                    if bone and theme:
                                        bone.color.palette = theme

                            for collection_index, bone_names in bones_to_move.items():
                                bpy.ops.pose.select_all(action='DESELECT')
                                bones_found = False
                                for bone_name in bone_names:
                                    bone = armature.pose.bones.get(bone_name)
                                    if bone:
                                        bone.bone.select = True
                                        bones_found = True

                                if bones_found:
                                    bpy.ops.armature.move_to_collection(
                                        collection_index=collection_index)

                            context.object.data.collections_all["ORG"].is_visible = True

                            if not self.safe_mode_set(context, 'POSE'):
                                return {"CANCELLED"}

                            armature = context.view_layer.objects.active

                            keywords_and_collections = [
                                ("Hair", 16), ("Earrings", 16),
                                ("Piao", 17),
                                ("Skirt", 18), ("Trousers", 18),
                                ("Chest", 19),
                                ("Tail", 19),
                                ("Other", 22),
                                ("Weapon", 22),
                                ("Prop", 22),
                                ("Chibang", 22),

                                ("EyeTracker", 0), ("Eye.L", 0), ("Eye.R", 0),
                            ]

                            for keyword, collection_index in keywords_and_collections:
                                self.select_and_move_bones(
                                    armature, keyword, collection_index)

                            context.object.data.collections_all["ORG"].is_visible = False
                            context.object.data.collections_all["Torso (Tweak)"].is_visible = False
                            context.object.data.collections_all["Arm.L (FK)"].is_visible = False
                            context.object.data.collections_all["Arm.R (FK)"].is_visible = False
                            context.object.data.collections_all["Leg.L (FK)"].is_visible = False
                            context.object.data.collections_all["Leg.R (FK)"].is_visible = False
                            context.object.data.collections_all["Arm.L (Tweak)"].is_visible = False
                            context.object.data.collections_all["Arm.R (Tweak)"].is_visible = False
                            context.object.data.collections_all["Leg.L (Tweak)"].is_visible = False
                            context.object.data.collections_all["Leg.R (Tweak)"].is_visible = False
                            context.object.data.collections_all["Hair"].is_visible = False
                            context.object.data.collections_all["Cloth"].is_visible = False
                            context.object.data.collections_all["Skirt"].is_visible = False
                            context.object.data.collections_all["Chest"].is_visible = False
                            if "Face Panel" in context.object.data.collections_all:
                                context.object.data.collections_all["Face Panel"].is_visible = False

                            if not self.safe_mode_set(context, 'POSE'):
                                return {"CANCELLED"}

                            armature = context.view_layer.objects.active
                            pose_bones = armature.pose.bones

                            theme_assignments = {
                                "EyeTracker": "THEME01", "Eye.L": "THEME09", "Eye.R": "THEME09"
                            }

                            for bone_name, theme in theme_assignments.items():
                                bone = pose_bones.get(bone_name)
                                if bone:
                                    bone.color.palette = theme

                            if rig_armature_object:
                                self.ensure_object_mode(context)

                                if rig_armature_object:
                                    obj = rig_armature_object
                                    if obj and obj.type == 'ARMATURE':
                                        if not self.safe_mode_set(context, 'EDIT'):
                                            return {"CANCELLED"}

                                        armature = obj.data

                                        for bone in armature.edit_bones:
                                            length = (
                                                bone.head - bone.tail).length
                                            if length > 1.0:
                                                direction = (
                                                    bone.tail - bone.head).normalized()
                                                bone.tail = bone.head + direction * 0.5

                                        self.ensure_object_mode(context)

                bpy.ops.object.select_all(action='DESELECT')
                original_armature = bpy.data.objects.get(OrigArmature)
                if original_armature and original_armature.type == 'ARMATURE':
                    bpy.ops.object.select_all(action='DESELECT')
                    original_armature.select_set(True)
                    context.view_layer.objects.active = original_armature
                    original_armature.hide_set(True)

                if original_selected_object_type == 'MESH':
                    original_mesh = bpy.data.objects.get(
                        original_selected_object_name)
                    if original_mesh:
                        context.view_layer.objects.active = original_mesh
                        original_mesh.select_set(True)
                    else:
                        if CharacterMesh:
                            context.view_layer.objects.active = CharacterMesh
                            CharacterMesh.select_set(True)
                else:
                    rig_armature_object = context.scene.objects.get(
                        RigArmature)
                    if rig_armature_object:
                        context.view_layer.objects.active = rig_armature_object
                        rig_armature_object.select_set(True)

                ObjectManager.clear_cache()

                try:
                    bpy.ops.ww.set_driver()
                except RuntimeError:
                    pass

                try:
                    bpy.ops.ww.create_collection()
                except RuntimeError:
                    pass

                cleaned_name = ObjectManager._clean_mesh_name(
                    CharacterMesh.name)
                self.report(
                    {'INFO'}, f"Rigify Armature for '{cleaned_name}' completed")

                return {"FINISHED"}

        except Exception:
            ObjectManager.clear_cache()
            self.ensure_object_mode(context)
            return {"CANCELLED"}
