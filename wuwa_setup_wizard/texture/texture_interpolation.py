import bpy


# ========== TEXTURE INTERPOLATION MANAGER ==========

# Handles texture interpolation mode for AMD GPU fixes
class TextureInterpolationManager:

    # ========== INTERPOLATION MODE ==========

    # Sets all texture nodes in scene to specified interpolation mode
    @staticmethod
    def set_interpolation_mode(mode: str) -> int:
        count = 0
        for material in bpy.data.materials:
            if material and material.use_nodes and material.node_tree:
                count += TextureInterpolationManager._process_node_tree(
                    material.node_tree, mode)
        return count

    # Recursively sets interpolation mode on all texture nodes in a node tree
    @staticmethod
    def _process_node_tree(node_tree: bpy.types.NodeTree, mode: str) -> int:
        count = 0
        for node in node_tree.nodes:
            if node.type == 'TEX_IMAGE' and hasattr(node, 'interpolation'):
                if node.interpolation != mode:
                    node.interpolation = mode
                    count += 1
            if node.type == 'GROUP' and node.node_tree:
                count += TextureInterpolationManager._process_node_tree(
                    node.node_tree, mode)
        return count
