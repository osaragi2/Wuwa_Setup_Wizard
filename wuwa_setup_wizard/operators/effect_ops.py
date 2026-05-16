import bpy
from bpy.types import Operator

from ..core.object_manager import ObjectManager
from ..geometry.effect_manager import EffectManager
from ..material.material_manager import MaterialManager


# ========== OUTLINE TOGGLE ==========

# Toggles character outline visibility
class WW_OT_ToggleOutlines(Operator):
    bl_idname = "ww.toggle_outlines"
    bl_label = "Toggle Outlines"
    bl_description = "Toggles the character's outline on or off."
    bl_options = {'REGISTER', 'UNDO'}

    # Toggles outline modifiers on or off and updates the UI cache
    def execute(self, context):
        try:
            from ..ui.ui_cache import UICache
            current_state = EffectManager.get_outlines_state()
            new_state = not current_state
            EffectManager.toggle_outlines(new_state)
            UICache.clear()
            state_text = "enabled" if new_state else "disabled"
            self.report({'INFO'}, f"Outlines {state_text}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to toggle outlines: {str(e)}")
            return {'CANCELLED'}


# ========== TWO-COLORED EYES ==========

# Toggles heterochromia effect
class WW_OT_ToggleTwoColoredEyes(Operator):
    bl_idname = "ww.toggle_two_colored_eyes"
    bl_label = "Toggle Two-colored Eyes"
    bl_description = "Toggles the effect for two-colored eyes (heterochromia)."
    bl_options = {'REGISTER', 'UNDO'}

    # Toggles heterochromia UV mapping on the active mesh
    def execute(self, context):
        mesh = context.active_object

        if not mesh or mesh.type != 'MESH':
            self.report({'ERROR'}, "Please select a mesh object first")
            return {'CANCELLED'}

        if not MaterialManager.has_ww_materials(mesh):
            self.report({'ERROR'}, "Please apply Wuthering Waves shader first")
            return {'CANCELLED'}

        try:
            current_state = EffectManager.get_two_colored_eyes_state(mesh)
            new_state = not current_state
            if EffectManager.toggle_two_colored_eyes(mesh, new_state):
                cleaned_name = ObjectManager._clean_mesh_name(mesh.name)
                state_text = "enabled" if new_state else "disabled"
                self.report(
                    {'INFO'}, f"Two-colored eyes {state_text} for '{cleaned_name}'")
                return {'FINISHED'}
            self.report(
                {'ERROR'}, "Effect toggle failed - Eye material not found")
            return {'CANCELLED'}
        except Exception as e:
            self.report(
                {'ERROR'}, f"Failed to toggle two-colored eyes: {str(e)}")
            return {'CANCELLED'}


# ========== TACET MARK ANIMATION ==========

# Toggles Tacet Mark sparkling animation
class WW_OT_AnimateTacetMark(Operator):
    bl_idname = "ww.animate_tacet_mark"
    bl_label = "Animate Tacet Mark"
    bl_description = "Toggles the sparkling animation effect for the Tacet Mark."
    bl_options = {'REGISTER', 'UNDO'}

    # Toggles the Tacet Mark sparkling driver with the configured expression
    def execute(self, context):
        mesh = context.active_object
        if not mesh or mesh.type != 'MESH':
            self.report({'ERROR'}, "Please select a mesh object first")
            return {'CANCELLED'}

        if not EffectManager.has_tacet_mark(mesh):
            self.report({'ERROR'}, "No Tacet Mark material found on this mesh")
            return {'CANCELLED'}

        try:
            expression = context.scene.ww_properties.tacet_mark_driver_expression
            if not expression.strip():
                self.report({'ERROR'}, "Driver expression is empty")
                return {'CANCELLED'}

            current_state = EffectManager.get_tacet_animation_state(mesh)
            if EffectManager.toggle_tacet_animation(mesh, expression):
                cleaned_name = ObjectManager._clean_mesh_name(mesh.name)
                new_state = not current_state
                state_text = "enabled" if new_state else "disabled"
                self.report(
                    {'INFO'}, f"Tacet Mark animation {state_text} for '{cleaned_name}'")
                return {'FINISHED'}
            self.report({'ERROR'}, "Failed to toggle Tacet Mark animation")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Tacet Mark animation error: {str(e)}")
            return {'CANCELLED'}


