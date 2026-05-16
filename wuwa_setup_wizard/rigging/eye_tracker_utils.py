import math

import bmesh
import bpy
import mathutils

from ..core.object_manager import ObjectManager


# ========== CONSTANTS ==========

EYE_OFFSET_X = 0.03
MIDPOINT_Y_OFFSET = -0.15
MIDPOINT_Z_SHAPEKEY = -0.015
MIDPOINT_Z_HEADBONE = 0.025
TRACKER_TAIL_Z = 0.03
CIRCLE_SEGMENTS = 32
CIRCLE_RADIUS = 0.1
CAPSULE_INNER_RADIUS = 0.13
CAPSULE_OUTER_RADIUS = 0.16
CAPSULE_SPACING = 0.6
CAPSULE_SEGMENTS = 16
DEFAULT_MIDPOINT = mathutils.Vector((0, -0.1, 1.5))

PUPIL_DRIVER_CONFIG = {
    "Pupil_L": {
        "axis": "x",
        "transform": "LOC_X",
        "expression":
            "max(min((bone_x * 10), 1), 0)"
            " if bone_x > 0 else 0",
    },
    "Pupil_R": {
        "axis": "x",
        "transform": "LOC_X",
        "expression":
            "max(min((-bone_x * 10), 1), 0)"
            " if bone_x < 0 else 0",
    },
    "Pupil_Up": {
        "axis": "y",
        "transform": "LOC_Y",
        "expression":
            "max(min((bone_y * 10), 1), 0)"
            " if bone_y > 0 else 0",
    },
    "Pupil_Down": {
        "axis": "y",
        "transform": "LOC_Y",
        "expression":
            "max(min((-bone_y * 10), 1), 0)"
            " if bone_y < 0 else 0",
    },
}

PUPIL_DRIVER_CONFIG_EYE = {
    "Pupil_L": {
        "axis": "x",
        "transform": "LOC_X",
        "expression":
            "max(min((bone_x * 20), 1), 0)"
            " if bone_x > 0 else 0",
    },
    "Pupil_R": {
        "axis": "x",
        "transform": "LOC_X",
        "expression":
            "max(min((-bone_x * 20), 1), 0)"
            " if bone_x < 0 else 0",
    },
    "Pupil_Up": {
        "axis": "y",
        "transform": "LOC_Y",
        "expression":
            "max(min((bone_y * 20), 1), 0)"
            " if bone_y > 0 else 0",
    },
    "Pupil_Down": {
        "axis": "y",
        "transform": "LOC_Y",
        "expression":
            "max(min((-bone_y * 20), 1), 0)"
            " if bone_y < 0 else 0",
    },
}


# ========== EYE TRACKER UTILITIES ==========

