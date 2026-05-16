import bpy
from bpy.types import Operator

from ..core.driver_manager import DriverManager
from ..core.object_manager import ObjectManager
from ..core.utils import Utils
from ..core.viewport_manager import ViewportManager
from ..geometry.geometry_manager import GeometryManager
from ..material.material_manager import MaterialManager

FACE_PANEL_PREFIXES = ["Face Panel"]


# ========== DRIVER SETUP ==========

# Resets position and constraints for light control objects
class WW_OT_SetDriver(Operator):
    bl_idname = "ww.set_driver"
    bl_label = "Set Driver"
    bl_description = "Resets the position and constraints for the light control objects."
    bl_options = {'REGISTER', 'UNDO'}

    # Requires mesh, armature, or shader helper object to be selected
    @classmethod
    def poll(cls, context):
        active_obj = context.active_object
        if not active_obj:
            return False
        if active_obj.type == 'ARMATURE':
            return True
        if active_obj.type == 'MESH':
            return True
        if active_obj.type in {'EMPTY', 'LIGHT'}:
            ww_prefixes = ["Light Direction",
                           "Head Origin", "Head Forward", "Head Right"]
            return any(
                active_obj.name.startswith(prefix)
                for prefix in ww_prefixes)
        return False

    # Configures helper object drivers for all processable meshes
    def execute(self, context):
        try:
            bpy.ops.outliner.orphans_purge()
        except RuntimeError:
            pass

        active_obj = context.active_object
        if not active_obj:
            self.report({'ERROR'}, "No object selected")
            return {'CANCELLED'}

        is_face_panel = any(
            active_obj.name.startswith(p)
            for p in FACE_PANEL_PREFIXES)
        if not is_face_panel and active_obj.users_collection:
            is_face_panel = any(
                "Face Panel" in c.name
                for c in active_obj.users_collection)

        if is_face_panel:
            return self._reset_face_panel_position(
                context, active_obj)

        mesh = None
        armature = None
        gw_prefixes = ["Head Controller", "Main Light"]

        if active_obj.type == 'MESH':
            if any(active_obj.name.startswith(prefix)
                   for prefix in gw_prefixes):
                mesh = ObjectManager.get_mesh_from_helper_object(
                    active_obj)
                if not mesh:
                    self.report(
                        {'ERROR'},
                        "Could not find associated mesh"
                        " from this helper object")
                    return {'CANCELLED'}
                armature = ObjectManager.get_armature(mesh)
                if not armature:
                    self.report(
                        {'ERROR'},
                        "No armature found for this mesh")
                    return {'CANCELLED'}
            else:
                mesh = active_obj
                armature = ObjectManager.get_armature(mesh)
                if not MaterialManager.has_ww_materials(mesh):
                    self.report(
                        {'ERROR'},
                        "Please apply Wuthering Waves shader first")
                    return {'CANCELLED'}
                if not armature:
                    self.report(
                        {'ERROR'},
                        "No armature found for this mesh")
                    return {'CANCELLED'}
        elif active_obj.type == 'ARMATURE':
            armature = active_obj
            mesh = ObjectManager.get_mesh_from_armature(armature)
            if not mesh:
                self.report(
                    {'ERROR'},
                    "No mesh found for this armature")
                return {'CANCELLED'}
        elif active_obj.type in {'EMPTY', 'LIGHT'}:
            mesh = ObjectManager.get_mesh_from_helper_object(
                active_obj)
            if not mesh:
                self.report(
                    {'ERROR'},
                    "Could not find associated mesh"
                    " from this helper object")
                return {'CANCELLED'}
            armature = ObjectManager.get_armature(mesh)
            if not armature:
                self.report(
                    {'ERROR'},
                    "No armature found for this mesh")
                return {'CANCELLED'}
        else:
            self.report(
                {'ERROR'},
                "Please select a mesh, armature,"
                " or helper object")
            return {'CANCELLED'}

        cached_xform = Utils.cache_and_reset_transform(armature)
        success = False
        error_msg = None
        try:
            success = DriverManager.set_drivers(mesh)
        except Exception as e:
            error_msg = str(e)
        finally:
            Utils.restore_transform(armature, cached_xform)

        if success:
            cleaned_name = ObjectManager._clean_mesh_name(
                mesh.name)
            self.report(
                {'INFO'},
                f"Light drivers successfully configured for '{cleaned_name}'")
            return {'FINISHED'}
        if error_msg:
            self.report(
                {'ERROR'},
                f"Driver setup failed: {error_msg}")
        else:
            self.report({'ERROR'}, "Driver setup failed")
        return {'CANCELLED'}

    # Resets Face Panel to correct position beside the head bone
    def _reset_face_panel_position(self, context, face_panel):
        armature = None
        head_bone_name = None
        child_of_con = None

        if hasattr(face_panel, 'constraints'):
            for con in face_panel.constraints:
                if (con.type == 'CHILD_OF'
                        and con.target
                        and con.target.type == 'ARMATURE'):
                    armature = con.target
                    head_bone_name = con.subtarget
                    child_of_con = con
                    break

        if not armature or not head_bone_name:
            self.report(
                {'ERROR'},
                "Could not find character armature"
                " from Face Panel constraint")
            return {'CANCELLED'}

        cached_xform = Utils.cache_and_reset_transform(
            armature)

        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except RuntimeError:
            pass

        try:
            bone = armature.data.bones.get(head_bone_name)
            if not bone:
                self.report(
                    {'ERROR'},
                    f"Head bone '{head_bone_name}'"
                    f" not found")
                return {'CANCELLED'}

            head_pos = bone.head_local.copy()
            x = head_pos.x + 0.1
            y = 0.0
            z = head_pos.z - 0.1

            face_panel.location = (x, y, z)

            context.view_layer.objects.active = face_panel
            face_panel.select_set(True)
            bpy.ops.constraint.childof_set_inverse(
                constraint=child_of_con.name,
                owner="OBJECT")

            cleaned_name = face_panel.name.replace(
                "Face Panel ", "")
            self.report(
                {'INFO'},
                f"Face Panel position reset"
                f" for '{cleaned_name}'")
            return {'FINISHED'}

        except Exception as e:
            print(f"[WuWa] Face Panel reset error: {e}")
            self.report(
                {'WARNING'},
                f"Face Panel reset failed: {e}")
            return {'CANCELLED'}
        finally:
            Utils.restore_transform(armature, cached_xform)