# ========== TACET MARK CREATION ==========

# Adds Tacet Mark via 3-stage vertex selection and UV editing workflow
class WW_OT_AddTacetMark(Operator):
    bl_idname = "ww.add_tacet_mark"
    bl_label = "Add Tacet Mark"
    bl_description = "Add Tacet Mark by selecting vertices, assigning UV coordinates, and completing the setup."
    bl_options = {'REGISTER', 'UNDO'}

    # Requires mesh with shader materials and no existing Tacet Mark, or active stage
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            return False
        stage = obj.get("ww_tacet_mark_stage", 0)
        if stage > 0:
            return True
        if not MaterialManager.has_ww_materials(obj):
            return False
        for slot in obj.material_slots:
            if slot.material and "Tacet Mark" in slot.material.name:
                return False
        return True

    # Routes to the appropriate stage handler based on current progress
    def execute(self, context):
        obj = context.active_object
        stage = obj.get("ww_tacet_mark_stage", 0)

        if stage == 0:
            return self._stage1_start(context, obj)
        elif stage == 1:
            return self._stage2_uv_editing(context, obj)
        else:
            return self._stage3_complete(context, obj)

    # ========== STAGE 1: START ==========

    # Separates mesh by material slots and prepares for vertex selection
    def _stage1_start(self, context, mesh):
        mesh["ww_tacet_mark_stage"] = 1
        mesh["ww_tacet_mark_original"] = mesh.name

        armature = mesh.find_armature()
        if armature:
            armature.hide_set(True)
            mesh["ww_tacet_mark_armature"] = armature.name

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.separate(type='MATERIAL')
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if hasattr(space, 'shading'):
                        space.shading.type = 'SOLID'
                        break

        from ..ui.ui_cache import UICache
        UICache.clear()

        self.report({'INFO'}, "Select a mesh part, enter Edit Mode, select vertices, then click 'Tacet Mark [UV]'")
        return {'FINISHED'}

    # ========== STAGE 2: UV EDITING ==========

    # Duplicates selected vertices, assigns Tacet Mark material, opens UV editor
    def _stage2_uv_editing(self, context, mesh):
        cleaned_name = ObjectManager._clean_mesh_name(mesh.name)

        tacet_mat_name = f"Tacet Mark {cleaned_name}"
        tacet_source = bpy.data.materials.get(tacet_mat_name)
        if not tacet_source:
            tacet_source = bpy.data.materials.get("Tacet Mark")
            if tacet_source:
                tacet_source = tacet_source.copy()
                tacet_source.name = tacet_mat_name
            else:
                del mesh["ww_tacet_mark_stage"]
                if "ww_tacet_mark_original" in mesh:
                    del mesh["ww_tacet_mark_original"]
                bpy.ops.object.mode_set(mode='OBJECT')
                self.report({'ERROR'}, "Tacet Mark material not found in shader")
                return {'CANCELLED'}

        try:
            bpy.ops.mesh.duplicate()
            bpy.ops.mesh.separate(type='SELECTED')
        except RuntimeError:
            del mesh["ww_tacet_mark_stage"]
            if "ww_tacet_mark_original" in mesh:
                del mesh["ww_tacet_mark_original"]
            self.report({'ERROR'}, "No vertices selected for Tacet Mark")
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='OBJECT')

        tacet_obj = None
        for obj in context.selected_objects:
            if obj != mesh and obj.type == 'MESH':
                tacet_obj = obj
                break

        if not tacet_obj:
            del mesh["ww_tacet_mark_stage"]
            if "ww_tacet_mark_original" in mesh:
                del mesh["ww_tacet_mark_original"]
            self.report({'ERROR'}, "Failed to separate selection")
            return {'CANCELLED'}

        tacet_obj.data.materials.clear()
        tacet_obj.data.materials.append(tacet_source)

        from ..material.shader_importer import ShaderImporter
        ShaderImporter._configure_material_settings(tacet_source, 'Tacet Mark')

        tacet_obj["ww_tacet_mark_stage"] = 2
        tacet_obj["ww_tacet_mark_original"] = mesh.name
        del mesh["ww_tacet_mark_stage"]
        if "ww_tacet_mark_original" in mesh:
            del mesh["ww_tacet_mark_original"]

        bpy.ops.object.select_all(action='DESELECT')
        tacet_obj.select_set(True)
        context.view_layer.objects.active = tacet_obj

        for ws in bpy.data.workspaces:
            if "UV Editing" in ws.name:
                context.window.workspace = ws
                break

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')

        from ..ui.ui_cache import UICache
        UICache.clear()

        self.report({'INFO'}, "Edit UV for Tacet Mark, then click 'Tacet Mark [Complete]'")
        return {'FINISHED'}

    # ========== STAGE 3: COMPLETE ==========

    # Joins Tacet Mark geometry back into the original mesh and restores state
    def _stage3_complete(self, context, tacet_obj):
        original_name = tacet_obj.get("ww_tacet_mark_original")
        if not original_name:
            del tacet_obj["ww_tacet_mark_stage"]
            self.report({'ERROR'}, "Original mesh reference lost")
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='OBJECT')

        original_mesh = bpy.data.objects.get(original_name)
        if not original_mesh:
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and ObjectManager._clean_mesh_name(
                        obj.name) == ObjectManager._clean_mesh_name(original_name):
                    original_mesh = obj
                    break

        del tacet_obj["ww_tacet_mark_stage"]
        if "ww_tacet_mark_original" in tacet_obj:
            del tacet_obj["ww_tacet_mark_original"]

        cleaned_name = ObjectManager._clean_mesh_name(original_name)

        all_parts = [tacet_obj]
        if original_mesh:
            all_parts.append(original_mesh)

        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj not in all_parts:
                obj_clean = ObjectManager._clean_mesh_name(obj.name)
                if obj_clean == cleaned_name:
                    all_parts.append(obj)

        bpy.ops.object.select_all(action='DESELECT')
        for obj in all_parts:
            obj.select_set(True)

        armature_name = tacet_obj.get("ww_tacet_mark_armature")
        if not armature_name and original_mesh:
            armature_name = original_mesh.get("ww_tacet_mark_armature")

        if original_mesh:
            context.view_layer.objects.active = original_mesh
            final_mesh = original_mesh
        else:
            context.view_layer.objects.active = all_parts[0]
            final_mesh = all_parts[0]

        if len(all_parts) > 1:
            bpy.ops.object.join()

        mat_index = -1
        for i, slot in enumerate(final_mesh.material_slots):
            if slot.material and "Tacet Mark" in slot.material.name:
                mat_index = i
                break

        if mat_index >= 0:
            last_index = len(final_mesh.material_slots) - 1
            while mat_index < last_index:
                final_mesh.active_material_index = mat_index
                bpy.ops.object.material_slot_move(direction='DOWN')
                mat_index += 1

        if armature_name:
            armature = bpy.data.objects.get(armature_name)
            if armature:
                armature.hide_set(False)
            if "ww_tacet_mark_armature" in final_mesh:
                del final_mesh["ww_tacet_mark_armature"]

        from ..ui.ui_cache import UICache
        UICache.clear()

        self.report({'INFO'}, f"Tacet Mark added to '{cleaned_name}'")
        return {'FINISHED'}
