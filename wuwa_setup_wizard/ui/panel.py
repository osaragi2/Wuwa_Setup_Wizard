import bpy
from bpy.types import Panel

from ..addon_info import get_shader_path
from ..core.object_manager import ObjectManager
from ..geometry.effect_manager import EffectManager
from ..material.material_manager import MaterialManager
from ..texture.texture_processor import TextureProcessor
from .ui_cache import UICache


# ========== MAIN PANEL ==========

# Main addon panel in the sidebar
class WW_PT_ShaderPanel(Panel):
    bl_label = "Wuthering Waves Shader Tool"
    bl_idname = "WW_PT_shader_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Wuthering Waves"

    # Draws the complete sidebar UI with all sections
    def draw(self, context):
        layout = self.layout
        active_obj = context.active_object
        ww_props = context.scene.ww_properties

        is_mesh = bool(active_obj and active_obj.type == 'MESH')
        has_ww_mats = False
        if is_mesh:
            has_ww_mats = UICache.get(
                'has_ww_materials',
                lambda: MaterialManager.has_ww_materials(active_obj),
                active_obj
            )

        self._draw_header(layout, active_obj)
        self._draw_shader_selector(layout, ww_props)
        self._draw_quick_setup(layout, ww_props)
        self._draw_character_setup(layout, ww_props, is_mesh)
        self._draw_material_pipeline(layout, ww_props, active_obj, is_mesh, has_ww_mats)
        self._draw_texture_pipeline(layout, ww_props, active_obj, is_mesh, has_ww_mats)
        self._draw_character_rig(layout, ww_props, active_obj)
        self._draw_global_settings(layout, ww_props, is_mesh, has_ww_mats)
        self._draw_advanced_tools(layout, ww_props, active_obj, is_mesh, has_ww_mats)
        self._draw_visual_effects(layout, ww_props, active_obj, is_mesh, has_ww_mats)
        self._draw_smart_camera(layout, ww_props, context)
        self._draw_amd_fix(layout, ww_props)
        self._draw_footer(layout)

    # ========== HEADER ==========

    # Draws the panel title and active object status indicator
    def _draw_header(self, layout, active_obj):
        header = layout.box()
        header.use_property_split = False
        header.use_property_decorate = False
        title_row = header.row(align=True)
        title_row.scale_y = 1.2
        title_row.alignment = 'CENTER'
        title_row.label(text="⚡ Wuthering Waves Studio")
        layout.separator(factor=0.5)

        main_col = layout.column(align=True)
        status = main_col.box()
        status.use_property_split = False
        status_row = status.row(align=True)
        status_row.scale_y = 0.9
        if active_obj:
            status_row.label(text=f"✓ Active: {active_obj.name}", icon='OBJECT_DATA')
        else:
            status_row.label(text="✗ No Active Object", icon='OBJECT_DATA')
        layout.separator(factor=0.5)

    # Checks available shaders and returns whether any shader exists
    def _draw_shader_selector(self, layout, ww_props):
        from ..addon_info import get_available_shaders

        available_shaders = get_available_shaders()
        has_ww = available_shaders['wuthering_waves']
        has_gw = available_shaders['gathering_wives']
        has_any_shader = has_ww or has_gw

        return has_any_shader

    # ========== QUICK SETUP ==========

    # Draws the Quick Setup section with options and run button
    def _draw_quick_setup(self, layout, ww_props):
        from ..addon_info import get_available_shaders

        available_shaders = get_available_shaders()
        has_any_shader = available_shaders['wuthering_waves'] or available_shaders['gathering_wives']
        shader_path = get_shader_path()

        main_col = layout.column(align=True)
        quick_setup_box = main_col.box()
        quick_setup_box.enabled = has_any_shader

        header_row = quick_setup_box.row(align=True)
        header_row.label(text="Quick Setup", icon='AUTO')
        settings_col = header_row.row(align=True)
        settings_col.alignment = 'RIGHT'
        settings_col.enabled = has_any_shader
        settings_col.operator("ww.shader_settings", text="", icon='PREFERENCES')

        options_container = quick_setup_box.box()
        options_col = options_container.column(align=True)
        options_col.prop(ww_props, "quick_setup_rigify")

        face_options_col = options_col.column(align=True)
        face_options_col.enabled = ww_props.quick_setup_rigify
        face_options_col.prop(ww_props, "quick_setup_create_face")
        face_options_col.prop(ww_props, "quick_setup_import_face")

        run_row = quick_setup_box.row()
        run_row.enabled = bool(shader_path)
        run_row.operator("ww.quick_setup", text="Run", icon='PLAY')

    # ========== CHARACTER SETUP ==========

    # Draws the character setup section with model import button
    def _draw_character_setup(self, layout, ww_props, is_mesh):
        main_col = layout.column(align=True)
        setup_box = main_col.box()
        header_row = setup_box.row(align=True)
        header_row.prop(ww_props, "show_character_setup", text="",
                        icon='TRIA_DOWN' if ww_props.show_character_setup else 'TRIA_RIGHT', emboss=False)
        header_row.label(text="Set Up Character", icon='OUTLINER_OB_ARMATURE')

        if ww_props.show_character_setup:
            setup_col = setup_box.column(align=True)
            setup_col.scale_y = 1.0
            setup_col.operator("ww.import_model", text="Import Model", icon='IMPORT')

    # ========== MATERIAL PIPELINE ==========

    # Draws the material pipeline section with shader and texture import buttons
    def _draw_material_pipeline(self, layout, ww_props, active_obj, is_mesh, has_ww_mats):
        main_col = layout.column(align=True)
        shader_box = main_col.box()
        header_row = shader_box.row(align=True)
        header_row.prop(ww_props, "show_material_pipeline", text="",
                        icon='TRIA_DOWN' if ww_props.show_material_pipeline else 'TRIA_RIGHT', emboss=False)
        header_row.label(text="Material Pipeline", icon='MATERIAL')

        if not ww_props.show_material_pipeline:
            return

        shader_col = shader_box.column(align=True)
        shader_col.scale_y = 1.0
        shader_col.enabled = is_mesh

        is_part_mesh = False
        if shader_col.enabled and active_obj:
            is_part_mesh = any(active_obj.name.endswith(suffix)
                               for suffix in [" Body", " Hair", " Cloth", " Skirt"])

        shader_row = shader_col.row(align=True)
        shader_row.enabled = not is_part_mesh

        if has_ww_mats:
            shader_row.enabled = False
            shader_row.operator("ww.apply_shader", text="Shader Applied", icon='CHECKMARK')
        else:
            shader_path = get_shader_path()
            shader_row.enabled = bool(shader_path) and not is_part_mesh
            shader_row.operator("ww.apply_shader", text="Apply Shader", icon='NODE_MATERIAL')

        texture_row = shader_col.row(align=True)
        texture_row.enabled = has_ww_mats
        texture_row.operator("ww.import_texture", text="Import Textures", icon='TEXTURE_DATA')

    # ========== TEXTURE PIPELINE ==========

    # Draws the texture variant pipeline with Status and Form sub-sections
    def _draw_texture_pipeline(self, layout, ww_props, active_obj, is_mesh, has_ww_mats):
        main_col = layout.column(align=True)
        texture_pipeline_box = main_col.box()
        header_row = texture_pipeline_box.row(align=True)
        header_row.prop(ww_props, "show_texture_pipeline", text="",
                        icon='TRIA_DOWN' if ww_props.show_texture_pipeline else 'TRIA_RIGHT', emboss=False)
        header_row.label(text="Texture Pipeline", icon='IMAGE_DATA')

        if not ww_props.show_texture_pipeline:
            return

        texture_pipeline_col = texture_pipeline_box.column(align=True)
        texture_pipeline_col.scale_y = 1.0
        texture_pipeline_col.enabled = is_mesh and has_ww_mats

        availability = {'normal': False, 'injured': False, 'wet': False}
        current_mode = None
        if texture_pipeline_col.enabled:
            availability = UICache.get(
                'texture_availability',
                lambda: TextureProcessor.check_texture_availability(active_obj),
                active_obj
            )
            current_mode = UICache.get(
                'pipeline_state',
                lambda: TextureProcessor.get_current_pipeline_state(active_obj),
                active_obj
            )

        # Status sub-section
        status_box = texture_pipeline_col.box()
        status_box.label(text="Status", icon='RADIOBUT_ON')
        pipeline_row = status_box.row(align=True)
        self._draw_pipeline_button(pipeline_row, availability['normal'], 'normal', current_mode)
        self._draw_pipeline_button(pipeline_row, availability['injured'], 'injured', current_mode)
        self._draw_pipeline_button(pipeline_row, availability['wet'], 'wet', current_mode, ['wet_02', 'wet_03'])

        # Form sub-section
        form_box = texture_pipeline_col.box()
        form_box.label(text="Form", icon='RENDERLAYERS')
        form_current, form_total = 0, 0
        if texture_pipeline_col.enabled:
            form_current, form_total = UICache.get(
                'texture_form_info',
                lambda: TextureProcessor.get_current_form_info(active_obj),
                active_obj
            )
        form_row = form_box.row(align=True)
        change_row = form_row.row(align=True)
        change_row.enabled = form_total > 1
        change_row.operator("ww.texture_form_change", text="Change", icon='LOOP_FORWARDS')
        label_row = form_row.row(align=True)
        label_row.alignment = 'RIGHT'
        if form_total > 1:
            label_row.label(text=f"Form: {form_current}/{form_total}")
        else:
            label_row.label(text="Form: —")

    # Draws a single texture pipeline toggle button with active state highlight
    def _draw_pipeline_button(self, row, enabled, pipeline_type, current_mode, active_modes=None):
        op_row = row.row(align=True)
        op_row.enabled = enabled
        if active_modes is None:
            active_modes = [pipeline_type]
        depress = current_mode in active_modes
        op = op_row.operator("ww.texture_pipeline", text=pipeline_type.capitalize(), depress=depress)
        op.pipeline_type = pipeline_type

    # ========== CHARACTER RIG ==========

    # Draws the character rig section with rigify and face panel buttons
    def _draw_character_rig(self, layout, ww_props, active_obj):
        main_col = layout.column(align=True)
        rig_section = main_col.box()
        header_row = rig_section.row(align=True)
        header_row.prop(ww_props, "show_character_rig", text="",
                        icon='TRIA_DOWN' if ww_props.show_character_rig else 'TRIA_RIGHT', emboss=False)
        header_row.label(text="Character Rig", icon='POSE_HLT')

        if not ww_props.show_character_rig:
            return

        rig_col = rig_section.column(align=True)
        rig_col.scale_y = 1.0

        rig_info = self._get_rig_info(active_obj)
        rig_col.enabled = rig_info['enabled']

        rigify_row = rig_col.row(align=True)
        rigify_row.enabled = not rig_info['is_rigified'] and not rig_info['is_auto_rigged']
        rigify_row.operator("ww.rigify_armature", text="Rigify Armature", icon='ARMATURE_DATA')

        self._draw_face_panel_button(rig_col, rig_info)
        self._draw_import_face_button(rig_col, rig_info)

    # Gathers rig status information for the active object
    def _get_rig_info(self, active_obj):
        info = {
            'enabled': False,
            'armature': None,
            'is_rigified': False,
            'is_auto_rigged': False,
            'is_part_mesh': False,
            'mesh_for_face': None
        }

        if not active_obj:
            return info

        is_face_panel, face_panel_armature = self._check_face_panel(active_obj)
        info['enabled'] = active_obj.type in {'MESH', 'ARMATURE'} or is_face_panel

        if is_face_panel and face_panel_armature:
            info['armature'] = self._find_armature_for_face_panel(face_panel_armature, active_obj)
        elif active_obj.type == 'MESH':
            info['armature'] = ObjectManager.get_armature(active_obj)
            info['is_part_mesh'] = any(
                active_obj.name.endswith(suffix) for suffix in [" Body", " Hair", " Cloth", " Skirt"]
            )
        elif active_obj.type == 'ARMATURE':
            info['armature'] = active_obj

        if info['armature']:
            info['is_rigified'] = info['armature'].name.startswith("RIG-")
            info['is_auto_rigged'] = "rig" in info['armature'].name.lower()
            info['mesh_for_face'] = ObjectManager.get_mesh_from_armature(info['armature'])

        return info

    # Checks if the active object belongs to a face panel collection
    def _check_face_panel(self, active_obj):
        is_face_panel = False
        face_panel_armature = None

        if (active_obj.name.startswith("Face Panel")
                or (active_obj.users_collection and any(
                    "Face Panel" in c.name
                    for c in active_obj.users_collection))):
            is_face_panel = True
            if active_obj.type == 'ARMATURE':
                face_panel_armature = active_obj
            else:
                for coll in active_obj.users_collection:
                    if "Face Panel" in coll.name:
                        for obj in coll.objects:
                            if obj.type == 'ARMATURE':
                                face_panel_armature = obj
                                break

        return is_face_panel, face_panel_armature

    # Finds the character armature associated with a face panel object
    def _find_armature_for_face_panel(self, face_panel_armature, active_obj):
        # Searches for armature linked to face panel via mesh property or constraint
        def find_face_panel_armature():
            for obj in bpy.data.objects:
                if (obj.type == 'MESH'
                        and obj.get("face_panel_armature")
                        == face_panel_armature.name):
                    return ObjectManager.get_armature(obj)
            for obj in bpy.data.objects:
                if obj.name.startswith("Face Panel"):
                    for con in obj.constraints:
                        if (con.type == 'CHILD_OF'
                                and con.target):
                            return con.target
            return None

        return UICache.get(
            'face_panel_armature',
            find_face_panel_armature, active_obj)

    # Draws the Create Face Panel button with rig type and shape key checks
    def _draw_face_panel_button(self, rig_col, rig_info):
        face_row = rig_col.row(align=True)
        has_shape_keys = bool(rig_info['mesh_for_face'] and rig_info['mesh_for_face'].data.shape_keys)
        has_compatible_rig = rig_info['is_rigified'] or rig_info['is_auto_rigged']
        face_row.enabled = has_compatible_rig and not rig_info['is_part_mesh'] and has_shape_keys
        face_row.operator("ww.create_face_panel", text="Create Face Panel", icon='SHAPEKEY_DATA')

    # Draws the Import Face Panel button with rig type and shape key checks
    def _draw_import_face_button(self, rig_col, rig_info):
        import_row = rig_col.row(align=True)
        has_shape_keys = bool(rig_info['mesh_for_face'] and rig_info['mesh_for_face'].data.shape_keys)
        has_compatible_rig = rig_info['is_rigified'] or rig_info['is_auto_rigged']
        import_row.enabled = has_compatible_rig and not rig_info['is_part_mesh'] and has_shape_keys
        import_row.operator("ww.import_face_panel", text="Import Face Panel", icon='FILE_NEW')

    # ========== GLOBAL SETTINGS ==========

    # Draws the global settings section with Expression, Shadow, and Skin Color controls
    def _draw_global_settings(self, layout, ww_props, is_mesh, has_ww_mats):
        if not (is_mesh and has_ww_mats):
            return

        from ..core.global_settings_manager import GlobalSettingsManager

        mesh = bpy.context.active_object

        main_col = layout.column(align=True)
        gs_section = main_col.box()
        header_row = gs_section.row(align=True)
        header_row.prop(ww_props, "show_global_settings", text="",
                        icon='TRIA_DOWN' if ww_props.show_global_settings else 'TRIA_RIGHT', emboss=False)
        header_row.label(text="Global Settings", icon='WORLD_DATA')
        reset_col = header_row.row(align=True)
        reset_col.alignment = 'RIGHT'
        reset_col.operator("ww.reset_global_settings", text="", icon='LOOP_BACK')

        if not ww_props.show_global_settings:
            return

        gs_col = gs_section.column(align=True)
        gs_col.scale_y = 1.0
        face_parts = ["Face"]
        excluded_skin = list(GlobalSettingsManager.SKIN_EXCLUDED_PARTS)

        # Expression sub-section (Face inputs)
        expr_items = [
            ("gs_face_blush", "Face Blush", True),
            ("gs_face_shadow", "Face Shadow", True),
            ("gs_face_shadow_atlas", "Face Shadow Atlas", False),
        ]
        valid_expr = [(p, s) for p, inp, s in expr_items
                      if GlobalSettingsManager.has_input(mesh, inp, face_parts)]
        if valid_expr:
            expr_box = gs_col.box()
            expr_box.label(text="Expression", icon='FACE_MAPS')
            expr_col = expr_box.column(align=True)
            for prop_name, use_slider in valid_expr:
                expr_col.prop(ww_props, prop_name, slider=use_slider)

        # Shadow sub-section (all Part materials)
        has_offset = GlobalSettingsManager.has_input(mesh, "Shadow Offset")
        has_smooth = GlobalSettingsManager.has_input(mesh, "Shadow Smooth")
        has_cast = GlobalSettingsManager.has_input(mesh, "Cast Shadows")

        if has_offset or has_smooth or has_cast:
            shadow_box = gs_col.box()
            shadow_box.label(text="Shadow", icon='LIGHT_SUN')
            shadow_col = shadow_box.column(align=True)
            if has_offset and has_smooth:
                shadow_row = shadow_col.row(align=True)
                shadow_row.prop(ww_props, "gs_shadow_offset", text="Offset")
                shadow_row.prop(ww_props, "gs_shadow_smooth", text="Smooth")
            elif has_offset:
                shadow_col.prop(ww_props, "gs_shadow_offset")
            elif has_smooth:
                shadow_col.prop(ww_props, "gs_shadow_smooth")
            if has_cast:
                shadow_col.prop(ww_props, "gs_cast_shadow", slider=True)

        # Skin Color sub-section (all parts except Bangs, Hair)
        has_lit = GlobalSettingsManager.has_input(mesh, "Skin Lit Color", excluded_skin, exclude=True)
        has_midtone = GlobalSettingsManager.has_input(mesh, "Skin Midtone Color", excluded_skin, exclude=True)
        has_shadow = GlobalSettingsManager.has_input(mesh, "Skin Shadow Color", excluded_skin, exclude=True)
        has_edge = GlobalSettingsManager.has_input(mesh, "Skin Edge Color", excluded_skin, exclude=True)

        if has_lit or has_midtone or has_shadow or has_edge:
            skin_box = gs_col.box()
            skin_box.label(text="Skin Color", icon='COLOR')
            skin_col = skin_box.column(align=True)
            if has_lit:
                lit_row = skin_col.row(align=True)
                lit_row.label(text="Lit")
                lit_row.prop(ww_props, "gs_skin_lit_color", text="")
            if has_midtone:
                midtone_row = skin_col.row(align=True)
                midtone_row.label(text="Midtone")
                midtone_row.prop(ww_props, "gs_skin_midtone_color", text="")
            if has_shadow:
                shadow_row = skin_col.row(align=True)
                shadow_row.label(text="Shadow")
                shadow_row.prop(ww_props, "gs_skin_shadow_color", text="")
            if has_edge:
                edge_row = skin_col.row(align=True)
                edge_row.label(text="Edge")
                edge_row.prop(ww_props, "gs_skin_edge_color", text="")

    # ========== ADVANCED TOOLS ==========

    # Draws the advanced tools section with driver, geometry, and utility buttons
    def _draw_advanced_tools(self, layout, ww_props, active_obj, is_mesh, has_ww_mats):
        main_col = layout.column(align=True)
        tools_section = main_col.box()
        header_row = tools_section.row(align=True)
        header_row.prop(ww_props, "show_advanced_tools", text="",
                        icon='TRIA_DOWN' if ww_props.show_advanced_tools else 'TRIA_RIGHT', emboss=False)
        header_row.label(text="Advanced Tools", icon='TOOL_SETTINGS')

        if not ww_props.show_advanced_tools:
            return

        tools_col = tools_section.column(align=True)
        tools_col.scale_y = 1.0

        is_helper_obj = self._is_helper_object(active_obj)
        driver_enabled = bool(
            active_obj and (active_obj.type in {'MESH', 'ARMATURE'} or is_helper_obj)
        )
        if driver_enabled and active_obj.type == 'MESH' and not is_helper_obj:
            driver_enabled = has_ww_mats

        geometry_nodes_enabled = driver_enabled

        self._draw_tool_row(tools_col, "ww.set_driver", "Set Driver", 'DRIVER', driver_enabled)

        from ..geometry.effect_manager import EffectManager
        anim_mode = EffectManager.get_animation_mode_state()
        anim_text = f"Animation Mode [{'On' if anim_mode else 'Off'}]"
        self._draw_tool_row(tools_col, "ww.toggle_animation_mode", anim_text, 'RENDER_ANIMATION', True)

        tacet_stage = active_obj.get("ww_tacet_mark_stage", 0) if active_obj else 0
        if tacet_stage == 0:
            tacet_text = "Add Tacet Mark"
        elif tacet_stage == 1:
            tacet_text = "Tacet Mark [UV]"
        else:
            tacet_text = "Tacet Mark [Complete]"
        tacet_enabled = is_mesh
        if tacet_enabled and tacet_stage == 0:
            if has_ww_mats:
                has_tacet = any(s.material and "Tacet Mark" in s.material.name for s in active_obj.material_slots)
                tacet_enabled = not has_tacet
            else:
                tacet_enabled = False
        self._draw_tool_row(
            tools_col,
            "ww.add_tacet_mark",
            tacet_text,
            'OUTLINER_OB_LIGHT',
            tacet_enabled or tacet_stage > 0)
        self._draw_tool_row(tools_col, "ww.join_mesh", "Join Mesh", 'AUTOMERGE_ON', is_mesh)
        self._draw_tool_row(
            tools_col,
            "ww.create_collection",
            "Create Collection",
            'OUTLINER_COLLECTION',
            driver_enabled)
        self._draw_tool_row(
            tools_col,
            "ww.setup_geometry_nodes",
            "Set Up Geometry Nodes",
            'NODETREE',
            geometry_nodes_enabled)
        self._draw_tool_row(tools_col, "ww.physical_bone_arrangement", "Bone Arrangement", 'PHYSICS',
                            bool(active_obj and active_obj.type == 'ARMATURE'))
        self._draw_tool_row(tools_col, "ww.planet_shadow_catcher", "Planet Shadow Catcher", 'MATPLANE',
                            "Planet" in bpy.data.materials)

    # Checks if the active object is a shader helper (light direction, head origin, etc.)
    def _is_helper_object(self, active_obj):
        if not active_obj:
            return False
        helper_prefixes = [
            "Light Direction",
            "Head Origin",
            "Head Forward",
            "Head Right",
            "Head Controller",
            "Main Light"]
        if active_obj.type in {'EMPTY', 'LIGHT'}:
            return any(active_obj.name.startswith(prefix) for prefix in helper_prefixes[:4])
        if active_obj.type == 'MESH':
            return any(active_obj.name.startswith(prefix) for prefix in helper_prefixes[4:])
        return False

    # Draws a single tool button row with enabled state
    def _draw_tool_row(self, col, operator_id, text, icon, enabled):
        row = col.row(align=True)
        row.enabled = enabled
        row.operator(operator_id, text=text, icon=icon)

    # ========== VISUAL EFFECTS ==========

    # Draws the visual effects section with outline, eye, and tacet mark toggles
    def _draw_visual_effects(self, layout, ww_props, active_obj, is_mesh, has_ww_mats):
        main_col = layout.column(align=True)
        vfx_section = main_col.box()
        header_row = vfx_section.row(align=True)
        header_row.prop(ww_props, "show_vfx", text="",
                        icon='TRIA_DOWN' if ww_props.show_vfx else 'TRIA_RIGHT', emboss=False)
        header_row.label(text="Visual Effects", icon='SHADERFX')

        if not ww_props.show_vfx:
            return

        vfx_col = vfx_section.column(align=True)
        vfx_col.scale_y = 1.0

        self._draw_outline_toggle(vfx_col)
        self._draw_eye_toggle(vfx_col, active_obj)
        self._draw_tacet_mark(vfx_col, ww_props, active_obj, is_mesh)

    # Draws the outline visibility toggle button with current state
    def _draw_outline_toggle(self, vfx_col):
        outline_state = UICache.get('outlines_state', EffectManager.get_outlines_state)
        has_outline_mods = UICache.get('has_outline_mods', EffectManager.has_any_outline_mod)

        outline_row = vfx_col.row(align=True)
        outline_row.enabled = has_outline_mods
        outline_text = f"Outlines [{'On' if outline_state else 'Off'}]"
        outline_icon = 'CUBE' if outline_state else 'MOD_WIREFRAME'
        outline_row.operator("ww.toggle_outlines", text=outline_text, icon=outline_icon)

    # Draws the two-colored eyes toggle button with current state
    def _draw_eye_toggle(self, vfx_col, active_obj):
        eye_row = vfx_col.row(align=True)
        has_eye_material = False
        if active_obj and active_obj.type == 'MESH':
            has_eye_material = any(
                slot.material and "Eye" in slot.material.name
                for slot in active_obj.material_slots if slot.material
            )
        eye_row.enabled = has_eye_material

        eye_state = False
        if eye_row.enabled:
            eye_state = EffectManager.get_two_colored_eyes_state(active_obj)

        eye_text = f"Two-colored Eyes [{'Yes' if eye_state else 'No'}]"
        eye_icon = 'HIDE_OFF' if eye_state else 'HIDE_ON'
        eye_row.operator("ww.toggle_two_colored_eyes", text=eye_text, icon=eye_icon)

    # Draws the Tacet Mark animation toggle and driver expression input
    def _draw_tacet_mark(self, vfx_col, ww_props, active_obj, is_mesh):
        tacet_col = vfx_col.column(align=True)
        has_tacet = False
        if is_mesh:
            has_tacet = UICache.get(
                'has_tacet_mark',
                lambda: EffectManager.has_tacet_mark(active_obj),
                active_obj
            )
        tacet_col.enabled = has_tacet

        tacet_state = False
        if tacet_col.enabled:
            tacet_state = UICache.get(
                'tacet_animation_state',
                lambda: EffectManager.get_tacet_animation_state(active_obj),
                active_obj
            )

        tacet_row = tacet_col.row(align=True)
        tacet_text = f"Animate Tacet Mark [{'On' if tacet_state else 'Off'}]"
        tacet_icon = 'PAUSE' if tacet_state else 'PLAY'
        tacet_row.operator("ww.animate_tacet_mark", text=tacet_text, icon=tacet_icon)

        formula_row = tacet_col.row(align=True)
        formula_row.prop(ww_props, "tacet_mark_driver_expression", text="", icon='SCRIPT')

    # ========== SMART CAMERA ==========

    # Draws the smart camera section with portrait mode preset buttons
    def _draw_smart_camera(self, layout, ww_props, context):
        main_col = layout.column(align=True)
        camera_section = main_col.box()
        header_row = camera_section.row(align=True)
        header_row.prop(ww_props, "show_smart_camera", text="",
                        icon='TRIA_DOWN' if ww_props.show_smart_camera else 'TRIA_RIGHT', emboss=False)
        header_row.label(text="Smart Camera System", icon='CAMERA_DATA')

        if not ww_props.show_smart_camera:
            return

        camera_col = camera_section.column(align=True)
        current_mode = context.scene.ww_properties.smart_camera_mode
        mode_grid = camera_col.grid_flow(columns=5, align=True)
        mode_grid.scale_y = 1.0

        for mode in ['M', 'MS', 'S', 'XL', 'XXL']:
            op = mode_grid.operator("ww.set_smart_camera", text=mode, depress=(mode == current_mode))
            op.mode = mode

    # ========== AMD FIX ==========

    # Draws the AMD material fix section with Linear and Cubic interpolation buttons
    def _draw_amd_fix(self, layout, ww_props):
        main_col = layout.column(align=True)
        amd_section = main_col.box()
        amd_header = amd_section.row(align=True)
        amd_header.prop(ww_props, "show_amd_fix", text="",
                        icon='TRIA_DOWN' if ww_props.show_amd_fix else 'TRIA_RIGHT', emboss=False)
        amd_header.label(text="AMD Material Fix", icon='MEMORY')

        if not ww_props.show_amd_fix:
            return

        amd_row = amd_section.row(align=True)
        op_linear = amd_row.operator("ww.amd_material_fix", text="Linear")
        op_linear.mode = 'Linear'
        op_cubic = amd_row.operator("ww.amd_material_fix", text="Cubic")
        op_cubic.mode = 'Cubic'

    # ========== FOOTER ==========

    # Draws the addon footer with credits
    def _draw_footer(self, layout):
        layout.separator(factor=0.8)
        footer_section = layout.box()
        footer_section.use_property_split = False
        footer_section.scale_y = 0.8
        footer_row = footer_section.row(align=True)
        footer_row.alignment = 'CENTER'
        footer_row.label(text="🌟 Powered by Akatsuki")