# ========== ANIMATION MODE ==========

# Toggles Animation Mode to reduce viewport lag
class WW_OT_ToggleAnimationMode(Operator):
    bl_idname = "ww.toggle_animation_mode"
    bl_label = "Toggle Animation Mode"
    bl_description = "Toggle Animation Mode to reduce lag during animation by bypassing shader nodes."
    bl_options = {'REGISTER', 'UNDO'}

    # Requires at least one mesh with shader materials in the scene
    @classmethod
    def poll(cls, context):
        return len(ObjectManager.get_processable_meshes()) > 0

    # Toggles animation mode between shader output and emission for all meshes
    def execute(self, context):
        try:
            from ..geometry.effect_manager import EffectManager
            from ..ui.ui_cache import UICache

            current_state = EffectManager.get_animation_mode_state()
            new_state = not current_state

            count = EffectManager.toggle_animation_mode(new_state)
            UICache.clear()

            if count > 0:
                state_text = "enabled" if new_state else "disabled"
                self.report({'INFO'}, f"Animation Mode {state_text}")
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, "No materials processed")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Animation mode error: {str(e)}")
            return {'CANCELLED'}


# ========== GEOMETRY NODES ==========

# Re-initializes Light Vectors and Outline modifiers
class WW_OT_SetupGeometryNodes(Operator):
    bl_idname = "ww.setup_geometry_nodes"
    bl_label = "Set Up Geometry Nodes"
    bl_description = "Re-initializes Light Vectors and Outline modifiers based on the current outline mode."
    bl_options = {'REGISTER', 'UNDO'}

    # Requires mesh or armature with shader materials applied
    @classmethod
    def poll(cls, context):
        active_obj = context.active_object
        if not active_obj:
            return False
        if active_obj.type == 'MESH':
            return MaterialManager.has_ww_materials(active_obj)
        elif active_obj.type == 'ARMATURE':
            mesh = ObjectManager.get_mesh_from_armature(active_obj)
            return mesh and MaterialManager.has_ww_materials(mesh)
        return False

    # Removes and recreates vector and outline geometry node modifiers

    def execute(self, context):
        active_obj = context.active_object
        mesh = None

        if active_obj.type == 'MESH':
            mesh = active_obj
        elif active_obj.type == 'ARMATURE':
            mesh = ObjectManager.get_mesh_from_armature(active_obj)

        if not mesh:
            self.report({'ERROR'}, "No valid mesh found")
            return {'CANCELLED'}

        try:
            mode = GeometryManager.reset_geometry_nodes(mesh)
            cleaned_name = ObjectManager._clean_mesh_name(mesh.name)
            self.report(
                {'INFO'}, f"Geometry Nodes reset for '{cleaned_name}' (Mode: {mode})")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Geometry Nodes setup failed: {str(e)}")
            return {'CANCELLED'}
