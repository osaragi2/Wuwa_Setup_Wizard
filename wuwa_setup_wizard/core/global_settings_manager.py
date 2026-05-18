import bpy

from ..material.material_manager import MaterialManager


# ========== GLOBAL SETTINGS MANAGER ==========

# Manages real-time shader node group parameter adjustments for Expression, Shadow, and Skin Color settings
class GlobalSettingsManager:

    # Shader node group name prefixes used to identify the main character shader
    SHADER_GROUP_PREFIXES = ("Wuthering Waves", "Gathering Wives")

    # Part names to exclude for skin color settings
    SKIN_EXCLUDED_PARTS = ("Bangs", "Hair")

    # ========== NODE GROUP UTILITIES ==========

    # Finds the main shader node group in a material's node tree
    @staticmethod
    def get_main_node_group(material):
        if not material or not material.node_tree:
            return None
        for node in material.node_tree.nodes:
            if node.type == 'GROUP' and node.node_tree:
                if any(node.node_tree.name.startswith(prefix)
                       for prefix in GlobalSettingsManager.SHADER_GROUP_PREFIXES):
                    return node
        return None

    # Returns shader materials from the mesh filtered by part names
    @staticmethod
    def get_materials_by_part(mesh, parts=None, exclude=False):
        results = []
        if not mesh or not hasattr(mesh, 'material_slots'):
            return results

        for slot in mesh.material_slots:
            mat = slot.material
            if not mat:
                continue
            if not mat.name.startswith(tuple(MaterialManager.PREFIXES.values())):
                continue

            mat_suffix = mat.name.split(" - ", 1)[-1] if " - " in mat.name else ""

            # Skip non-Part materials (e.g., Seethrough)
            if "Seethrough" in mat_suffix:
                continue

            if parts is None:
                results.append(mat)
                continue

            if exclude:
                if not any(part in mat_suffix for part in parts):
                    results.append(mat)
            else:
                if any(part in mat_suffix for part in parts):
                    results.append(mat)

        return results

    # Reads the current value of an input from a shader node group
    @staticmethod
    def get_input_value(node_group, input_name):
        if not node_group or input_name not in node_group.inputs:
            return None
        return node_group.inputs[input_name].default_value

    # Writes a value to a shader node group input
    @staticmethod
    def set_input_value(node_group, input_name, value):
        if not node_group or input_name not in node_group.inputs:
            return False
        node_group.inputs[input_name].default_value = value
        return True

    # Checks if a given input name exists in any shader node group on the mesh
    @staticmethod
    def has_input(mesh, input_name, parts=None, exclude=False):
        materials = GlobalSettingsManager.get_materials_by_part(mesh, parts, exclude)
        for mat in materials:
            node = GlobalSettingsManager.get_main_node_group(mat)
            if node and input_name in node.inputs:
                return True
        return False

    # ========== EXPRESSION SETTINGS (FACE ONLY) ==========

    # Sets the Face Blush intensity on the Face material's shader node group
    @staticmethod
    def set_face_blush(mesh, value):
        materials = GlobalSettingsManager.get_materials_by_part(mesh, ["Face"])
        for mat in materials:
            node = GlobalSettingsManager.get_main_node_group(mat)
            GlobalSettingsManager.set_input_value(node, "Face Blush", value)

    # Sets the Face Shadow intensity on the Face material's shader node group
    @staticmethod
    def set_face_shadow(mesh, value):
        materials = GlobalSettingsManager.get_materials_by_part(mesh, ["Face"])
        for mat in materials:
            node = GlobalSettingsManager.get_main_node_group(mat)
            GlobalSettingsManager.set_input_value(node, "Face Shadow", value)

    # Sets the Face Shadow Atlas index on the Face material's shader node group
    @staticmethod
    def set_face_shadow_atlas(mesh, value):
        materials = GlobalSettingsManager.get_materials_by_part(mesh, ["Face"])
        for mat in materials:
            node = GlobalSettingsManager.get_main_node_group(mat)
            GlobalSettingsManager.set_input_value(node, "Face Shadow Atlas", value)

    # ========== SHADOW SETTINGS (ALL PARTS) ==========

    # Sets the Shadow Offset on all shader materials
    @staticmethod
    def set_shadow_offset(mesh, value):
        materials = GlobalSettingsManager.get_materials_by_part(mesh)
        for mat in materials:
            node = GlobalSettingsManager.get_main_node_group(mat)
            GlobalSettingsManager.set_input_value(node, "Shadow Offset", value)

    # Sets the Shadow Smooth on all shader materials
    @staticmethod
    def set_shadow_smooth(mesh, value):
        materials = GlobalSettingsManager.get_materials_by_part(mesh)
        for mat in materials:
            node = GlobalSettingsManager.get_main_node_group(mat)
            GlobalSettingsManager.set_input_value(node, "Shadow Smooth", value)

    # Sets the Cast Shadows value on all Part materials
    @staticmethod
    def set_cast_shadow(mesh, value):
        materials = GlobalSettingsManager.get_materials_by_part(mesh)
        for mat in materials:
            node = GlobalSettingsManager.get_main_node_group(mat)
            GlobalSettingsManager.set_input_value(node, "Cast Shadows", value)

    # ========== SKIN COLOR SETTINGS (ALL PARTS EXCEPT BANGS, HAIR) ==========

    # Sets the Skin Lit Color on all shader materials except Bangs and Hair
    @staticmethod
    def set_skin_lit_color(mesh, value):
        materials = GlobalSettingsManager.get_materials_by_part(
            mesh, list(GlobalSettingsManager.SKIN_EXCLUDED_PARTS), exclude=True)
        for mat in materials:
            node = GlobalSettingsManager.get_main_node_group(mat)
            if node and "Skin Lit Color" in node.inputs:
                input_socket = node.inputs["Skin Lit Color"]
                for i in range(min(len(value), len(input_socket.default_value))):
                    input_socket.default_value[i] = value[i]

    # Sets the Skin Midtone Color on all shader materials except Bangs and Hair
    @staticmethod
    def set_skin_midtone_color(mesh, value):
        materials = GlobalSettingsManager.get_materials_by_part(
            mesh, list(GlobalSettingsManager.SKIN_EXCLUDED_PARTS), exclude=True)
        for mat in materials:
            node = GlobalSettingsManager.get_main_node_group(mat)
            if node and "Skin Midtone Color" in node.inputs:
                input_socket = node.inputs["Skin Midtone Color"]
                for i in range(min(len(value), len(input_socket.default_value))):
                    input_socket.default_value[i] = value[i]

    # Sets the Skin Shadow Color on all shader materials except Bangs and Hair
    @staticmethod
    def set_skin_shadow_color(mesh, value):
        materials = GlobalSettingsManager.get_materials_by_part(
            mesh, list(GlobalSettingsManager.SKIN_EXCLUDED_PARTS), exclude=True)
        for mat in materials:
            node = GlobalSettingsManager.get_main_node_group(mat)
            if node and "Skin Shadow Color" in node.inputs:
                input_socket = node.inputs["Skin Shadow Color"]
                for i in range(min(len(value), len(input_socket.default_value))):
                    input_socket.default_value[i] = value[i]

    # Sets the Skin Edge Color on all shader materials except Bangs and Hair
    @staticmethod
    def set_skin_edge_color(mesh, value):
        materials = GlobalSettingsManager.get_materials_by_part(
            mesh, list(GlobalSettingsManager.SKIN_EXCLUDED_PARTS), exclude=True)
        for mat in materials:
            node = GlobalSettingsManager.get_main_node_group(mat)
            if node and "Skin Edge Color" in node.inputs:
                input_socket = node.inputs["Skin Edge Color"]
                for i in range(min(len(value), len(input_socket.default_value))):
                    input_socket.default_value[i] = value[i]

    # ========== GW SHADOW SETTINGS (Gathering Wives materials only) ==========

    # Returns only materials whose shader node group name starts with "Gathering Wives"
    @staticmethod
    def get_gw_materials(mesh):
        results = []
        if not mesh or not hasattr(mesh, 'material_slots'):
            return results
        for slot in mesh.material_slots:
            mat = slot.material
            if not mat or not mat.node_tree:
                continue
            for node in mat.node_tree.nodes:
                if (node.type == 'GROUP' and node.node_tree
                        and node.node_tree.name.startswith("Gathering Wives")):
                    results.append(mat)
                    break
        return results

    # Sets Shadow Position on all Gathering Wives materials
    @staticmethod
    def set_gw_shadow_position(mesh, value):
        for mat in GlobalSettingsManager.get_gw_materials(mesh):
            node = GlobalSettingsManager.get_main_node_group(mat)
            GlobalSettingsManager.set_input_value(node, "Shadow Position", value)

    # Sets Shadow Softness on all Gathering Wives materials
    @staticmethod
    def set_gw_shadow_softness(mesh, value):
        for mat in GlobalSettingsManager.get_gw_materials(mesh):
            node = GlobalSettingsManager.get_main_node_group(mat)
            GlobalSettingsManager.set_input_value(node, "Shadow Softness", value)

    # Sets Enable Cast Shadows on all Gathering Wives materials
    @staticmethod
    def set_gw_cast_shadow(mesh, value):
        for mat in GlobalSettingsManager.get_gw_materials(mesh):
            node = GlobalSettingsManager.get_main_node_group(mat)
            GlobalSettingsManager.set_input_value(node, "Enable Cast Shadows", value)

    # ========== GW SKIN COLOR SETTINGS (Gathering Wives materials only) ==========

    # Sets Base Color on all Gathering Wives materials
    @staticmethod
    def set_gw_base_color(mesh, value):
        for mat in GlobalSettingsManager.get_gw_materials(mesh):
            node = GlobalSettingsManager.get_main_node_group(mat)
            if node and "Base Color" in node.inputs:
                socket = node.inputs["Base Color"]
                for i in range(min(len(value), len(socket.default_value))):
                    socket.default_value[i] = value[i]

    # Sets Shadow Color on all Gathering Wives materials
    @staticmethod
    def set_gw_shadow_color(mesh, value):
        for mat in GlobalSettingsManager.get_gw_materials(mesh):
            node = GlobalSettingsManager.get_main_node_group(mat)
            if node and "Shadow Color" in node.inputs:
                socket = node.inputs["Shadow Color"]
                for i in range(min(len(value), len(socket.default_value))):
                    socket.default_value[i] = value[i]

    # Sets Skin Color Multiplier on all Gathering Wives materials
    @staticmethod
    def set_gw_skin_color_multiplier(mesh, value):
        for mat in GlobalSettingsManager.get_gw_materials(mesh):
            node = GlobalSettingsManager.get_main_node_group(mat)
            if node and "Skin Color Multiplier" in node.inputs:
                socket = node.inputs["Skin Color Multiplier"]
                for i in range(min(len(value), len(socket.default_value))):
                    socket.default_value[i] = value[i]

    # Checks if any Gathering Wives material has the given input
    @staticmethod
    def has_gw_input(mesh, input_name):
        for mat in GlobalSettingsManager.get_gw_materials(mesh):
            node = GlobalSettingsManager.get_main_node_group(mat)
            if node and input_name in node.inputs:
                return True
        return False
