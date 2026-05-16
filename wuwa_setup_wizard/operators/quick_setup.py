import os

import bpy
from bpy.types import Operator

from ..addon_info import get_shader_path
from ..core.collection_manager import CollectionManager
from ..core.object_manager import ObjectManager
from ..core.scene_manager import SceneManager
from ..core.utils import Utils
from ..material.material_manager import MaterialManager
from ..material.shader_importer import ShaderImporter
from ..rigging.face_panel_creator import WW_OT_CreateFacePanel
from ..rigging.face_panel_importer import WW_OT_ImportFacePanel
from ..rigging.rigify_operator import WW_OT_Rigify
from ..texture.texture_processor import TextureProcessor
from .collection_ops import WW_OT_CreateCollection


# ========== CONSTANTS ==========

VALID_TEXTURE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.tga', '.tiff')
PROGRESS_BAR_WIDTH = 40


# ========== PROGRESS BAR ==========

# Console progress bar utility
class ProgressBar:
    # Renders progress bar with percentage and task name to console
    @staticmethod
    def show(percent: int, task: str, width: int = PROGRESS_BAR_WIDTH) -> None:
        filled = int(width * percent / 100)
        bar = "█" * filled + "░" * (width - filled)
        print("\033[2A", end="")
        print(f"\r[{bar}] {percent:3d}%")
        print(f"\r> {task:<50}", end="", flush=True)

    # Prints initial blank lines for progress bar space
    @staticmethod
    def start() -> None:
        print("\n\n")

    # Prints completion message with separator lines
    @staticmethod
    def complete(message: str) -> None:
        print(f"\n\n{'=' * 50}")
        print(f"[DONE] {message}")
        print(f"{'=' * 50}\n")

    # Prints section header with title and separator lines
    @staticmethod
    def header(title: str) -> None:
        print(f"\n{'=' * 50}")
        print(f"  {title}")
        print(f"{'=' * 50}")
        ProgressBar.start()


# ========== QUICK SETUP OPERATOR ==========

