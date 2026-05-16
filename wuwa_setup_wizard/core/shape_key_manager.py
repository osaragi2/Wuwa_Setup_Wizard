import bpy


# ========== SHAPE KEY MANAGER ==========

# Handles shape key driver management
class ShapeKeyManager:

    # ========== CONSTANTS ==========

    protected_shape_keys = []

    # ========== DRIVER CLEARING ==========

    # Removes drivers from shape keys while preserving specified protected keys
    @staticmethod
    def clear_shape_key_drivers(mesh: bpy.types.Object, preserved_keys: set[str]) -> None:
        if not mesh.data.shape_keys:
            return

        shape_keys = mesh.data.shape_keys
        for key_block in shape_keys.key_blocks:
            if key_block.name in preserved_keys:
                continue

            data_path = f'key_blocks["{key_block.name}"].value'
            try:
                shape_keys.driver_remove(data_path)
            except (TypeError, RuntimeError):
                pass
