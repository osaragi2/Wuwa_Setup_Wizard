import bpy
from bpy.types import Operator

from ..core.object_manager import ObjectManager
from ..geometry.mesh_manager import MeshManager


# ========== MESH JOIN ==========

# Joins separated mesh parts with similar names back into a single model
class WW_OT_Join(Operator):
    bl_idname = "ww.join_mesh"
    bl_label = "Join"
    bl_description = "Joins mesh parts with similar suffixes (.001, .002, _Body, _Hair) into a single model."
    bl_options = {"REGISTER", "UNDO"}

    # Requires selected mesh with joinable parts in the scene
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            return False
        return MeshManager.find_joinable_parts(obj) is not None

    # Finds and joins all matching mesh parts into a single object
    def execute(self, context):
        selected_part = context.active_object
        if not selected_part or selected_part.type != 'MESH':
            self.report({'ERROR'}, "Please select a mesh object first")
            return {'CANCELLED'}

        try:
            result = MeshManager.join_mesh(context, selected_part)

            if result['status'] == 'JOINED':
                self.report(
                    {'INFO'}, f"Joined {result['count']} parts into '{result['name']}'")
                return {'FINISHED'}
            elif result['status'] == 'SINGLE':
                self.report({'WARNING'}, "No similar mesh parts found to join")
                return {'CANCELLED'}
            else:
                self.report({'ERROR'}, "Join failed")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Join error: {str(e)}")
            return {'CANCELLED'}
