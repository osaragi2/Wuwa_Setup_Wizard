# Wuthering Waves Setup Wizard

Blender addon for importing and setting up Wuthering Waves character models.

## Features

### Shader & Material
- Shader Selection (Wuthering Waves / Gathering Wives)
- Quick Setup
- Texture Pipeline
- Seethrough Mesh
- AMD Fix

### Rigging & Drivers
- Rigify Integration
- EyeTracker
- Face Panel
- Driver Setup

### Mesh Tools
- Join Mesh
- Outlines
- Geometry Nodes
- Collection Organization
- Physical Bone Arrangement

### Visual Effects
- Outlines Toggle
- Two-Colored Eyes
- Tacet Mark Animation
- Solid Mode

### Camera & Misc
- Smart Camera
- Planet Shadow Catcher

## File Structure

```
wuwa_setup_wizard/
├── __init__.py
├── addon_info.py
├── blender_manifest.toml
│
├── core/
│   ├── object_manager.py
│   ├── driver_manager.py
│   ├── helper_object_manager.py
│   ├── collection_manager.py
│   ├── scene_manager.py
│   ├── viewport_manager.py
│   ├── shape_key_manager.py
│   ├── camera_manager.py
│   └── utils.py
│
├── operators/
│   ├── quick_setup.py
│   ├── shader_ops.py
│   ├── setup_ops.py
│   ├── effect_ops.py
│   ├── camera_ops.py
│   ├── mesh_ops.py
│   ├── collection_ops.py
│   ├── misc_ops.py
│   ├── texture_ops.py
│   ├── import_export.py
│   └── amd_fix_ops.py
│
├── texture/
│   ├── texture_processor.py
│   └── texture_interpolation.py
│
├── material/
│   ├── material_manager.py
│   └── shader_importer.py
│
├── geometry/
│   ├── geometry_manager.py
│   ├── effect_manager.py
│   ├── mesh_manager.py
│   ├── seethrough_manager.py
│   └── vertex_processor.py
│
├── rigging/
│   ├── rigify_operator.py
│   ├── face_panel_creator.py
│   ├── face_panel_importer.py
│   └── bone_manager.py
│
├── ui/
│   ├── panel.py
│   ├── properties.py
│   └── ui_cache.py
│
└── shader/
    └── Gathering Wives.blend
```

## Credits

**Akatsuki** - Version 1.0
