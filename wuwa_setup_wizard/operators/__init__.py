# Operators module initialization
# Contains all Blender operators for the addon

from .amd_fix_ops import WW_OT_AMDMaterialFix
from .camera_ops import WW_OT_SetSmartCamera
from .collection_ops import WW_OT_CreateCollection, WW_OT_PhysicalBoneArrangement
from .effect_ops import (
    WW_OT_AddTacetMark,
    WW_OT_AnimateTacetMark,
    WW_OT_ToggleOutlines,
    WW_OT_ToggleTwoColoredEyes,
)
from .global_settings_ops import (
    WW_OT_ApplyGlobalSettings,
    WW_OT_ResetGlobalSettings,
)
from .import_export import WW_OT_ImportModel, WW_OT_ImportTexture
from .mesh_ops import WW_OT_Join
from .misc_ops import WW_OT_PlanetShadowCatcher, WW_OT_ShaderSettings
from .quick_setup import WW_OT_QuickSetup
from .setup_ops import (
    WW_OT_SetDriver,
    WW_OT_SetupGeometryNodes,
    WW_OT_ToggleAnimationMode,
)
from .shader_ops import WW_OT_ApplyShader
from .texture_ops import WW_OT_TextureFormChange, WW_OT_TexturePipeline

__all__ = [
    'WW_OT_QuickSetup',
    'WW_OT_ImportModel',
    'WW_OT_ImportTexture',
    'WW_OT_ApplyShader',
    'WW_OT_TexturePipeline',
    'WW_OT_TextureFormChange',
    'WW_OT_ShaderSettings',
    'WW_OT_Join',
    'WW_OT_ToggleOutlines',
    'WW_OT_ToggleTwoColoredEyes',
    'WW_OT_AnimateTacetMark',
    'WW_OT_AddTacetMark',
    'WW_OT_SetDriver',
    'WW_OT_ToggleAnimationMode',
    'WW_OT_SetupGeometryNodes',
    'WW_OT_CreateCollection',
    'WW_OT_PhysicalBoneArrangement',
    'WW_OT_SetSmartCamera',
    'WW_OT_PlanetShadowCatcher',
    'WW_OT_AMDMaterialFix',
    'WW_OT_ApplyGlobalSettings',
    'WW_OT_ResetGlobalSettings',
]
