import os

import bpy
from bpy.props import CollectionProperty, StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

from ..core.object_manager import ObjectManager
from ..core.scene_manager import SceneManager
from ..core.utils import Utils
from ..material.material_manager import MaterialManager
from ..texture.texture_processor import TextureProcessor


# ========== MODEL IMPORT ==========

# Opens file browser to import a character model
class WW_OT_ImportModel(Operator):
    bl_idname = "ww.import_model"
    bl_label = "Import Model"
    bl_description = "Opens the file browser to import a character model (.uemodel, .fbx, etc.)."
    bl_options = {'REGISTER', 'UNDO'}

    # Opens the UEFormat file browser for model import
    def execute(self, context):
        try:
            bpy.ops.uf.import_uemodel('INVOKE_DEFAULT')
            return {'FINISHED'}
        except AttributeError:
            self.report(
                {'ERROR'}, "UEFormat addon not installed. Please install it from GitHub")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {str(e)}")
            return {'CANCELLED'}


# ========== TEXTURE IMPORT ==========

# Opens file browser to select and assign textures
class WW_OT_ImportTexture(Operator, ImportHelper):
    bl_idname = "ww.import_texture"
    bl_label = "Import Textures"
    bl_description = "Opens the file browser to select and automatically assign textures (D, N, HM, etc.) to the model."
    bl_options = {'REGISTER', 'UNDO'}

    files: CollectionProperty(
        name="File Path", type=bpy.types.OperatorFileListElement)
    directory: StringProperty(subtype='DIR_PATH')
    filter_glob: StringProperty(
        default="*.png;*.jpg;*.jpeg;*.tga;*.tiff", options={'HIDDEN'}, maxlen=255)

    # Loads selected texture files and assigns them to material shader nodes
    def execute(self, context):
        mesh = context.active_object

        if not mesh or mesh.type != 'MESH':
            self.report({'ERROR'}, "Please select a mesh object first")
            return {'CANCELLED'}

        if not MaterialManager.has_ww_materials(mesh):
            self.report({'ERROR'}, "Please apply Wuthering Waves shader first")
            return {'CANCELLED'}

        if not self.files:
            self.report({'WARNING'}, "No texture files selected")
            return {'CANCELLED'}

        try:
            files = [os.path.join(self.directory, f.name) for f in self.files]
            valid_files = [f for f in files if os.path.exists(f)]

            if not valid_files:
                self.report({'ERROR'}, "Selected files not found")
                return {'CANCELLED'}

            bpy.ops.outliner.orphans_purge(
                do_local_ids=True, do_linked_ids=False, do_recursive=True)

            TextureProcessor.map_textures(valid_files, mesh)

            from ..material.shader_importer import ShaderImporter
            cleaned_name = ObjectManager._clean_mesh_name(mesh.name)
            ShaderImporter._apply_gw_legacy_shading(mesh, cleaned_name)

            SceneManager.setup_passes()
            SceneManager.setup_compositor()
            Utils.set_viewport('RENDERED')

            cleaned_name = ObjectManager._clean_mesh_name(mesh.name)
            skipped = len(files) - len(valid_files)
            if skipped > 0:
                self.report(
                    {'INFO'}, f"Imported {len(valid_files)} textures for '{cleaned_name}' ({skipped} skipped)")
            else:
                self.report(
                    {'INFO'}, f"Imported {len(valid_files)} textures for '{cleaned_name}'")

            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Texture import failed: {str(e)}")
            return {'CANCELLED'}
