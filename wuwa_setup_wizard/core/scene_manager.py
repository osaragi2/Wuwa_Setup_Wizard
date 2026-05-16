from math import radians
from typing import Any

import bpy


# ========== CONSTANTS ==========

DEFAULT_VIEW_TRANSFORM = 'Standard'
RENDER_SETTINGS = {
    'use_border': True,
    'use_crop_to_border': True,
}
EEVEE_SSR_SETTINGS = {
    'use_ssr': True,
    'use_ssr_refraction': True,
    'use_ssr_halfres': True,
}
EEVEE_SHADOW_SETTINGS = {
    'shadow_cube_size': '512',
    'shadow_cascade_size': '4096',
}

GLOW_NODE_GROUP = "Glow & Eye FX / Rim Light / Notch Shadow"

AOV_PASSES = [
    ("Eye Transparency", 'COLOR'),
    ("Eye Transparency Mask", 'COLOR'),
    ("Face Mask", 'VALUE'),
    ("Light", 'COLOR'),
    ("Rim Light Mask", 'VALUE'),
    ("Shadow Color", 'COLOR'),
    ("Transparency Value", 'VALUE'),
]

PLANET_SCALE = (10, 10, 10)
SUN_POSITION = (0, 0, 2)
SUN_ROTATION = (radians(-45), 0, radians(130))
SUN_ENERGY = 10


# ========== SCENE MANAGER ==========

# Manages scene setup including render settings, passes, and compositor
class SceneManager:

    # ========== SCENE SETTINGS ==========

    # Configures render, SSR, and shadow settings for the scene
    @staticmethod
    def setup_scene_settings(context: bpy.types.Context) -> None:
        scene = context.scene
        scene.view_settings.view_transform = DEFAULT_VIEW_TRANSFORM
        scene.render.use_border = RENDER_SETTINGS['use_border']
        scene.render.use_crop_to_border = RENDER_SETTINGS['use_crop_to_border']

        SceneManager._setup_eevee_ssr(scene)
        SceneManager._setup_eevee_shadows(scene)
        context.preferences.filepaths.use_auto_save_temporary_files = True

    # Enables EEVEE screen-space reflections
    @staticmethod
    def _setup_eevee_ssr(scene: bpy.types.Scene) -> None:
        for setting, value in EEVEE_SSR_SETTINGS.items():
            if hasattr(scene.eevee, setting):
                setattr(scene.eevee, setting, value)

    # Configures EEVEE shadow resolution settings
    @staticmethod
    def _setup_eevee_shadows(scene: bpy.types.Scene) -> None:
        for setting, value in EEVEE_SHADOW_SETTINGS.items():
            if hasattr(scene.eevee, setting):
                setattr(scene.eevee, setting, value)

    # ========== AOV PASSES ==========

    # Creates AOV passes for glow, transparency, and shadow effects
    @staticmethod
    def setup_passes() -> None:
        if GLOW_NODE_GROUP not in bpy.data.node_groups:
            return

        vl = bpy.context.scene.view_layers["ViewLayer"]
        vl.use_pass_z = True
        vl.eevee.use_pass_transparent = True

        existing = {aov.name for aov in vl.aovs}
        for name, aov_type in AOV_PASSES:
            if name not in existing:
                aov = vl.aovs.add()
                aov.name = name
                aov.type = aov_type

    # ========== COMPOSITOR ==========

    # Sets up compositor with Glow & Eye FX node group
    @staticmethod
    def setup_compositor() -> None:
        if GLOW_NODE_GROUP not in bpy.data.node_groups:
            return

        scene = bpy.context.scene
        scene.use_nodes = True
        nodes = scene.node_tree.nodes
        links = scene.node_tree.links

        rl = SceneManager._get_or_create_node(nodes, 'R_LAYERS', 'CompositorNodeRLayers')
        glow = SceneManager._get_or_create_glow_node(nodes)

        if glow:
            SceneManager._link_glow_inputs(rl, glow, links)
            SceneManager._link_glow_outputs(nodes, glow, links)

    # Gets existing node by type or creates new one
    @staticmethod
    def _get_or_create_node(nodes: Any, node_type: str, new_type: str) -> Any:
        return next((n for n in nodes if n.type == node_type), None) or nodes.new(new_type)

    # Gets existing Glow node group or creates new one
    @staticmethod
    def _get_or_create_glow_node(nodes: Any) -> Any | None:
        glow = next(
            (n for n in nodes if n.type == 'GROUP' and n.node_tree and n.node_tree.name == GLOW_NODE_GROUP),
            None
        )
        if not glow:
            glow = nodes.new('CompositorNodeGroup')
            glow.node_tree = bpy.data.node_groups[GLOW_NODE_GROUP]
        return glow

    # Links Render Layers outputs to Glow node inputs
    @staticmethod
    def _link_glow_inputs(rl: Any, glow: Any, links: Any) -> None:
        rl_output_names = [out.name for out in rl.outputs]
        for inp in glow.inputs:
            if inp.name in rl_output_names:
                links.new(rl.outputs[inp.name], inp)

    # Links Glow node output to Composite and Viewer nodes
    @staticmethod
    def _link_glow_outputs(nodes: Any, glow: Any, links: Any) -> None:
        if "Image" not in glow.outputs:
            return

        composite = SceneManager._get_or_create_node(nodes, 'COMPOSITE', 'CompositorNodeComposite')
        viewer = SceneManager._get_or_create_node(nodes, 'VIEWER', 'CompositorNodeViewer')

        links.new(glow.outputs["Image"], composite.inputs["Image"])
        links.new(glow.outputs["Image"], viewer.inputs["Image"])

    # ========== PLANET SHADOW CATCHER ==========

    # Creates planet plane, material, and sun light for shadow casting
    @staticmethod
    def create_planet_shadow_catcher() -> bool:
        planet_obj = SceneManager._get_or_create_planet()
        SceneManager._setup_planet_material(planet_obj)
        SceneManager._setup_sun_light()
        return True

    # Gets or creates the Planet plane object
    @staticmethod
    def _get_or_create_planet() -> bpy.types.Object:
        planet_obj = bpy.data.objects.get("Planet")
        if not planet_obj:
            bpy.ops.mesh.primitive_plane_add(
                size=1, enter_editmode=False, align='WORLD', location=(0, 0, 0)
            )
            planet_obj = bpy.context.active_object
            planet_obj.name = "Planet"

        planet_obj.location = (0, 0, 0)
        planet_obj.rotation_euler = (0, 0, 0)
        planet_obj.scale = PLANET_SCALE
        return planet_obj

    # Creates or assigns the Planet material
    @staticmethod
    def _setup_planet_material(planet_obj: bpy.types.Object) -> None:
        material = bpy.data.materials.get("Planet")
        if not material:
            material = bpy.data.materials.new(name="Planet")
        material.use_nodes = True

        if len(planet_obj.data.materials) == 0:
            planet_obj.data.materials.append(material)
        else:
            planet_obj.data.materials[0] = material

    # Creates or configures the Sun light object
    @staticmethod
    def _setup_sun_light() -> None:
        sun_obj = bpy.data.objects.get("Sun")
        if not sun_obj:
            bpy.ops.object.light_add(type='SUN', location=SUN_POSITION, rotation=SUN_ROTATION)
            sun_obj = bpy.context.active_object
            sun_obj.name = "Sun"
        else:
            sun_obj.location = SUN_POSITION
            sun_obj.rotation_euler = SUN_ROTATION

        if sun_obj.type == 'LIGHT':
            sun_obj.data.energy = SUN_ENERGY
