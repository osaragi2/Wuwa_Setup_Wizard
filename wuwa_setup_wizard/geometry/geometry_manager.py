from typing import Callable
import bpy


# ========== GEOMETRY MANAGER ==========

# Manages geometry nodes and modifiers for mesh objects
class GeometryManager:

    # ========== MODIFIER MANAGEMENT ==========

    # Removes duplicate node groups with .001, .002 suffixes
    @staticmethod
    def _remove_duplicate_node_groups(node_name: str) -> None:
        import re
        groups_to_remove = []
        for group in bpy.data.node_groups:
            if re.match(rf"^{re.escape(node_name)}\.d+$", group.name):
                groups_to_remove.append(group)
        for group in groups_to_remove:
            if group.users == 0:
                bpy.data.node_groups.remove(group)

    # Creates a geometry nodes modifier on the mesh with optional setup callback
    @staticmethod
    def create_modifier(mesh: bpy.types.Object, base_name: str, mesh_name: str,
                        extra_setup: Callable | None = None) -> bool:
        from ..core.object_manager import ObjectManager
        cleaned_mesh_name = ObjectManager._clean_mesh_name(mesh_name)
        node_name = f"{base_name} {cleaned_mesh_name}"

        GeometryManager._remove_duplicate_node_groups(node_name)

        if base_name not in bpy.data.node_groups:
            return False
        if node_name not in bpy.data.node_groups:
            source_group = bpy.data.node_groups.get(base_name)
            if not source_group:
                return False
            new_tree = source_group.copy()
            new_tree.name = node_name
        mod = mesh.modifiers.get(
            node_name) or mesh.modifiers.new(node_name, 'NODES')
        mod.node_group = bpy.data.node_groups[node_name]
        if extra_setup:
            extra_setup(mod, mesh.name)
        return True

    # Removes all outline-related geometry modifiers from mesh
    @staticmethod
    def remove_outline_modifiers(mesh: bpy.types.Object) -> None:
        modifiers_to_remove = [
            mod for mod in mesh.modifiers if "Outlines" in mod.name]
        for mod in modifiers_to_remove:
            mesh.modifiers.remove(mod)

    # ========== VECTOR SETUP (LIGHT DIRECTION) ==========

    # Sets up Wuthering Waves Vectors modifier with Head Origin and Light Direction

    @staticmethod
    def setup_light_direction_ww(mod: bpy.types.NodesModifier, mesh_name: str) -> None:
        from ..core.object_manager import ObjectManager
        cleaned_mesh_name = ObjectManager._clean_mesh_name(mesh_name)
        light_direction_name = f"Light Direction {cleaned_mesh_name}"
        head_origin_name = f"Head Origin {cleaned_mesh_name}"
        head_forward_name = f"Head Forward {cleaned_mesh_name}"
        head_right_name = f"Head Right {cleaned_mesh_name}"
        mod["Socket_6"] = bpy.data.objects.get(light_direction_name)
        mod["Socket_7"] = bpy.data.objects.get(head_origin_name)
        mod["Socket_10"] = bpy.data.objects.get(head_forward_name)
        mod["Socket_11"] = bpy.data.objects.get(head_right_name)
        mod["Socket_2_attribute_name"] = "lightDir"
        mod["Socket_4_attribute_name"] = "headForward"
        mod["Socket_5_attribute_name"] = "headRight"

    # Sets up Gathering Wives Vectors modifier with Head Controller and Main Light
    @staticmethod
    def setup_light_direction_gw(mod: bpy.types.NodesModifier, mesh_name: str) -> None:
        from ..core.object_manager import ObjectManager
        cleaned_mesh_name = ObjectManager._clean_mesh_name(mesh_name)
        main_light = bpy.data.objects.get(f"Main Light {cleaned_mesh_name}")
        head_controller = bpy.data.objects.get(
            f"Head Controller {cleaned_mesh_name}")
        if main_light and "Input_2" in mod:
            mod["Input_2"] = main_light
        if head_controller and "Socket_1" in mod:
            mod["Socket_1"] = head_controller

    # ========== OUTLINE SETUP ==========

    # Sets up UEMODEL Outlines modifier with Face/Eye exclusion and vertex color attribute
    @staticmethod
    def setup_outlines(mod: bpy.types.NodesModifier, mesh_name: str) -> None:
        from ..material.material_manager import MaterialManager

        mesh = bpy.data.objects.get(mesh_name)
        if not mesh:
            return

        shader_type = MaterialManager.get_shader_type_from_materials(mesh)
        prefix = MaterialManager.SHADER_NAMES.get(shader_type, MaterialManager.SHADER_NAMES['ww'])

        face_mat = None
        eye_mat = None
        for slot in mesh.material_slots:
            if slot.material and slot.material.name.startswith(prefix):
                if "Face" in slot.material.name:
                    face_mat = slot.material
                elif "Eye" in slot.material.name:
                    eye_mat = slot.material

        if "Socket_26" in mod:
            mod["Socket_26"] = 1
        if face_mat and "Socket_1" in mod:
            mod["Socket_1"] = face_mat
        if eye_mat and "Socket_2" in mod:
            mod["Socket_2"] = eye_mat
        if "Input_5" in mod:
            mod["Input_5"] = 0.075
        if "Input_3" in mod:
            mod["Input_3"] = 1
        if "Input_2_use_attribute" in mod:
            mod["Input_2_use_attribute"] = True
        if "Input_2_attribute_name" in mod:
            mod["Input_2_attribute_name"] = "COL0"

    # ========== GEOMETRY NODES RESET ==========

    # Resets and reconfigures all geometry node modifiers
    @staticmethod
    def reset_geometry_nodes(mesh: bpy.types.Object) -> str:
        GeometryManager._setup_geometry_nodes_for_mesh(mesh)
        return 'UEMODEL'

    # Removes existing vector/outline modifiers and recreates them
    @staticmethod
    def _setup_geometry_nodes_for_mesh(mesh: bpy.types.Object) -> None:
        from ..material.material_manager import MaterialManager
        mods_to_remove = [mod for mod in mesh.modifiers
                          if "[WW] Vectors" in mod.name or "[GW] Vectors" in mod.name or "Outlines" in mod.name]
        for mod in mods_to_remove:
            mesh.modifiers.remove(mod)

        shader_type = MaterialManager.detect_shader_type_by_helpers(mesh)

        if shader_type == 'ww':
            GeometryManager.create_modifier(
                mesh, "[WW] Vectors", mesh.name, GeometryManager.setup_light_direction_ww)
        else:
            GeometryManager.create_modifier(
                mesh, "[GW] Vectors", mesh.name, GeometryManager.setup_light_direction_gw)

        outline_base = "[WW] Outlines" if shader_type == 'ww' else "[GW] Outlines"
        GeometryManager.create_modifier(
            mesh, outline_base, mesh.name, GeometryManager.setup_outlines)
