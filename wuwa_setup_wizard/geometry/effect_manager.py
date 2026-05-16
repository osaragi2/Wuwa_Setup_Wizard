import time

import bpy

# Cache configuration
OUTLINE_CACHE_TTL = 3.0


# ========== EFFECT MANAGER ==========

# Manages visual effects including outlines, two-colored eyes, and tacet marks
class EffectManager:

    _outline_cache = {
        'mods': None,
        'state': None,
        'last_check': 0
    }

    # ========== OUTLINE EFFECTS ==========

    # Resets cached outline modifier list and state to force re-scan
    @classmethod
    def invalidate_outline_cache(cls) -> None:
        cls._outline_cache['mods'] = None
        cls._outline_cache['state'] = None
        cls._outline_cache['last_check'] = 0

    # Returns list of all outline geometry modifiers in scene (cached)
    @classmethod
    def get_outline_mods(cls, use_cache: bool = True) -> list[bpy.types.Modifier]:
        current_time = time.monotonic()
        cache = cls._outline_cache

        if use_cache and cache['mods'] is not None:
            if current_time - cache['last_check'] < OUTLINE_CACHE_TTL:
                # Validate cached mods are still valid
                valid_mods = []
                for mod in cache['mods']:
                    try:
                        _ = mod.name
                        if mod.id_data and mod.id_data.name in bpy.data.objects:
                            valid_mods.append(mod)
                    except (ReferenceError, AttributeError, UnicodeDecodeError):
                        pass
                if valid_mods:
                    return valid_mods

        mods = [mod for obj in bpy.data.objects if obj.type == 'MESH'
                for mod in obj.modifiers if mod.type == 'NODES' and "Outlines" in mod.name]

        cache['mods'] = mods
        cache['last_check'] = current_time
        return mods

    # Quick check if any outline modifier exists in scene
    @classmethod
    def has_any_outline_mod(cls) -> bool:
        return len(cls.get_outline_mods()) > 0

    # Returns current state of outline visibility (cached)
    @classmethod
    def get_outlines_state(cls) -> bool:
        mods = cls.get_outline_mods()
        return bool(mods) and any(mod.show_viewport for mod in mods)

    # Toggles visibility of all outline modifiers
    @classmethod
    def toggle_outlines(cls, state: bool) -> None:
        for mod in cls.get_outline_mods(use_cache=False):
            mod.show_viewport = mod.show_render = state
        cls.invalidate_outline_cache()

    # ========== TWO-COLORED EYES EFFECT ==========

    # Creates unique eye depth node group for two-colored eyes effect (Wuthering Waves only)
    @staticmethod
    def create_unique_eye_depth(mesh: bpy.types.Object) -> None:
        from ..core.object_manager import ObjectManager
        cleaned_mesh_name = ObjectManager._clean_mesh_name(mesh.name)
        name = f"Eye Depth {cleaned_mesh_name}"
        if name not in bpy.data.node_groups and "Eye Depth" in bpy.data.node_groups:
            new_tree = bpy.data.node_groups["Eye Depth"].copy()
            new_tree.name = name

        for slot in mesh.material_slots:
            if slot.material and "Eye" in slot.material.name and slot.material.node_tree:
                for node in slot.material.node_tree.nodes:
                    if node.type == 'GROUP' and node.node_tree and "Eye Depth" in node.node_tree.name:
                        node.node_tree = bpy.data.node_groups[name]

    # Returns whether two-colored eyes effect is active for mesh
    @staticmethod
    def get_two_colored_eyes_state(mesh: bpy.types.Object) -> bool:
        from ..material.material_manager import MaterialManager
        shader_type = MaterialManager.get_shader_type_from_materials(mesh)

        if shader_type == 'ww':
            from ..core.object_manager import ObjectManager
            cleaned_mesh_name = ObjectManager._clean_mesh_name(mesh.name)
            name = f"Eye Depth {cleaned_mesh_name}"
            if name in bpy.data.node_groups:
                for node in bpy.data.node_groups[name].nodes:
                    if node.type == 'UVMAP' and node.name == "UV Map":
                        return node.uv_map == "UV2"
        else:
            for slot in mesh.material_slots:
                if slot.material and "Eye" in slot.material.name and slot.material.node_tree:
                    for node in slot.material.node_tree.nodes:
                        if node.type == 'UVMAP' and node.name == "UV Map":
                            return node.uv_map == "UV2"
        return False

    # Toggles the two-colored eyes (heterochromia) effect on/off
    @staticmethod
    def toggle_two_colored_eyes(mesh: bpy.types.Object, state: bool) -> bool:
        from ..material.material_manager import MaterialManager
        outline_states = [(mod, mod.show_viewport) for mod in mesh.modifiers
                          if mod.type == 'NODES' and "Outlines" in mod.name]
        for mod, _ in outline_states:
            mod.show_viewport = False

        shader_type = MaterialManager.get_shader_type_from_materials(mesh)

        if shader_type == 'ww':
            EffectManager._toggle_two_colored_eyes_ww(mesh, state)
        else:
            EffectManager._toggle_two_colored_eyes_gw(mesh, state)

        for mod, orig_state in outline_states:
            mod.show_viewport = orig_state
        return True

    # Toggles heterochromia via UV Map switch in the Eye Depth node group (Wuthering Waves)
    @staticmethod
    def _toggle_two_colored_eyes_ww(mesh: bpy.types.Object, state: bool) -> None:
        from ..core.object_manager import ObjectManager
        cleaned_mesh_name = ObjectManager._clean_mesh_name(mesh.name)
        name = f"Eye Depth {cleaned_mesh_name}"

        if "Eye Depth" in bpy.data.node_groups:
            EffectManager.create_unique_eye_depth(mesh)
            if name in bpy.data.node_groups:
                for node in bpy.data.node_groups[name].nodes:
                    if node.type == 'UVMAP' and node.name == "UV Map":
                        node.uv_map = "UV2" if state else ""

    # Toggles heterochromia via UV Map switch directly in Eye material nodes (Gathering Wives)
    @staticmethod
    def _toggle_two_colored_eyes_gw(mesh: bpy.types.Object, state: bool) -> None:
        for slot in mesh.material_slots:
            if slot.material and "Eye" in slot.material.name and slot.material.node_tree:
                for node in slot.material.node_tree.nodes:
                    if node.type == 'UVMAP' and node.name == "UV Map":
                        node.uv_map = "UV2" if state else ""

    # ========== TACET MARK EFFECT ==========

    # Checks if the mesh has a Tacet Mark material
    @staticmethod
    def has_tacet_mark(mesh: bpy.types.Object) -> bool:
        if not mesh or not hasattr(mesh, 'material_slots'):
            return False
        for slot in mesh.material_slots:
            if slot.material and slot.material.node_tree:
                for node in slot.material.node_tree.nodes:
                    if node.type == 'GROUP' and node.node_tree and node.node_tree.name == "Tacet Mark":
                        return True
        return False

    # Gets node tree and socket info for Tacet Mark animation driver
    @staticmethod
    def _get_tacet_animation_data(mesh: bpy.types.Object) -> tuple[bpy.types.NodeTree | None,
                                                                   str | None, str | None]:
        for slot in mesh.material_slots:
            material = slot.material
            if material and material.node_tree:
                node_tree = material.node_tree
                for node in node_tree.nodes:
                    if node.type == 'GROUP' and node.node_tree and node.node_tree.name == "Tacet Mark":
                        if "Animate Tacet Mark" in node.inputs:
                            return node_tree, node.name, "Animate Tacet Mark"
        return None, None, None

    # Returns current Tacet Mark animation driver state
    @staticmethod
    def get_tacet_animation_state(mesh: bpy.types.Object) -> bool:
        node_tree, node_name, socket_name = EffectManager._get_tacet_animation_data(
            mesh)
        if node_tree:
            if not node_tree.animation_data:
                return False
            path = f'nodes["{node_name}"].inputs["{socket_name}"].default_value'
            for driver in node_tree.animation_data.drivers:
                if driver.data_path == path:
                    return True
        return False

    # Toggles Tacet Mark sparkling animation driver on/off
    @staticmethod
    def toggle_tacet_animation(mesh: bpy.types.Object, expression: str) -> bool:
        node_tree, node_name, socket_name = EffectManager._get_tacet_animation_data(
            mesh)
        if not node_tree:
            return False

        path = f'nodes["{node_name}"].inputs["{socket_name}"].default_value'

        is_driven = False
        if node_tree.animation_data:
            for driver in node_tree.animation_data.drivers:
                if driver.data_path == path:
                    is_driven = True
                    break

        if is_driven:
            node_tree.driver_remove(path)
        else:
            driver = node_tree.driver_add(path).driver
            driver.expression = expression
        return True

    # ========== ANIMATION MODE ==========

    # Shader output names
    WW_SHADER_OUTPUTS = ["Shader"]
    GW_SHADER_OUTPUTS = ["Standard"]

    # Returns whether animation mode is active for any mesh
    @staticmethod
    def get_animation_mode_state() -> bool:
        from ..core.object_manager import ObjectManager
        meshes = ObjectManager.get_processable_meshes()
        for mesh in meshes:
            if mesh.get("ww_animation_mode", False):
                return True
        return False

    # Toggles animation mode for all processable meshes
    @classmethod
    def toggle_animation_mode(cls, enable: bool) -> int:
        from ..core.object_manager import ObjectManager
        meshes = ObjectManager.get_processable_meshes()
        count = 0
        for mesh in meshes:
            if cls._toggle_mesh_animation_mode(mesh, enable):
                count += 1
        return count

    # Toggles animation mode for a single mesh
    @classmethod
    def _toggle_mesh_animation_mode(cls, mesh: bpy.types.Object, enable: bool) -> bool:
        if not mesh.material_slots:
            return False

        from ..material.material_manager import MaterialManager
        shader_type = MaterialManager.get_shader_type_from_materials(mesh)
        output_names = cls.GW_SHADER_OUTPUTS if shader_type == 'gw' else cls.WW_SHADER_OUTPUTS

        success = False
        for slot in mesh.material_slots:
            mat = slot.material
            if not mat or not mat.node_tree:
                continue

            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            output_node = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
            if not output_node:
                continue

            shader_group = None
            d_texture = None

            for node in nodes:
                if node.type == 'GROUP' and node.node_tree:
                    group_name = node.node_tree.name
                    if "Wuthering Waves" in group_name or "Gathering Wives" in group_name:
                        shader_group = node
                if node.type == 'TEX_IMAGE':
                    if node.label == "D" or (node.image and "_D" in node.image.name):
                        d_texture = node

            if not shader_group and not d_texture:
                continue

            if enable:
                if d_texture and output_node:
                    for link in list(links):
                        if link.to_node == output_node and link.to_socket.name == "Surface":
                            links.remove(link)

                    emit_node = nodes.get("Animation_Emit")
                    if not emit_node:
                        emit_node = nodes.new('ShaderNodeEmission')
                        emit_node.name = "Animation_Emit"
                        emit_node.location = (output_node.location.x - 200, output_node.location.y)

                    links.new(d_texture.outputs['Color'], emit_node.inputs['Color'])
                    links.new(emit_node.outputs['Emission'], output_node.inputs['Surface'])
                    success = True
            else:
                emit_node = nodes.get("Animation_Emit")
                if emit_node:
                    for link in list(links):
                        if link.to_node == output_node and link.to_socket.name == "Surface":
                            links.remove(link)
                    nodes.remove(emit_node)

                if shader_group and output_node:
                    if "Seethrough" in mat.name:
                        from .seethrough_manager import SeeThroughManager
                        restore_outputs = [SeeThroughManager.SEETHROUGH_OUTPUT] + output_names
                    else:
                        restore_outputs = output_names

                    for out_name in restore_outputs:
                        if out_name in shader_group.outputs:
                            links.new(shader_group.outputs[out_name], output_node.inputs['Surface'])
                            success = True
                            break

        mesh["ww_animation_mode"] = enable
        return success
