import re

import bpy

from ..texture.texture_processor import TextureProcessor


# ========== MATERIAL MANAGER ==========

# Manages material creation, assignment, and shader processing for Wuthering Waves and Gathering Wives shaders
class MaterialManager:

    # ========== SHADER DEFINITIONS ==========

    SHADER_MATS_WW = [
        "Wuthering Waves - Bangs", "Wuthering Waves - Hair", "Wuthering Waves - Face",
        "Wuthering Waves - Up", "Wuthering Waves - Body", "Wuthering Waves - Eye",
        "Tacet Mark", "Outlines_Alpha", "Outlines", "Planet"
    ]
    SHADER_MATS_GW = [
        "Gathering Wives - Bangs", "Gathering Wives - Hair", "Gathering Wives - Face",
        "Gathering Wives - Up", "Gathering Wives - Body", "Gathering Wives - Eye",
        "Tacet Mark", "Outlines_Alpha", "Outlines", "Planet"
    ]
    NODE_GROUPS_WW = [
        "[WW] Vectors", "[WW] Outlines",
        "Glow & Eye FX / Rim Light / Notch Shadow"
    ]
    NODE_GROUPS_GW = [
        "[GW] Vectors", "[GW] Outlines",
        "Glow & Eye FX / Rim Light / Notch Shadow"
    ]
    PREFIXES = {
        'ww': "Wuthering Waves - ",
        'gw': "Gathering Wives - "
    }
    SHADER_NAMES = {
        'ww': "Wuthering Waves",
        'gw': "Gathering Wives"
    }

    # ========== SHADER TYPE DETECTION ==========

    # Detects shader type from helper objects (Head Controller, Main Light)
    @staticmethod
    def detect_shader_type_by_helpers(mesh: bpy.types.Object) -> str:
        from ..core.object_manager import ObjectManager
        cleaned_name = ObjectManager._clean_mesh_name(mesh.name)
        head_controller = bpy.data.objects.get(f"Head Controller {cleaned_name}")
        main_light = bpy.data.objects.get(f"Main Light {cleaned_name}")
        if head_controller and main_light:
            return 'gw'
        return 'ww'

    # Detects shader type from mesh materials ('ww' or 'gw')
    @staticmethod
    def get_shader_type_from_materials(mesh: bpy.types.Object) -> str:
        for slot in mesh.material_slots:
            if slot.material:
                for key, prefix in MaterialManager.PREFIXES.items():
                    if slot.material.name.startswith(prefix):
                        return key
        return 'ww'

    # Checks if mesh has Wuthering Waves or Gathering Wives shader materials applied
    @staticmethod
    def has_ww_materials(mesh: bpy.types.Object) -> bool:
        prefixes = tuple(MaterialManager.PREFIXES.values())
        for slot in mesh.material_slots:
            if slot.material and slot.material.name.startswith(prefixes):
                return True
        return False

    # ========== UTILITY FUNCTIONS ==========

    # Extracts part name from material name (e.g., "Body", "Face", "Eye")
    @staticmethod
    def extract_part(name: str) -> str | None:
        matches = list(re.finditer(r'[A-Z]', name))
        if matches:
            part = name[matches[-1].start():]
            return TextureProcessor.PART_MAP.get(part, part)
        return None

    # Extracts Xing number from material name for Tacet Mark textures
    @staticmethod
    def extract_xing_number(name: str) -> int | None:
        match = re.search(r'(\d+)xing', name, re.IGNORECASE)
        return int(match.group(1)) if match else None

    # ========== SHADER DATA MANAGEMENT ==========

    # Removes all shader materials and node groups from the blend file
    @staticmethod
    def purge_shader_data() -> None:
        all_mats = set(MaterialManager.SHADER_MATS_WW + MaterialManager.SHADER_MATS_GW)
        all_groups = set(MaterialManager.NODE_GROUPS_WW + MaterialManager.NODE_GROUPS_GW)
        for mat_name in all_mats:
            mat = bpy.data.materials.get(mat_name)
            if mat:
                bpy.data.materials.remove(mat)
        for group_name in all_groups:
            group = bpy.data.node_groups.get(group_name)
            if group:
                bpy.data.node_groups.remove(group)

    # ========== TACET MARK ==========

    # Configures Tacet Mark node group with appropriate texture index
    @staticmethod
    def setup_tacet_node(material: bpy.types.Material, xing_num: int) -> bool:
        if not material or not material.node_tree:
            return False
        mapping = {3: 1, 5: 2, 6: 3}
        if xing_num not in mapping:
            return False
        for node in material.node_tree.nodes:
            if node.type == 'GROUP' and node.node_tree and node.node_tree.name == "Tacet Mark":
                if "Tacet Mark Texture" in node.inputs:
                    node.inputs["Tacet Mark Texture"].default_value = mapping[xing_num]
                    return True
        return False

    # Copies Tacet Mark material for the slot and sets texture index from Xing number
    @staticmethod
    def _process_tacet_mark(
        slot,
        image_name: str,
        imported: dict[str, bpy.types.Material],
        cache: dict[str, bpy.types.Material],
        cleaned_mesh_name: str
    ) -> bool:
        if "Tacet Mark" in cache:
            slot.material = cache["Tacet Mark"]
            return True

        if "Tacet Mark" not in imported:
            return False

        tacet_mat = imported["Tacet Mark"].copy()
        tacet_mat.name = f"Tacet Mark {cleaned_mesh_name}"
        slot.material = tacet_mat
        cache["Tacet Mark"] = tacet_mat

        xing_num = MaterialManager.extract_xing_number(image_name)
        if xing_num:
            MaterialManager.setup_tacet_node(tacet_mat, xing_num)
        return True

    # ========== OUTLINE MATERIALS ==========

    # Removes duplicate outline materials with .001, .002 suffixes
    @staticmethod
    def _remove_duplicate_outline_materials(cleaned_mesh_name: str) -> None:
        target_names = [
            f"Outlines_Alpha {cleaned_mesh_name}",
            f"Outlines {cleaned_mesh_name}"
        ]
        mats_to_remove = []
        for mat in bpy.data.materials:
            for target in target_names:
                if mat.name.startswith(target) and mat.name != target:
                    if re.match(rf"^{re.escape(target)}\.\d+$", mat.name):
                        mats_to_remove.append(mat)
        for mat in mats_to_remove:
            if mat.users == 0:
                bpy.data.materials.remove(mat)

    # Creates per-character copies of Outlines_Alpha and Outlines materials into cache

    @staticmethod
    def _ensure_outline_materials(
        imported: dict[str, bpy.types.Material],
        cache: dict[str, bpy.types.Material],
        cleaned_mesh_name: str
    ) -> None:
        for suffix in ["Outlines_Alpha", "Outlines"]:
            if suffix in imported and suffix not in cache:
                outline_mat = imported[suffix].copy()
                outline_mat.name = f"{suffix} {cleaned_mesh_name}"
                cache[suffix] = outline_mat

    # ========== MATERIAL CREATION ==========

    # Creates or retrieves a per-character copy of a shader material from cache
    @staticmethod
    def _create_or_get_material(
        part_key: str,
        imported: dict[str, bpy.types.Material],
        cache: dict[str, bpy.types.Material],
        cleaned_mesh_name: str,
        prefix: str = ""
    ) -> bpy.types.Material | None:
        if part_key in cache:
            return cache[part_key]

        shader_name = f"{prefix}{part_key}" if prefix else part_key
        source = imported.get(shader_name, imported.get(f"{prefix}Body") if prefix else None)
        if not source:
            source = imported.get(part_key)
        if not source:
            return None

        new_mat = source.copy()
        new_mat.name = f"{shader_name} {cleaned_mesh_name}" if prefix else f"{part_key} {cleaned_mesh_name}"
        cache[part_key] = new_mat
        return new_mat

    # ========== MODEL TYPE DETECTION ==========

    # Checks if mesh is a MOD model (all materials contain "Component")

    @staticmethod
    def _is_mod_model(mesh: bpy.types.Object) -> bool:
        if not mesh.material_slots:
            return False
        return all(
            slot.material and "Component" in slot.material.name
            for slot in mesh.material_slots
        )

    # Extracts component number from material name

    @staticmethod
    def _extract_component_number(name: str) -> int:
        match = re.search(r'Component\s*(\d+)', name)
        return int(match.group(1)) if match else -1

    # Maps component number to part name
    @staticmethod
    def _get_part_from_component(comp_num: int, is_last_slot: bool) -> str:
        if is_last_slot:
            return "Eye"
        part_map = {0: "Bangs", 1: "Hair", 2: "Face"}
        if comp_num in part_map:
            return part_map[comp_num]
        if comp_num >= 3:
            return f"Body {comp_num}"
        return "Body"

    # ========== MATERIAL PROCESSING ==========

    # Replaces UEModel materials based on part names extracted from slot names

    @staticmethod
    def _process_standard_materials(
        mesh: bpy.types.Object,
        cleaned_mesh_name: str,
        imported: dict[str, bpy.types.Material],
        prefix: str
    ) -> bool:
        tacet_mapped = False
        cache: dict[str, bpy.types.Material] = {}

        for slot in mesh.material_slots:
            if not slot.material:
                continue

            orig_name = slot.material.name

            if "XingStar" in orig_name:
                if MaterialManager._process_tacet_mark(slot, orig_name, imported, cache, cleaned_mesh_name):
                    tacet_mapped = True
                continue

            part = MaterialManager.extract_part(orig_name)
            if part:
                new_mat = MaterialManager._create_or_get_material(part, imported, cache, cleaned_mesh_name, prefix)
                if new_mat:
                    slot.material = new_mat

        MaterialManager._ensure_outline_materials(imported, cache, cleaned_mesh_name)
        return tacet_mapped

    # Replaces MOD materials by mapping Component numbers to shader parts
    @staticmethod
    def _process_mod_materials(
        mesh: bpy.types.Object,
        cleaned_mesh_name: str,
        imported: dict[str, bpy.types.Material],
        prefix: str
    ) -> bool:
        total_slots = len(mesh.material_slots)
        cache: dict[str, bpy.types.Material] = {}

        for i, slot in enumerate(mesh.material_slots):
            if not slot.material:
                continue

            is_last = (i == total_slots - 1)
            comp_num = MaterialManager._extract_component_number(slot.material.name)
            part = MaterialManager._get_part_from_component(comp_num, is_last)

            if part in cache:
                slot.material = cache[part]
            else:
                base_part = part.split()[0]
                shader_name = f"{prefix}{base_part}"
                source = imported.get(shader_name, imported.get(f"{prefix}Body"))
                if source:
                    new_mat = source.copy()
                    new_mat.name = f"{prefix}{part} {cleaned_mesh_name}"
                    slot.material = new_mat
                    cache[part] = new_mat

        MaterialManager._ensure_outline_materials(imported, cache, cleaned_mesh_name)
        return False

    # ========== MAIN ENTRY POINT ==========

    # Detects model type (MOD/Standard) and dispatches to appropriate material processor
    @staticmethod
    def process_materials(mesh: bpy.types.Object, mesh_name: str, shader_type: str = 'ww') -> bool:
        from ..core.object_manager import ObjectManager

        shader_mats = MaterialManager.SHADER_MATS_WW if shader_type == 'ww' else MaterialManager.SHADER_MATS_GW
        imported: dict[str, bpy.types.Material] = {
            mat.name: mat for mat in bpy.data.materials if mat.name in shader_mats
        }
        cleaned_mesh_name = ObjectManager._clean_mesh_name(mesh_name)
        prefix = MaterialManager.PREFIXES.get(shader_type, MaterialManager.PREFIXES['ww'])

        if MaterialManager._is_mod_model(mesh):
            return MaterialManager._process_mod_materials(mesh, cleaned_mesh_name, imported, prefix)

        return MaterialManager._process_standard_materials(mesh, cleaned_mesh_name, imported, prefix)
