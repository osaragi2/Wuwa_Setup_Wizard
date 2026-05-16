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


# Returns path to shader .blend file based on selected shader type
def get_shader_path():
    if not os.path.exists(_shader_folder):
        return None

    available = get_available_shaders()

    shader_type = 'wuthering_waves'
    try:
        if hasattr(bpy.context, 'scene') and hasattr(bpy.context.scene, 'ww_properties'):
            shader_type = bpy.context.scene.ww_properties.shader_type
    except (AttributeError, TypeError):
        pass

    if available.get(shader_type):
        return os.path.join(_shader_folder, SHADER_FILES[shader_type])

    for key, is_available in available.items():
        if is_available:
            return os.path.join(_shader_folder, SHADER_FILES[key])

    return None
