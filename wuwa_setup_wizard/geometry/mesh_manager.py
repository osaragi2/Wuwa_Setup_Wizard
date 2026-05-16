import re
from typing import Any
import bpy

from ..core.object_manager import ObjectManager
from ..core.utils import Utils


# ========== MESH MANAGER ==========

# Handles mesh joining and part detection
class MeshManager:

    # ========== CONSTANTS ==========

    SUFFIX_PATTERNS = [
        (r'^(.+?)\.(\d{3,})$', 'blender_numeric'),
        (r'^(.+?)_(\d+)$', 'underscore_numeric'),
        (r'^(.+?) (Body|Hair|Cloth|Skirt|Face|Eye|Weapon)$', 'part_type'),
    ]

    # ========== PART DETECTION ==========

    # Finds all mesh parts that can be joined with the selected object
    @staticmethod
    def find_joinable_parts(obj: bpy.types.Object) -> dict[str, Any] | None:
        if not obj or obj.type != 'MESH':
            return None

        obj_name = obj.name
        base_name = None
        match_type = None

        for pattern, ptype in MeshManager.SUFFIX_PATTERNS:
            match = re.match(pattern, obj_name, re.IGNORECASE)
            if match:
                base_name = match.group(1)
                match_type = ptype
                break

        if not base_name:
            base_name = obj_name
            match_type = 'exact'

        parts = []
        for o in bpy.data.objects:
            if o.type != 'MESH':
                continue

            if match_type == 'blender_numeric':
                if o.name == base_name or re.match(rf'^{re.escape(base_name)}\.(\d{{3,}})$', o.name):
                    parts.append(o)
            elif match_type == 'underscore_numeric':
                if o.name == base_name or re.match(rf'^{re.escape(base_name)}_(\d+)$', o.name):
                    parts.append(o)
            elif match_type == 'part_type':
                if re.match(rf'^{re.escape(base_name)} (Body|Hair|Cloth|Skirt|Face|Eye|Weapon)$',
                            o.name, re.IGNORECASE):
                    parts.append(o)
            else:
                if o.name == base_name or re.match(rf'^{re.escape(base_name)}\.(\d{{3,}})$', o.name):
                    parts.append(o)

        if len(parts) > 1:
            return {'base_name': base_name, 'parts': parts, 'type': match_type}
        return None

    # ========== MESH JOINING ==========

    # Joins all matching mesh parts into a single object
    @staticmethod
    def join_mesh(context: bpy.types.Context, selected_part: bpy.types.Object) -> dict[str, Any]:
        result = MeshManager.find_joinable_parts(selected_part)

        if not result or len(result['parts']) <= 1:
            return {'status': 'SINGLE', 'name': None, 'count': 0}

        parts = result['parts']
        base_name = result['base_name']

        Utils.ensure_object_mode()
        bpy.ops.object.select_all(action='DESELECT')

        active_part = next((p for p in parts if p.name == base_name), parts[0])

        for p in parts:
            p.hide_set(False)
            p.select_set(True)

        context.view_layer.objects.active = active_part

        try:
            bpy.ops.object.join()
        except RuntimeError:
            return {'status': 'ERROR', 'name': None, 'count': 0}

        joined_obj = context.active_object
        joined_obj.name = base_name

        ObjectManager.clear_cache()
        ObjectManager.refresh_context()

        return {'status': 'JOINED', 'name': base_name, 'count': len(parts)}
