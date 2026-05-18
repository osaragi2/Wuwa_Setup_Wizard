import os
import time

import bpy

_addon_dir = os.path.dirname(os.path.abspath(__file__))
_shader_folder = os.path.join(_addon_dir, "shader")

SHADER_FILES = {
    'wuthering_waves': 'Wuthering Waves.blend',
    'gathering_wives': 'Gathering Wives.blend'
}

_shader_cache = {
    'available': None,
    'last_check': 0,
    'cache_ttl': 5.0
}


# Checks which shaders are available (cached for 5 seconds)
def get_available_shaders():
    current_time = time.monotonic()
    if (_shader_cache['available'] is not None and
            current_time - _shader_cache['last_check'] < _shader_cache['cache_ttl']):
        return _shader_cache['available']

    available = {'wuthering_waves': False, 'gathering_wives': False}
    if os.path.exists(_shader_folder):
        for key, filename in SHADER_FILES.items():
            if os.path.exists(os.path.join(_shader_folder, filename)):
                available[key] = True

    _shader_cache['available'] = available
    _shader_cache['last_check'] = current_time
    return available


# Converts scene property value to internal shader key ('ww' or 'gw')
def prop_to_shader_key(prop_value: str) -> str:
    return 'gw' if prop_value == 'gathering_wives' else 'ww'


# Returns (filepath, prop_value) already synchronized — filepath always matches shader_type
def get_resolved_shader_type():
    if not os.path.exists(_shader_folder):
        return None, None

    available = get_available_shaders()

    # Read user preference
    preferred = 'gathering_wives'
    try:
        if hasattr(bpy.context, 'scene') and hasattr(bpy.context.scene, 'ww_properties'):
            preferred = bpy.context.scene.ww_properties.shader_type
    except (AttributeError, TypeError):
        pass

    # Use preferred if available
    if available.get(preferred):
        return os.path.join(_shader_folder, SHADER_FILES[preferred]), preferred

    # Fallback to any available shader — return its actual type so they always match
    for key, is_available in available.items():
        if is_available:
            return os.path.join(_shader_folder, SHADER_FILES[key]), key

    return None, None


# Returns path to shader .blend file based on selected shader type
def get_shader_path():
    filepath, _ = get_resolved_shader_type()
    return filepath
