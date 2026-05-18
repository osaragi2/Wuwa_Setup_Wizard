import os

import bpy
from bpy.props import StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

from ..core.object_manager import ObjectManager
from ..core.shape_key_manager import ShapeKeyManager
from ..core.utils import Utils
from .eye_tracker_utils import EyeTrackerUtils


# Returns addon preferences for persistent storage
def _get_addon_prefs():
    addon_name = '.'.join(__name__.split('.')[:-2])
    prefs = bpy.context.preferences.addons.get(addon_name)
    if prefs:
        return prefs.preferences
    return None


# ========== FACE PANEL IMPORTER ==========

# Imports pre-made face panel from blend file and connects drivers
class WW_OT_ImportFacePanel(Operator, ImportHelper):
    bl_idname = "ww.import_face_panel"
    bl_label = "Import Face Panel"
    bl_description = "Imports a pre-made face panel from a .blend file and connects it to the character."
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".blend"
    filter_glob: StringProperty(default="*.blend", options={"HIDDEN"})

    # Requires mesh with armature and shape keys for driver connections
    @classmethod
    def poll(cls, context):
        active_obj = context.active_object
        if not active_obj:
            return False
        if active_obj.type == "ARMATURE":
            return True
        if active_obj.type == "MESH":
            if ObjectManager.get_armature(active_obj) is not None:
                return True
        return bool(
            active_obj.name.startswith("Face Panel")
            or (active_obj.users_collection and any(
                "Face Panel" in c.name
                for c in active_obj.users_collection)))

    # Finds character armature and mesh from Face Panel object
    @staticmethod
    def get_character_from_face_panel(obj):

        if obj.name.startswith("Face Panel"):
            if hasattr(obj, 'constraints'):
                for con in obj.constraints:
                    if (con.type == 'CHILD_OF'
                            and con.target
                            and con.target.type == 'ARMATURE'):
                        armature = con.target
                        mesh = ObjectManager.get_mesh_from_armature(
                            armature)
                        return mesh, armature

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
                    armature = ObjectManager.get_armature(mesh_obj)
                    return mesh_obj, armature

        for o in bpy.data.objects:
            if o.name.startswith("Face Panel"):
                if hasattr(o, 'constraints'):
                    for con in o.constraints:
                        if (con.type == 'CHILD_OF'
                                and con.target
                                and con.target.type == 'ARMATURE'):
                            armature = con.target
                            mesh = (
                                ObjectManager
                                .get_mesh_from_armature(armature))
                            return mesh, armature

        return None, None

    # Validates that filepath points to a valid blend file
    def is_valid_blend_file(self, filepath):
        try:
            with bpy.data.libraries.load(filepath, link=False) as (src_data, _):
                return "Face Panel" in src_data.collections
        except Exception:
            return False

    # Invokes operator with file browser or modal dialog
    def invoke(self, context, event):
        active_obj = context.active_object

        if active_obj:
            mesh = None
            if active_obj.type == "MESH":
                is_panel = (
                    active_obj.name.startswith("Face Panel")
                    or (active_obj.users_collection and any(
                        "Face Panel" in c.name
                        for c in active_obj.users_collection)))
                if is_panel:
                    mesh, _ = self.get_character_from_face_panel(
                        active_obj)
                else:
                    mesh = active_obj
            elif active_obj.type == "ARMATURE":
                mesh = ObjectManager.get_mesh_from_armature(
                    active_obj)

            if mesh and mesh.get("face_panel_assigned", False):
                return self.execute(context)

        addon_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))
        bundled_path = os.path.join(
            addon_dir, "face_panel", "face_panel_shapes.blend")

        if (os.path.exists(bundled_path)
                and self.is_valid_blend_file(bundled_path)):
            self.filepath = bundled_path
            return self.execute(context)

        prefs = _get_addon_prefs()
        if prefs and prefs.face_panel_file_path:
            saved_path = prefs.face_panel_file_path
            if (os.path.exists(saved_path)
                    and self.is_valid_blend_file(saved_path)):
                self.filepath = saved_path
                return self.execute(context)

        if (hasattr(context.scene, 'ww_properties')
                and context.scene.ww_properties
                .face_panel_file_path):
            legacy_path = (
                context.scene.ww_properties
                .face_panel_file_path)
            if (os.path.exists(legacy_path)
                    and self.is_valid_blend_file(
                        legacy_path)):
                self.filepath = legacy_path
                return self.execute(context)

        return ImportHelper.invoke(self, context, event)

    # Gets world position of a bone
    def get_bone_world_pos(self, armature, bone_name):
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except RuntimeError:
            pass

        bone = armature.data.bones.get(bone_name)
        if bone:
            return bone.head_local.copy()

        return None

    # Validates mesh and armature for face panel setup
    def validate_mesh_and_armature(self, context, mesh, armature, active_obj):
        if not mesh.data.shape_keys:
            self.restore_initial_state(context, active_obj)
            return False
        return True

    # Restores initial selection state after operations
    def restore_initial_state(self, context, active_obj):
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except RuntimeError:
            pass
        bpy.ops.object.select_all(action="DESELECT")
        if active_obj:
            active_obj.select_set(True)
            context.view_layer.objects.active = active_obj

    # Imports face panel collection from blend file
    def import_collection(self, context):
        collection_name = "Face Panel"
        filepath = self.filepath

        if not filepath or not os.path.exists(filepath):
            return None, None

        with bpy.data.libraries.load(filepath, link=False) as (src_data, tgt_data):
            if collection_name in src_data.collections:
                tgt_data.collections = [collection_name]
            else:
                return None, None

        imported_collection = next(
            (coll for coll in tgt_data.collections if coll), None)
        if not imported_collection:
            return None, None

        bpy.context.scene.collection.children.link(imported_collection)

        face_panel = next(
            (obj for obj in imported_collection.objects
             if obj.name.startswith("Face Panel")),
            None)
        if not face_panel:
            return None, None

        bpy.context.view_layer.objects.active = face_panel
        face_panel.select_set(True)
        face_panel.lock_scale = [False, False, False]
        face_panel.scale = (0.2, 0.2, 0.2)
        face_panel.lock_scale = [True, True, True]

        panel_armature = next(
            (obj for obj in imported_collection.objects if obj.type == "ARMATURE"), None)
        if not panel_armature:
            return None, None

        prefs = _get_addon_prefs()
        if prefs:
            prefs.face_panel_file_path = filepath
            try:
                bpy.ops.wm.save_userpref()
            except Exception:
                pass

        if hasattr(context.scene, 'ww_properties'):
            context.scene.ww_properties.face_panel_file_path = (
                filepath)

        return face_panel, panel_armature

    # Positions face panel at head location
    def position_panel(self, panel, armature, head_pos):
        y = 0.0
        x = head_pos.x + 0.1
        z = head_pos.z - 0.1

        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.view_layer.objects.active = panel
        panel.select_set(True)
        panel.location = (x, y, z)

    # Adds single driver to shape key from bone transform
    def add_driver(self, mesh, armature, shape_key, bone_name, expression, transform_type):
        shape_key_block = mesh.data.shape_keys.key_blocks.get(shape_key)
        if not shape_key_block or (hasattr(shape_key_block, "driver") and shape_key_block.driver):
            return

        driver = shape_key_block.driver_add("value").driver
        variable = driver.variables.new()
        variable.name = "bone"
        variable.type = "TRANSFORMS"
        variable.targets[0].id = armature
        variable.targets[0].bone_target = bone_name
        variable.targets[0].transform_space = "LOCAL_SPACE"
        variable.targets[0].transform_type = transform_type

        driver.type = "SCRIPTED"
        driver.expression = expression

    # Adds driver with two bone inputs for combined control
    def add_dual_driver(self, mesh, armature, shape_key, bone1, bone2, expression, transform_type):
        shape_key_block = mesh.data.shape_keys.key_blocks.get(shape_key)
        if not shape_key_block or (hasattr(shape_key_block, "driver") and shape_key_block.driver):
            return

        driver = shape_key_block.driver_add("value").driver

        var1 = driver.variables.new()
        var1.name = "bone_001"
        var1.type = "TRANSFORMS"
        var1.targets[0].id = armature
        var1.targets[0].bone_target = bone1
        var1.targets[0].transform_space = "LOCAL_SPACE"
        var1.targets[0].transform_type = transform_type

        var2 = driver.variables.new()
        var2.name = "bone"
        var2.type = "TRANSFORMS"
        var2.targets[0].id = armature
        var2.targets[0].bone_target = bone2
        var2.targets[0].transform_space = "LOCAL_SPACE"
        var2.targets[0].transform_type = transform_type

        driver.type = "SCRIPTED"
        driver.expression = expression

    # Sets up all face panel drivers for shape keys
    def setup_drivers(self, context, mesh, armature):
        if not armature:
            return

        bpy.context.view_layer.objects.active = mesh

        driver_configs = [
            ("Aa", "m.A", "bone * 5", "LOC_X"),
            ("A", "m.AA", "bone * 5", "LOC_X"),
            ("E", "m.E", "bone * 5", "LOC_X"),
            ("I", "m.I", "bone * 5", "LOC_X"),
            ("O", "m.O", "bone * 5", "LOC_X"),
            ("U", "m.U", "bone * 5", "LOC_X"),
            ("P_M_Up_Add", "fp.m.pos.sel", "bone * 5", "LOC_Y"),
            ("P_M_Down_Add", "fp.m.pos.sel", "bone * -5", "LOC_Y"),
            ("P_M_RMove_Add", "fp.m.pos.sel", "bone * -5", "LOC_X"),
            ("P_M_LMove_Add", "fp.m.pos.sel", "bone * 5", "LOC_X"),
            ("P_M_L_Add", "lip.cor.pos.sel.r", "bone * 5", "LOC_X"),
            ("P_M_R_Add", "lip.cor.pos.sel.l", "bone * -5", "LOC_X"),
            ("M_Smile_L", "lip.cor.pos.sel.r", "bone * 5", "LOC_Y"),
            ("M_Smile_R", "lip.cor.pos.sel.l", "bone * 5", "LOC_Y"),
            ("M_Ennui_L", "lip.cor.pos.sel.r", "bone * -5", "LOC_Y"),
            ("M_Ennui_R", "lip.cor.pos.sel.l", "bone * -5", "LOC_Y"),
            ("M_Laugh", "x1", "bone * 5", "LOC_X"),
            ("M_Scared", "x2", "bone * 5", "LOC_X"),
            ("M_ScaredTooth", "x3", "bone * 5", "LOC_X"),
            ("M_Anger", "x4", "bone * 5", "LOC_X"),
            ("M_Nutcracker", "x5", "bone * 5", "LOC_X"),
            ("M_O", "x6", "bone * 5", "LOC_X"),
            ("B_AH_R", "doubt.1", "bone * 5", "LOC_X"),
            ("B_AH_L", "doubt.2", "bone * 5", "LOC_X"),
            ("B_Cheerful", "b.happy", "bone * 5", "LOC_X"),
            ("B_Flat", "b.flat", "bone * 5", "LOC_X"),
            ("B_Inside_Add", "b.close", "bone * 5", "LOC_X"),
            ("B_Anger", "fp.brow.sel", "bone * -5", "LOC_X"),
            ("B_Sad", "fp.brow.sel", "bone * 5", "LOC_X"),
            ("B_Up_Add", "fp.brow.sel", "bone * 5", "LOC_Y"),
            ("B_Down_Add", "fp.brow.sel", "bone * -5", "LOC_Y"),
            ("E_Insipid", "e.ji", "bone * 5", "LOC_X"),
            ("E_Blephar", "e.lowlid", "bone * 5", "LOC_X"),
            ("E_Focus", "e.focus", "bone * 5", "LOC_X"),
            ("E_Stare", "e.wide", "bone * 5", "LOC_X"),
            ("E_Smile_R", "e.wink.up.r", "bone * 5", "LOC_X"),
            ("E_Smile_L", "e.wink.up.l", "bone * 5", "LOC_X"),
            ("E_Anger", "eye.pos", "bone * -5", "LOC_X"),
            ("E_Sad", "eye.pos", "bone * 5", "LOC_X"),
            ("E_Close", "eye.pos", "bone * -5", "LOC_Y"),
        ]

        dual_driver_configs = [
            ("E_Smile_L", "eye.pos", "e.wink.up.l",
             "max(bone_001 * 5, bone * 5)", "LOC_Y"),
            ("E_Smile_R", "eye.pos", "e.wink.up.r",
             "max(bone_001 * 5, bone * 5)", "LOC_Y"),
        ]

        try:
            for shape_key, bone_name, expression, transform_type in driver_configs:
                self.add_driver(mesh, armature, shape_key,
                                bone_name, expression, transform_type)

            for shape_key, bone1, bone2, expression, transform_type in dual_driver_configs:
                self.add_dual_driver(
                    mesh, armature, shape_key, bone1, bone2, expression, transform_type)

            context.evaluated_depsgraph_get().update()
        except Exception:
            pass

    # Imports face panel from blend file, positions it, and sets up shape key drivers
    def execute(self, context):
        active_obj = context.active_object
        selected_obj = context.active_object
        initial_mode = context.mode

        if initial_mode == 'POSE':
            bpy.ops.object.mode_set(mode='OBJECT')

        mesh = None
        armature = None

        if selected_obj.type == "ARMATURE":
            is_panel_armature = (
                selected_obj.name.startswith("Face Panel")
                or (selected_obj.users_collection and any(
                    "Face Panel" in c.name
                    for c in selected_obj.users_collection))
            )
            if is_panel_armature:
                mesh, armature = self.get_character_from_face_panel(
                    selected_obj)
            else:
                armature = selected_obj
                mesh = ObjectManager.get_mesh_from_armature(armature)
            if not mesh:
                self.restore_initial_state(context, active_obj)
                return {"CANCELLED"}
        elif selected_obj.type == "MESH":
            is_panel_mesh = (
                selected_obj.name.startswith("Face Panel")
                or (selected_obj.users_collection and any(
                    "Face Panel" in c.name
                    for c in selected_obj.users_collection)))
            if is_panel_mesh:
                mesh, armature = self.get_character_from_face_panel(
                    selected_obj)
                if not mesh or not armature:
                    self.restore_initial_state(
                        context, active_obj)
                    return {"CANCELLED"}
            else:
                mesh = selected_obj
                armature = ObjectManager.get_armature(mesh)
                if not self.validate_mesh_and_armature(
                        context, mesh, armature, active_obj):
                    return {"CANCELLED"}
        else:
            mesh, armature = self.get_character_from_face_panel(selected_obj)
            if mesh and not self.validate_mesh_and_armature(context, mesh, armature, active_obj):
                return {"CANCELLED"}

        if not armature or not mesh:
            self.restore_initial_state(context, active_obj)
            return {"CANCELLED"}

        cleaned_name = ObjectManager._clean_mesh_name(mesh.name)

        if mesh.get("face_panel_assigned", False):
            panel_armature_name = mesh.get("face_panel_armature")
            if panel_armature_name:
                panel_armature = bpy.data.objects.get(panel_armature_name)
                if panel_armature:
                    ShapeKeyManager.clear_shape_key_drivers(
                        mesh, ShapeKeyManager.protected_shape_keys)
                    self.setup_drivers(context, mesh, panel_armature)
                    # Rebuild Pupil drivers if rig armature has EyeTracker (post-Rigify)
                    rig_armature = ObjectManager.get_armature(mesh)
                    if rig_armature and "EyeTracker" in rig_armature.pose.bones:
                        EyeTrackerUtils.setup_pupil_drivers(rig_armature, mesh)

                    msg = (f"Face Panel drivers reset for '{cleaned_name}'")
                    self.report({'INFO'}, msg)
                    if initial_mode == 'POSE':
                        context.view_layer.objects.active = (
                            active_obj)
                        bpy.ops.object.mode_set(mode='POSE')
                    else:
                        self.restore_initial_state(
                            context, active_obj)
                    return {'FINISHED'}
                else:
                    del mesh["face_panel_assigned"]
                    if "face_panel_armature" in mesh:
                        del mesh["face_panel_armature"]
            else:
                del mesh["face_panel_assigned"]

        armature_was_hidden = armature.hide_get()
        if armature_was_hidden:
            armature.hide_set(False)

        cached_xform = Utils.cache_and_reset_transform(armature)

        try:
            bpy.ops.object.mode_set(mode="OBJECT")
            head_bone = ObjectManager.get_head_bone(armature)
            head_pos = self.get_bone_world_pos(
                armature, head_bone) if head_bone else None
            if not head_pos:
                Utils.restore_transform(armature, cached_xform)
                if armature_was_hidden:
                    armature.hide_set(True)
                self.restore_initial_state(context, active_obj)
                return {"CANCELLED"}

            face_panel, panel_armature = self.import_collection(context)
            if not face_panel or not panel_armature:
                Utils.restore_transform(armature, cached_xform)
                if armature_was_hidden:
                    armature.hide_set(True)
                self.restore_initial_state(context, active_obj)
                return {"CANCELLED"}

            for coll in face_panel.users_collection:
                if (coll.name == "Face Panel"
                        or coll.name.startswith("Face Panel.")):
                    coll.name = f"Face Panel {cleaned_name}"
                    break

            face_panel.name = f"Face Panel {cleaned_name}"

            self.position_panel(face_panel, armature, head_pos)

            child_of = face_panel.constraints.new("CHILD_OF")
            child_of.target = armature
            child_of.subtarget = head_bone

            bpy.ops.object.mode_set(mode="OBJECT")
            context.view_layer.objects.active = face_panel
            bpy.ops.constraint.childof_set_inverse(
                constraint=child_of.name, owner="OBJECT")

            mesh["face_panel_armature"] = panel_armature.name

            ShapeKeyManager.clear_shape_key_drivers(
                mesh, ShapeKeyManager.protected_shape_keys)
            self.setup_drivers(context, mesh, panel_armature)
            # Rebuild Pupil drivers if rig armature has EyeTracker (post-Rigify)
            rig_armature = ObjectManager.get_armature(mesh)
            if rig_armature and "EyeTracker" in rig_armature.pose.bones:
                EyeTrackerUtils.setup_pupil_drivers(rig_armature, mesh)

            mesh["face_panel_assigned"] = True

            shapes_coll_name = f"Face Panel {cleaned_name}"
            shapes_coll = bpy.data.collections.get(shapes_coll_name)
            if shapes_coll:
                for obj_in_coll in list(shapes_coll.objects):
                    if (obj_in_coll != face_panel
                            and obj_in_coll != panel_armature):
                        bpy.data.objects.remove(
                            obj_in_coll, do_unlink=True)
                for child_coll in list(shapes_coll.children):
                    bpy.data.collections.remove(
                        child_coll, do_unlink=True)
                scene_coll = context.scene.collection
                for keep_obj in [face_panel, panel_armature]:
                    if keep_obj and keep_obj.name in shapes_coll.objects:
                        shapes_coll.objects.unlink(keep_obj)
                        if keep_obj.name not in scene_coll.objects:
                            scene_coll.objects.link(keep_obj)
                bpy.data.collections.remove(
                    shapes_coll, do_unlink=True)

            self.report(
                {'INFO'},
                f"Import Face Panel for"
                f" '{cleaned_name}' completed.")

        finally:
            Utils.restore_transform(armature, cached_xform)
            if armature_was_hidden:
                armature.hide_set(True)

        try:
            bpy.ops.ww.create_collection()
        except RuntimeError:
            pass

        self.restore_initial_state(context, active_obj)
        if initial_mode == 'POSE':
            bpy.ops.object.mode_set(mode='POSE')
        return {"FINISHED"}
