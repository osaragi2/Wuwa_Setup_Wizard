import os

import bpy

from ..core.helper_object_manager import HelperObjectManager
from ..core.object_manager import ObjectManager
from ..core.utils import Utils
from ..geometry.geometry_manager import GeometryManager
from ..geometry.seethrough_manager import SeeThroughManager
from ..geometry.vertex_processor import VertexProcessor
from ..texture.texture_processor import TextureProcessor
from .material_manager import MaterialManager


# ========== SHADER IMPORTER ==========

# Handles importing and configuring shaders for Wuthering Waves and Gathering Wives types
class ShaderImporter:

    # ========== MATERIAL SETTINGS ==========

    # Configures material render settings based on material type
    @staticmethod
    def _configure_material_settings(mat: bpy.types.Material, mat_type: str = 'Default') -> None:
        mat.use_backface_culling = True
        mat.use_sss_translucency = False
        mat.pass_index = 0
        mat.alpha_threshold = 0.5
        mat.refraction_depth = 0.0

        if mat_type == 'Face/Eye':
            mat.blend_method = 'HASHED'
            mat.shadow_method = 'HASHED'
            mat.use_screen_refraction = True
            mat.show_transparent_back = False
        elif mat_type == 'Tacet Mark':
            mat.blend_method = 'BLEND'
            mat.shadow_method = 'NONE'
            mat.use_screen_refraction = False
            mat.show_transparent_back = False
        elif mat_type == 'Alpha':
            mat.use_backface_culling = False
            mat.blend_method = 'BLEND'
            mat.shadow_method = 'HASHED'
            mat.use_screen_refraction = False
            mat.show_transparent_back = True
        elif mat_type == 'Outlines Alpha':
            mat.blend_method = 'BLEND'
            mat.shadow_method = 'NONE'
            mat.use_screen_refraction = False
            mat.show_transparent_back = True
        elif mat_type == 'Fur':
            mat.use_backface_culling = False
            mat.blend_method = 'HASHED'
            mat.shadow_method = 'HASHED'
            mat.use_screen_refraction = False
            mat.show_transparent_back = False
        else:
            mat.blend_method = 'OPAQUE'
            mat.shadow_method = 'OPAQUE'
            mat.use_screen_refraction = False
            mat.show_transparent_back = False

    # ========== FUR UV HELPER ==========

    # Recursively searches for node group named "Fur" and sets its UV Map to UV2
    @staticmethod
    def _set_fur_uv(node_tree) -> None:
        for node in node_tree.nodes:
            if node.type == 'GROUP' and node.node_tree:
                if node.node_tree.name == "Fur":
                    for n in node.node_tree.nodes:
                        if n.type == 'UVMAP':
                            n.uv_map = "UV2"
                    return
                ShaderImporter._set_fur_uv(node.node_tree)

    # ========== BASE MATERIAL SETTINGS ==========

    # Applies material settings to base (Fake User) materials so copies inherit them
    @staticmethod
    def _configure_base_material_settings(shader_mats: list[str]) -> None:
        for mat_name in shader_mats:
            mat = bpy.data.materials.get(mat_name)
            if not mat or mat_name == 'Planet':
                continue
            if mat_name == 'Tacet Mark':
                ShaderImporter._configure_material_settings(mat, 'Tacet Mark')
            elif mat_name == 'Outlines_Alpha':
                ShaderImporter._configure_material_settings(mat, 'Outlines Alpha')
            else:
                ShaderImporter._configure_material_settings(mat)

    # ========== COPY OVERRIDES ==========

    # Applies special overrides only for Alpha, Fur, Leisi, Glass material copies
    @staticmethod
    def _apply_copy_overrides(mesh: bpy.types.Object, shader_type: str) -> None:
        prefix = MaterialManager.PREFIXES.get(shader_type, MaterialManager.PREFIXES['ww'])
        for slot in mesh.material_slots:
            if not slot.material or not slot.material.node_tree:
                continue
            mat = slot.material
            if not mat.name.startswith(prefix):
                continue

            if "Fur" in mat.name:
                ShaderImporter._configure_material_settings(mat, 'Fur')
                ShaderImporter._apply_fur_node_inputs(mat, shader_type)
            elif any(p in mat.name for p in ["Alpha", "Leisi", "Glass"]):
                ShaderImporter._configure_material_settings(mat, 'Alpha')
                ShaderImporter._apply_alpha_node_inputs(mat, shader_type)

            if shader_type == 'ww':
                ShaderImporter._set_alpha_uv2(mat)

    # Enables fur-related node group inputs on a fur material copy
    @staticmethod
    def _apply_fur_node_inputs(mat: bpy.types.Material, shader_type: str) -> None:
        for node in mat.node_tree.nodes:
            if node.type != 'GROUP' or not node.node_tree:
                continue
            if shader_type == 'ww':
                if "Use Alpha" in node.inputs:
                    node.inputs["Use Alpha"].default_value = True
                if "Fur" in node.inputs:
                    node.inputs["Fur"].default_value = True
            else:
                if "Enable Alpha Override" in node.inputs:
                    node.inputs["Enable Alpha Override"].default_value = 1.0
                if "Enable Fur Override" in node.inputs:
                    node.inputs["Enable Fur Override"].default_value = 1.0
                ShaderImporter._set_fur_uv(node.node_tree)

    # Enables alpha-related node group inputs on an alpha material copy
    @staticmethod
    def _apply_alpha_node_inputs(mat: bpy.types.Material, shader_type: str) -> None:
        for node in mat.node_tree.nodes:
            if node.type != 'GROUP' or not node.node_tree:
                continue
            if shader_type == 'ww':
                if "Use Alpha" in node.inputs:
                    node.inputs["Use Alpha"].default_value = True
            else:
                if "Enable Alpha Override" in node.inputs:
                    node.inputs["Enable Alpha Override"].default_value = 1.0

    # Sets UV2 on Alpha node groups within WW materials
    @staticmethod
    def _set_alpha_uv2(mat: bpy.types.Material) -> None:
        if not mat.node_tree:
            return
        for node in mat.node_tree.nodes:
            if node.type != 'GROUP' or not node.node_tree:
                continue
            targets = [node.node_tree]
            targets.extend(
                n.node_tree for n in node.node_tree.nodes
                if n.type == 'GROUP' and n.node_tree)
            for nt in targets:
                if nt.name == "Alpha":
                    for n in nt.nodes:
                        if n.type == 'UVMAP':
                            n.uv_map = "UV2"

    # ========== GATHERING WIVES LEGACY SHADING ==========

    # Configures shading based on FTM/RGID texture presence in material nodes
    @staticmethod
    def _apply_gw_legacy_shading(mesh: bpy.types.Object, cleaned_mesh_name: str) -> None:
        for slot in mesh.material_slots:
            if not slot.material or not slot.material.node_tree:
                continue
            if not slot.material.name.startswith(MaterialManager.PREFIXES['gw']):
                continue

            nodes = slot.material.node_tree.nodes
            has_ftm = any(n.type == 'TEX_IMAGE' and n.image and 'FTM' in n.image.name for n in nodes)
            has_id = any(
                n.type == 'TEX_IMAGE' and n.image
                and 'ID' in n.image.name and 'RGID' not in n.image.name
                for n in nodes)
            has_rgid = any(n.type == 'TEX_IMAGE' and n.image and 'RGID' in n.image.name for n in nodes)

            mat_parts = slot.material.name.split(" ")
            is_up_or_down = any(
                TextureProcessor.PART_MAP.get(p, p) in ('Up', 'Down') for p in mat_parts
            )

            rgid_value = 1.0 if has_rgid and not has_id else 0.0

            for node in nodes:
                if node.type == 'GROUP' and node.node_tree:
                    if "Enable Legacy Shading" in node.inputs:
                        node.inputs["Enable Legacy Shading"].default_value = 0.0 if has_ftm else 1.0
                    if is_up_or_down and "Force Prioritize RGID Map" in node.inputs:
                        node.inputs["Force Prioritize RGID Map"].default_value = rgid_value

    # ========== SHADER IMPORT PIPELINE ==========

    # Per-shader-type configuration for the unified import pipeline
    SHADER_CONFIGS = {
        'ww': {
            'shader_mats': MaterialManager.SHADER_MATS_WW,
            'node_groups': list(MaterialManager.NODE_GROUPS_WW),
            'helper_objs': ["Head Origin", "Light Direction", "Head Forward", "Head Right"],
            'helper_setup': lambda mesh: (
                HelperObjectManager.setup_head_origin(mesh),
                HelperObjectManager.setup_light_direction(mesh),
            ),
            'vectors_name': "[WW] Vectors",
            'vectors_setup': GeometryManager.setup_light_direction_ww,
            'outlines_name': "[WW] Outlines",
        },
        'gw': {
            'shader_mats': MaterialManager.SHADER_MATS_GW,
            'node_groups': list(MaterialManager.NODE_GROUPS_GW),
            'helper_objs': ["Head Controller", "Main Light"],
            'helper_setup': lambda mesh: (
                HelperObjectManager.setup_head_controller(mesh),
                HelperObjectManager.setup_main_light(mesh),
            ),
            'vectors_name': "[GW] Vectors",
            'vectors_setup': GeometryManager.setup_light_direction_gw,
            'outlines_name': "[GW] Outlines",
        },
    }

    # Loads shader assets (materials, node groups, objects) from blend file
    @staticmethod
    def _load_shader_assets(filepath: str, shader_mats: list[str],
                            node_groups: list[str], helper_objs: list[str]) -> None:
        with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
            mats = [m for m in data_from.materials if m in shader_mats]
            groups = [g for g in data_from.node_groups if g in node_groups]
            objs = [o for o in data_from.objects if o in helper_objs]

            existing_mats = set(bpy.data.materials.keys())
            existing_groups = set(bpy.data.node_groups.keys())

            mats_to_import = [m for m in mats if m not in existing_mats]
            groups_to_import = [g for g in groups if g not in existing_groups]

            if mats_to_import:
                bpy.ops.wm.append(filepath=filepath, directory=os.path.join(
                    filepath, "Material"), files=[{"name": m} for m in mats_to_import])
            if groups_to_import:
                bpy.ops.wm.append(filepath=filepath, directory=os.path.join(
                    filepath, "NodeTree"), files=[{"name": g} for g in groups_to_import])
            if objs:
                bpy.ops.wm.append(filepath=filepath, directory=os.path.join(
                    filepath, "Object"), files=[{"name": o} for o in objs])

            bpy.context.view_layer.update()

            for mat_name in mats_to_import:
                mat = bpy.data.materials.get(mat_name)
                if mat:
                    mat.use_fake_user = True
            for group_name in groups_to_import:
                group = bpy.data.node_groups.get(group_name)
                if group:
                    group.use_fake_user = True
            for obj_name in objs:
                obj = bpy.data.objects.get(obj_name)
                if obj and obj.name not in bpy.context.view_layer.objects:
                    bpy.context.collection.objects.link(obj)

    # Loads only helper objects from blend file (non-first import)
    @staticmethod
    def _load_helper_objects(filepath: str, helper_objs: list[str]) -> None:
        with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
            objs_to_import = [o for o in data_from.objects if o in helper_objs]
            if objs_to_import:
                bpy.ops.wm.append(filepath=filepath, directory=os.path.join(
                    filepath, "Object"), files=[{"name": o} for o in objs_to_import])
            bpy.context.view_layer.update()
            for obj_name in objs_to_import:
                obj = bpy.data.objects.get(obj_name)
                if obj and obj.name not in bpy.context.view_layer.objects:
                    bpy.context.collection.objects.link(obj)

    # Sets up outline modifiers for the mesh
    @staticmethod
    def _setup_outlines(mesh: bpy.types.Object, mesh_name: str, outlines_name: str) -> None:
        cleaned_mesh_name = ObjectManager._clean_mesh_name(mesh_name)

        if not GeometryManager.create_modifier(mesh, outlines_name, mesh_name, GeometryManager.setup_outlines):
            return
        outline_mod_name = f"{outlines_name} {cleaned_mesh_name}"

        outline_mod = mesh.modifiers.get(outline_mod_name)
        if outline_mod:
            outline_mod.show_viewport = False
            outline_mod.show_render = False

    # Unified shader import pipeline for both WW and GW shader types
    @staticmethod
    def _import_shader(filepath: str, mesh: bpy.types.Object, mesh_name: str,
                       is_first: bool, shader_type: str) -> bool:
        config = ShaderImporter.SHADER_CONFIGS[shader_type]

        if is_first:
            ObjectManager.cleanup()
            MaterialManager.purge_shader_data()
            ShaderImporter._load_shader_assets(
                filepath, config['shader_mats'], config['node_groups'], config['helper_objs'])
            ShaderImporter._configure_base_material_settings(config['shader_mats'])
        else:
            ShaderImporter._load_helper_objects(filepath, config['helper_objs'])

        HelperObjectManager.rename_imported_objects(mesh_name)
        config['helper_setup'](mesh)

        MaterialManager.process_materials(mesh, mesh_name, shader_type=shader_type)

        GeometryManager.create_modifier(
            mesh, config['vectors_name'], mesh_name, config['vectors_setup'])

        VertexProcessor.process_eye_colors(mesh)

        ShaderImporter._setup_outlines(mesh, mesh_name, config['outlines_name'])
        ShaderImporter._apply_copy_overrides(mesh, shader_type)
        SeeThroughManager.create_seethrough_mesh(mesh, mesh_name, shader_type=shader_type)

        if shader_type == 'gw':
            cleaned_mesh_name = ObjectManager._clean_mesh_name(mesh_name)
            ShaderImporter._apply_gw_legacy_shading(mesh, cleaned_mesh_name)

        return True

    # ========== MAIN ENTRY POINT ==========

    # Detects shader type from settings and delegates to the unified import pipeline
    @staticmethod
    def import_shader(filepath: str, mesh: bpy.types.Object, is_first: bool = True,
                      shader_type: str | None = None) -> bool:
        if not os.path.exists(filepath) or not filepath.endswith('.blend'):
            return False

        Utils.set_viewport('SOLID')
        mesh_name = mesh.name

        # If shader_type is explicitly provided, use it directly (avoids mismatch with filepath)
        if shader_type is None:
            shader_type = 'ww'
            try:
                if hasattr(bpy.context, 'scene') and hasattr(bpy.context.scene, 'ww_properties'):
                    prop_type = bpy.context.scene.ww_properties.shader_type
                    if prop_type == 'gathering_wives':
                        shader_type = 'gw'
            except (AttributeError, TypeError):
                pass

        result = ShaderImporter._import_shader(filepath, mesh, mesh_name, is_first, shader_type)

        Utils.select_only(mesh)
        return result
