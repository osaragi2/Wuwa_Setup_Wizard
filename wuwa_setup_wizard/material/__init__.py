# Material module initialization
# Contains material management and shader importing

from .material_manager import MaterialManager
from .shader_importer import ShaderImporter

__all__ = [
    'MaterialManager',
    'ShaderImporter',
]