# Shared utilities for EyeTracker bone creation, widget meshes, and drivers
class EyeTrackerUtils:

    # ========== EYE DETECTION ==========

    # Returns mesh objects parented to the given armature via modifiers
    @staticmethod
    def get_meshes_for_armature(armature_obj):
        return [
            obj for obj in bpy.data.objects
            if obj.type == 'MESH' and any(
                m.type == 'ARMATURE' and m.object == armature_obj
                for m in obj.modifiers
            )
        ]

    # Finds left and right eye centers from Pupil_Scale shape key vertices
    @staticmethod
    def find_eye_centers(meshes):
        for mesh in meshes:
            if not mesh.data.shape_keys:
                continue

            eye_mat_indices = [
                i for i, slot in enumerate(mesh.material_slots)
                if slot.material
                and "eye" in slot.material.name.lower()
            ]
            if not eye_mat_indices:
                continue

            pupil_key = mesh.data.shape_keys.key_blocks.get(
                "Pupil_Scale")
            if not pupil_key:
                continue

            basis_key = mesh.data.shape_keys.reference_key
            if not basis_key:
                continue

            left_verts = []
            right_verts = []

            for poly in mesh.data.polygons:
                if poly.material_index not in eye_mat_indices:
                    continue
                for vert_idx in poly.vertices:
                    basis_co = basis_key.data[vert_idx].co
                    pupil_co = pupil_key.data[vert_idx].co
                    if (pupil_co - basis_co).length > 0.0001:
                        world_co = mesh.matrix_world @ basis_co
                        if world_co.x > 0:
                            left_verts.append(world_co)
                        else:
                            right_verts.append(world_co)

            if left_verts and right_verts:
                left_center = sum(
                    left_verts,
                    mathutils.Vector()) / len(left_verts)
                right_center = sum(
                    right_verts,
                    mathutils.Vector()) / len(right_verts)
                return left_center, right_center

        return None, None

    # Calculates eye midpoint from Pupil_Scale or head bone fallback
    @staticmethod
    def find_eye_midpoint(armature_obj, edit_bones, meshes):
        left_center, right_center = (
            EyeTrackerUtils.find_eye_centers(meshes))
        if left_center and right_center:
            midpoint = (left_center + right_center) / 2
            midpoint.y += MIDPOINT_Y_OFFSET
            midpoint.z += MIDPOINT_Z_SHAPEKEY
            return midpoint

        head_bone_name = ObjectManager.get_head_bone(armature_obj)
        head_bone = edit_bones.get(
            head_bone_name) if head_bone_name else None
        if head_bone:
            midpoint = head_bone.head.copy()
            midpoint.y += MIDPOINT_Y_OFFSET
            midpoint.z += MIDPOINT_Z_HEADBONE
            return midpoint

        return DEFAULT_MIDPOINT.copy()

    # ========== BONE CREATION ==========

    # Creates EyeTracker, Eye.L, and Eye.R bones for rigs that lack them
    @staticmethod
    def create_eye_tracker_bones(armature_obj, edit_bones, meshes):
        eye_midpoint = EyeTrackerUtils.find_eye_midpoint(
            armature_obj, edit_bones, meshes)
        if not eye_midpoint:
            return None

        eye_tracker = edit_bones.new("EyeTracker")
        eye_tracker.head = eye_midpoint
        eye_tracker.tail = eye_midpoint + mathutils.Vector(
            (0, 0, TRACKER_TAIL_Z))

        head_bone_name = ObjectManager.get_head_bone(armature_obj)
        parent_bone = edit_bones.get(
            head_bone_name) if head_bone_name else None
        if parent_bone:
            eye_tracker.parent = parent_bone
            eye_tracker.use_connect = False

        y_offset = eye_tracker.tail.y - eye_tracker.head.y
        z_offset = eye_tracker.tail.z - eye_tracker.head.z

        eye_l = edit_bones.new("Eye.L")
        eye_l.head = eye_tracker.head + mathutils.Vector(
            (EYE_OFFSET_X, 0, 0))
        eye_l.tail = eye_l.head + mathutils.Vector(
            (0, y_offset, z_offset))
        eye_l.parent = eye_tracker
        eye_l.use_connect = False

        eye_r = edit_bones.new("Eye.R")
        eye_r.head = eye_tracker.head + mathutils.Vector(
            (-EYE_OFFSET_X, 0, 0))
        eye_r.tail = eye_r.head + mathutils.Vector(
            (0, y_offset, z_offset))
        eye_r.parent = eye_tracker
        eye_r.use_connect = False

        return eye_tracker

    # ========== WIDGET CREATION ==========

    # Creates circular bone widget for eye controls
    @staticmethod
    def create_circle_widget(name, collection=None,
                             location=(0, 0, 0)):
        if name in bpy.data.objects:
            return bpy.data.objects[name]

        mesh = bpy.data.meshes.new(name + "_Mesh")
        obj = bpy.data.objects.new(name, mesh)

        if collection:
            collection.objects.link(obj)
            obj.hide_viewport = True
            obj.hide_render = True
        else:
            bpy.context.collection.objects.link(obj)

        bm = bmesh.new()
        verts = []
        for i in range(CIRCLE_SEGMENTS):
            angle = 2 * math.pi * i / CIRCLE_SEGMENTS
            x = math.cos(angle) * CIRCLE_RADIUS
            y = math.sin(angle) * CIRCLE_RADIUS
            verts.append(bm.verts.new((x, y, 0)))

        for i in range(CIRCLE_SEGMENTS):
            bm.edges.new(
                (verts[i], verts[(i + 1) % CIRCLE_SEGMENTS]))

        bm.to_mesh(mesh)
        bm.free()

        obj.location = location
        obj.rotation_euler[0] = math.pi / 2
        return obj

    # Creates double capsule bone widget for eye tracker control
    @staticmethod
    def create_capsule_widget(name, collection=None):
        if name in bpy.data.objects:
            return bpy.data.objects[name]

        mesh = bpy.data.meshes.new(name + "_Mesh")
        obj = bpy.data.objects.new(name, mesh)

        if collection:
            collection.objects.link(obj)
            obj.hide_viewport = True
            obj.hide_render = True
        else:
            bpy.context.collection.objects.link(obj)

        bm = bmesh.new()
        for radius in [CAPSULE_INNER_RADIUS, CAPSULE_OUTER_RADIUS]:
            loop_verts = []
            left_x = -CAPSULE_SPACING / 2
            right_x = CAPSULE_SPACING / 2

            for i in range(CAPSULE_SEGMENTS + 1):
                angle = (math.pi / 2
                         + math.pi * i / CAPSULE_SEGMENTS)
                x = left_x + math.cos(angle) * radius
                y = math.sin(angle) * radius
                loop_verts.append(bm.verts.new((x, y, 0)))

            for i in range(CAPSULE_SEGMENTS + 1):
                angle = (-math.pi / 2
                         + math.pi * i / CAPSULE_SEGMENTS)
                x = right_x + math.cos(angle) * radius
                y = math.sin(angle) * radius
                loop_verts.append(bm.verts.new((x, y, 0)))

            for i in range(len(loop_verts)):
                bm.edges.new(
                    (loop_verts[i],
                     loop_verts[(i + 1) % len(loop_verts)]))

        bm.to_mesh(mesh)
        bm.free()
        obj.rotation_euler[0] = math.pi / 2
        return obj

    # ========== DRIVER SETUP ==========

    # Sets up Pupil shape key drivers for EyeTracker and Eye.L/R
    @staticmethod
    def setup_pupil_drivers(armature_obj, character_mesh):
        if not character_mesh.data.shape_keys:
            return

        if "EyeTracker" in armature_obj.pose.bones:
            for sk_name, config in PUPIL_DRIVER_CONFIG.items():
                EyeTrackerUtils._add_pupil_driver(
                    armature_obj, character_mesh,
                    sk_name, "EyeTracker", config)

        for suffix in ['.L', '.R']:
            bone_name = "Eye" + suffix
            if bone_name not in armature_obj.pose.bones:
                continue
            for sk_prefix, config in PUPIL_DRIVER_CONFIG_EYE.items():
                EyeTrackerUtils._add_pupil_driver(
                    armature_obj, character_mesh,
                    sk_prefix + suffix, bone_name, config)

    # Adds a single Pupil shape key driver for one bone-shapekey pair
    @staticmethod
    def _add_pupil_driver(armature_obj, character_mesh,
                          shape_key_name, bone_name, config):
        shape_key = character_mesh.data.shape_keys.key_blocks.get(
            shape_key_name)
        if not shape_key:
            return

        data_path = f'key_blocks["{shape_key_name}"].value'
        try:
            character_mesh.data.shape_keys.driver_remove(
                data_path)
        except (TypeError, RuntimeError):
            pass

        driver = shape_key.driver_add('value').driver
        driver.type = 'SCRIPTED'
        var = driver.variables.new()
        var.name = f'bone_{config["axis"]}'
        var.type = 'TRANSFORMS'
        var.targets[0].id = armature_obj
        var.targets[0].bone_target = bone_name
        var.targets[0].transform_type = config['transform']
        var.targets[0].transform_space = 'LOCAL_SPACE'
        driver.expression = config['expression']

    # ========== SHAPE KEY SPLIT ==========

    # Splits bilateral shapekeys into .L and .R versions by X axis
    @staticmethod
    def split_shape_keys(mesh_obj, shape_names):
        if not mesh_obj.data.shape_keys:
            return
        keys = mesh_obj.data.shape_keys.key_blocks
        basis = mesh_obj.data.shape_keys.reference_key
        original_active = bpy.context.view_layer.objects.active
        bpy.context.view_layer.objects.active = mesh_obj
        mesh_obj.select_set(True)
        for source_name in shape_names:
            if source_name not in keys:
                continue
            if f"{source_name}.L" in keys:
                continue
            source_key = keys[source_name]

            mesh_obj.active_shape_key_index = list(keys).index(
                source_key)
            bpy.ops.object.shape_key_add(from_mix=False)
            key_L = mesh_obj.data.shape_keys.key_blocks[-1]
            key_L.name = f"{source_name}.L"
            bpy.ops.object.shape_key_add(from_mix=False)
            key_R = mesh_obj.data.shape_keys.key_blocks[-1]
            key_R.name = f"{source_name}.R"
            for i, vert in enumerate(basis.data):
                base_co = vert.co
                delta = source_key.data[i].co - base_co
                if base_co.x >= 0:
                    key_L.data[i].co = base_co + delta
                    key_R.data[i].co = base_co
                else:
                    key_R.data[i].co = base_co + delta
                    key_L.data[i].co = base_co
        mesh_obj.select_set(False)
        if original_active:
            bpy.context.view_layer.objects.active = original_active