# Main operator for one-click character setup
class WW_OT_QuickSetup(Operator):
    bl_idname = "ww.quick_setup"
    bl_label = "Quick Setup"
    bl_description = "Automatically imports model, applies shaders, maps textures, and sets up rig in one click."
    bl_options = {'REGISTER', 'UNDO'}

    timer_handle = None
    initial_objects: set
    import_path: str

    # Requires shader blend file to be configured in preferences
    @classmethod
    def poll(cls, context):
        return bool(get_shader_path())

    # ========== INVOKE AND MODAL ==========

    # Opens UEFormat file browser and starts modal timer to detect imported objects
    def invoke(self, context, event):
        try:
            self.initial_objects = set(bpy.data.objects)
            bpy.ops.uf.import_uemodel('INVOKE_DEFAULT')
        except AttributeError:
            self.report({'ERROR'}, "UEFormat addon not installed. Install from GitHub first")
            return {'CANCELLED'}

        wm = context.window_manager
        self.timer_handle = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    # Waits for import completion then runs full setup pipeline
    def modal(self, context, event):
        if event.type != 'TIMER':
            return {'PASS_THROUGH'}

        current_objects = set(bpy.data.objects)
        new_objects = current_objects - self.initial_objects

        if not new_objects:
            return {'PASS_THROUGH'}

        wm = context.window_manager
        wm.progress_begin(0, 100)
        wm.progress_update(5)

        bpy.context.view_layer.update()
        self._cleanup_timer(context)

        new_mesh = self._post_import_processing(context, new_objects)

        if new_mesh and "LOD0" not in new_mesh.name:
            wm.progress_end()
            return {'FINISHED'}

        self._process_import_path(context, new_objects)

        if new_mesh:
            try:
                self.run_full_setup(context, new_mesh)
            except Exception:
                wm.progress_end()
                return {'CANCELLED'}
        else:
            self.report({'ERROR'}, "No valid mesh found after import")
            wm.progress_end()
            return {'CANCELLED'}

        return {'FINISHED'}

    # Cleans up modal timer on operator cancellation
    def cancel(self, context):
        self._cleanup_timer(context)

    # ========== POST IMPORT PROCESSING ==========

    # Finds the imported mesh from newly created objects after import
    def _post_import_processing(self, context, new_objects):
        new_armature = next(
            (obj for obj in new_objects if obj.type == 'ARMATURE'), None
        )
        if not new_armature:
            return None

        new_mesh = ObjectManager.get_mesh_from_armature(new_armature)
        if not new_mesh:
            return None

        if not Utils.select_only(new_mesh):
            return None
        return new_mesh

    # Removes the modal event timer
    def _cleanup_timer(self, context):
        if self.timer_handle:
            context.window_manager.event_timer_remove(self.timer_handle)
            self.timer_handle = None

    # Reads import path from last operator and cleans up existing character assets
    def _process_import_path(self, context, new_objects):
        last_op = context.window_manager.operator_properties_last("uf.import_uemodel")
        if last_op and hasattr(last_op, 'filepath'):
            self.import_path = last_op.filepath
            filename = os.path.basename(self.import_path)
            base_name = ObjectManager._clean_mesh_name(filename)
            ObjectManager.cleanup_character_assets(base_name, exclude_objects=new_objects)

    # ========== MAIN SETUP FLOW ==========

    # Orchestrates the complete character setup pipeline from shader to organization
    def run_full_setup(self, context, new_mesh):
        wm = context.window_manager
        try:
            if not self._validate_mesh(new_mesh):
                self.report({'ERROR'}, "Import failed: mesh not found")
                return

            self._prepare_context(context)

            if not Utils.select_only(new_mesh):
                self.report({'ERROR'}, "Failed to select mesh")
                return

            cleaned_name = ObjectManager._clean_mesh_name(new_mesh.name)

            if MaterialManager.has_ww_materials(new_mesh):
                self.report({'INFO'}, f"'{cleaned_name}' already set up, skipped")
                return

            shader_path = get_shader_path()
            if not shader_path:
                self.report({'ERROR'}, "Shader file not found")
                return

            ProgressBar.header(f"Quick Setup: {cleaned_name}")
            self._execute_setup_steps(context, new_mesh, shader_path, cleaned_name, wm)

        except Exception as e:
            self.report({'ERROR'}, f"Setup error: {str(e)}")
        finally:
            wm.progress_end()

    # Checks if the imported mesh object still exists in the scene
    def _validate_mesh(self, new_mesh) -> bool:
        return new_mesh and new_mesh.name in bpy.data.objects

    # Ensures Object mode and updates the view layer before setup
    def _prepare_context(self, context) -> None:
        bpy.context.view_layer.update()
        if bpy.context.mode != 'OBJECT':
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except RuntimeError:
                pass

    # ========== SETUP STEPS ==========

    # Runs all setup steps in sequence: shader, textures, scene, rigify, face panel, organize
    def _execute_setup_steps(self, context, new_mesh, shader_path, cleaned_name, wm):
        SceneManager.setup_scene_settings(context)
        shader_type = context.scene.ww_properties.shader_type
        if shader_type == 'gathering_wives':
            is_first = "[GW] Outlines" not in bpy.data.node_groups
        else:
            is_first = "[WW] Outlines" not in bpy.data.node_groups

        self._step_apply_shader(new_mesh, shader_path, is_first, wm)
        self._step_load_textures(new_mesh, wm)
        self._step_setup_scene(context, wm)
        self._step_rigify(context, new_mesh, wm)
        self._step_face_panel(context, new_mesh, wm)
        self._step_organize(context, new_mesh, wm)
        self._step_complete(cleaned_name, wm)

    # Imports and applies the character shader to the mesh
    def _step_apply_shader(self, new_mesh, shader_path, is_first, wm):
        ProgressBar.show(10, "Applying shader...")
        wm.progress_update(10)
        if not ShaderImporter.import_shader(shader_path, new_mesh, is_first):
            raise RuntimeError("Shader application failed")

    # Discovers and assigns texture files from the import directory
    def _step_load_textures(self, new_mesh, wm):
        ProgressBar.show(30, "Loading textures...")
        wm.progress_update(30)
        import_dir = os.path.dirname(self.import_path)
        texture_files = self._collect_texture_files(import_dir)

        if texture_files:
            TextureProcessor.map_textures(texture_files, new_mesh)
            from ..material.shader_importer import ShaderImporter
            cleaned_name = ObjectManager._clean_mesh_name(new_mesh.name)
            ShaderImporter._apply_gw_legacy_shading(new_mesh, cleaned_name)

    # Recursively collects valid texture image files from a directory
    def _collect_texture_files(self, import_dir: str) -> list:
        texture_files = []
        for root, _, files in os.walk(import_dir):
            for file in files:
                if file.lower().endswith(VALID_TEXTURE_EXTENSIONS):
                    texture_files.append(os.path.join(root, file))
        return texture_files

    # Configures scene render passes and compositor node setup
    def _step_setup_scene(self, context, wm):
        ProgressBar.show(50, "Setting up scene...")
        wm.progress_update(50)
        SceneManager.setup_passes()
        SceneManager.setup_compositor()
        context.view_layer.update()

    # Generates Rigify control rig if enabled in quick setup options
    def _step_rigify(self, context, new_mesh, wm):
        ww_props = context.scene.ww_properties
        if not Utils.select_only(new_mesh):
            return

        if ww_props.quick_setup_rigify:
            ProgressBar.show(60, "Setting up Rigify...")
            wm.progress_update(60)
            if WW_OT_Rigify.poll(context):
                try:
                    bpy.ops.ww.rigify_armature()
                except Exception:
                    pass
        else:
            ProgressBar.show(60, "Skipping Rigify...")
            wm.progress_update(60)

    # Creates or imports face panel if enabled in quick setup options
    def _step_face_panel(self, context, new_mesh, wm):
        ww_props = context.scene.ww_properties
        if ww_props.quick_setup_create_face:
            ProgressBar.show(75, "Creating face panel...")
            wm.progress_update(75)
            if WW_OT_CreateFacePanel.poll(context):
                try:
                    bpy.ops.ww.create_face_panel()
                except Exception:
                    pass
        else:
            ProgressBar.show(75, "Skipping face panel...")
            wm.progress_update(75)

        if ww_props.quick_setup_import_face:
            if WW_OT_ImportFacePanel.poll(context):
                try:
                    bpy.ops.ww.import_face_panel('INVOKE_DEFAULT')
                except Exception:
                    pass

        Utils.select_only(new_mesh)

    # Creates character collection and switches viewport to rendered mode
    def _step_organize(self, context, new_mesh, wm):
        ProgressBar.show(90, "Organizing collections...")
        wm.progress_update(90)
        if WW_OT_CreateCollection.poll(context):
            try:
                bpy.ops.ww.create_collection()
            except Exception:
                pass

        Utils.set_viewport('RENDERED')

    # Finalizes setup with progress completion and status report
    def _step_complete(self, cleaned_name, wm):
        ProgressBar.show(100, "Complete!")
        wm.progress_update(100)
        ProgressBar.complete(f"Setup complete for '{cleaned_name}'")
        self.report({'INFO'}, f"Setup complete for '{cleaned_name}'")
