import os
import re


import bpy


# ========== TEXTURE PROCESSOR ==========

# Handles texture loading, mapping, and pipeline management
class TextureProcessor:

    # ========== CONSTANTS ==========

    CONFIGS_WW = {
        'Skin': {'color_space': 'Non-Color', 'alpha': 'CHANNEL_PACKED'},
        'D': {'color_space': 'sRGB', 'alpha': 'CHANNEL_PACKED'},
        'FTM': {'color_space': 'Non-Color', 'alpha': 'CHANNEL_PACKED'},
        'HM': {'color_space': 'Non-Color', 'alpha': 'CHANNEL_PACKED'},
        'HN': {'color_space': 'Non-Color', 'alpha': 'CHANNEL_PACKED'},
        'N': {'color_space': 'Non-Color', 'alpha': 'CHANNEL_PACKED'},
        'ID': {'color_space': 'Non-Color', 'alpha': 'CHANNEL_PACKED'},
        'RGID': {'color_space': 'Non-Color', 'alpha': 'CHANNEL_PACKED'},
        'HET': {'color_space': 'Non-Color', 'alpha': 'CHANNEL_PACKED'}
    }
    CONFIGS_GW = {
        'Skin': {'color_space': 'sRGB', 'alpha': 'CHANNEL_PACKED'},
        'D': {'color_space': 'sRGB', 'alpha': 'CHANNEL_PACKED'},
        'FTM': {'color_space': 'Non-Color', 'alpha': 'CHANNEL_PACKED'},
        'HM': {'color_space': 'sRGB', 'alpha': 'CHANNEL_PACKED'},
        'HN': {'color_space': 'Non-Color', 'alpha': 'STRAIGHT'},
        'N': {'color_space': 'Non-Color', 'alpha': 'CHANNEL_PACKED'},
        'ID': {'color_space': 'sRGB', 'alpha': 'CHANNEL_PACKED'},
        'RGID': {'color_space': 'Non-Color', 'alpha': 'CHANNEL_PACKED'},
        'HET': {'color_space': 'Non-Color', 'alpha': 'CHANNEL_PACKED'}
    }
    PART_MAP = {
        'Eyes': 'Eye', 'Eye1': 'Eye', 'Eye01': 'Eye', 'Eye2': 'Eye', 'Eye02': 'Eye',
        'Eyes1': 'Eye', 'Eyes01': 'Eye', 'Eyes2': 'Eye', 'Eyes02': 'Eye',
        'Bang': 'Bangs', 'Bangs1': 'Bangs', 'Bangs01': 'Bangs', 'Bangs2': 'Bangs', 'Bangs02': 'Bangs',
        'Bang1': 'Bangs', 'Bang01': 'Bangs', 'Bang2': 'Bangs', 'Bang02': 'Bangs',
        'Hair1': 'Hair', 'Hair01': 'Hair', 'Hair2': 'Hair', 'Hair02': 'Hair',
        'Face1': 'Face', 'Face01': 'Face', 'Face2': 'Face', 'Face02': 'Face',
        'P': 'Up', 'Upper': 'Up', 'Up1': 'Up', 'Up01': 'Up',
        'Up2': 'Up', 'Up_2': 'Up', 'Up02': 'Up', 'Star': 'Up',
        'Down1': 'Down', 'Down01': 'Down', 'Down2': 'Down', 'Down_2': 'Down', 'Down02': 'Down',
        'Skir': 'Skirt', 'Shoes': 'Down',
        'Ahpla': 'Alpha', 'Fx01': 'Fx', 'Hi': 'Eye', 'Shy': 'Face', 'Suit1': 'Suit',
        'Suit01': 'Suit', 'Suit02': 'Suit'
    }
    SUFFIX_MAP = {'D1': 'D', 'D2': 'D', 'D3': 'D', 'DAL': 'D', '32': 'D'}

    # ========== SHADER DETECTION ==========

    # Detects shader type from mesh materials (returns 'ww' or 'gw')
    @staticmethod
    def detect_shader_type(mesh: bpy.types.Object) -> str:
        from ..material.material_manager import MaterialManager
        return MaterialManager.detect_shader_type_by_helpers(mesh)

    # ========== TEXTURE EXTRACTION ==========

    # Extracts material part identifier from texture filename
    @staticmethod
    def extract_part(name: str) -> str | None:
        for pattern in [r'(\w+)_(?:[A-Z]+\d*|\d+)\.(?:png|jpg|jpeg|tga|tiff)$',
                        r'(\w+[A-Za-z]+\d*)(?:_[A-Z]+\d*)?\.(?:png|jpg|jpeg|tga|tiff)$']:
            match = re.search(pattern, name, re.I)
            if match:
                part_match = re.search(r'([A-Z][a-z]*\d*)$', match.group(1))
                if part_match:
                    return part_match.group(1)
        return None

    # Extracts texture type suffix from filename (D, N, HM, Skin, etc)
    @staticmethod
    def extract_suffix(name: str) -> str | None:
        if '_Skin.' in name:
            return 'Skin'
        match = re.search(
            r'_([A-Z]+\d*|\d+)\.(?:png|jpg|jpeg|tga|tiff)$', name, re.I)
        return match.group(1).upper() if match else None

    # ========== TEXTURE LOADING ==========

    # Loads a texture from file path with proper color space settings
    @staticmethod
    def load_texture(path: str, shader_type: str = 'ww') -> bpy.types.Image | None:
        name = os.path.basename(path)
        img = bpy.data.images.get(name)

        if not img:
            try:
                img = bpy.data.images.load(path)
            except RuntimeError:
                return None
        else:
            if img.filepath != path:
                img.filepath = path
                try:
                    img.reload()
                except RuntimeError:
                    pass

        suffix = TextureProcessor.extract_suffix(name)
        norm_suffix = TextureProcessor.SUFFIX_MAP.get(suffix, suffix)
        configs = TextureProcessor.CONFIGS_GW if shader_type == 'gw' else TextureProcessor.CONFIGS_WW
        if norm_suffix in configs:
            config = configs[norm_suffix]
            img.colorspace_settings.name = config['color_space']
            img.alpha_mode = config['alpha']

        try:
            img.pack()
        except RuntimeError:
            pass

        img.use_fake_user = True
        return img

    # ========== NODE ASSIGNMENT ==========

    # Assigns textures to Image Texture nodes (shared for both Wuthering Waves and Gathering Wives)
    @staticmethod
    def _assign_textures_to_nodes(slot, target_map, loaded_imgs):
        has_id = 'ID' in target_map
        has_rgid = 'RGID' in target_map
        use_rgid_replacement = not has_id and has_rgid

        for node in slot.material.node_tree.nodes:
            if node.type == 'TEX_IMAGE':
                suffix = node.name
                if suffix == 'HN':
                    if 'HN' in target_map:
                        tex_name = os.path.basename(target_map['HN'])
                        if tex_name in loaded_imgs:
                            node.image = loaded_imgs[tex_name]
                            continue
                    elif 'N' in target_map:
                        tex_name = os.path.basename(target_map['N'])
                        if tex_name in loaded_imgs:
                            node.image = loaded_imgs[tex_name]
                            continue
                if suffix == 'ID' and use_rgid_replacement:
                    tex_name = os.path.basename(target_map['RGID'])
                    if tex_name in loaded_imgs:
                        node.image = loaded_imgs[tex_name]
                elif suffix in target_map:
                    tex_name = os.path.basename(target_map[suffix])
                    if tex_name in loaded_imgs:
                        node.image = loaded_imgs[tex_name]

        return use_rgid_replacement

    # ========== INPUT SETTINGS ==========

    # Applies material input settings for Wuthering Waves shader
    @staticmethod
    def _apply_ww_input_settings(slot, target_map, norm_part, use_rgid_replacement):
        has_ftm = 'FTM' in target_map
        has_rgid = 'RGID' in target_map

        for node in slot.material.node_tree.nodes:
            if node.type == 'GROUP' and node.node_tree:
                group_name = node.node_tree.name
                if "Wuthering Waves [Body]" in group_name:
                    if "Enable New Shader" in node.inputs:
                        node.inputs["Enable New Shader"].default_value = has_ftm
                    if has_rgid and norm_part in ('Up', 'Down') and "Skin Mask (RGID)" in node.inputs:
                        node.inputs["Skin Mask (RGID)"].default_value = True
                if "Wuthering Waves [Hair]" in group_name and norm_part in ('Bangs', 'Hair'):
                    if "Enable New Shader" in node.inputs:
                        node.inputs["Enable New Shader"].default_value = has_ftm

    # Reserved for Gathering Wives-specific shader input overrides (currently handled by shader defaults)
    @staticmethod
    def _apply_gw_input_settings(slot, target_map, norm_part, use_rgid_replacement):
        pass

    # ========== SEETHROUGH TEXTURES ==========

    # Assigns textures to Seethrough material slots for face/eye rendering
    @staticmethod
    def _map_textures_to_seethrough(mesh, files, shader_type):
        from ..material.material_manager import MaterialManager
        prefix = MaterialManager.PREFIXES.get(shader_type, MaterialManager.PREFIXES['gw'])
        loaded_imgs = {}
        skin_texture = None

        for path in files:
            name = os.path.basename(path)
            suffix = TextureProcessor.extract_suffix(name)
            if suffix == 'Skin':
                skin_texture = path
            img = TextureProcessor.load_texture(path, shader_type)
            if img:
                loaded_imgs[os.path.basename(path)] = img

        images_to_remove = set()
        for slot in mesh.material_slots:
            if not slot.material or not slot.material.node_tree:
                continue
            if not slot.material.name.startswith(prefix):
                continue
            if "Seethrough" not in slot.material.name:
                continue

            for node in slot.material.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    images_to_remove.add(node.image)
                    node.image = None

        for img in images_to_remove:
            img.use_fake_user = False
            if img.users == 0:
                bpy.data.images.remove(img)

        for slot in mesh.material_slots:
            if not slot.material or not slot.material.node_tree:
                continue
            if not slot.material.name.startswith(prefix):
                continue
            if "Seethrough" not in slot.material.name:
                continue

            for node in slot.material.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    suffix = node.name
                    if suffix == 'Ramp' and skin_texture:
                        tex_name = os.path.basename(skin_texture)
                        if tex_name in loaded_imgs:
                            node.image = loaded_imgs[tex_name]
                            node.interpolation = 'Closest'
                            node.extension = 'EXTEND'

            mat_name = slot.material.name
            part = None
            if "Face" in mat_name:
                part = "Face"
            elif "Eye" in mat_name:
                part = "Eye"

            if not part:
                continue

            target_map = {}
            for tex_name in loaded_imgs:
                extracted_part = TextureProcessor.extract_part(tex_name)
                if extracted_part:
                    norm_part = TextureProcessor.PART_MAP.get(
                        extracted_part, extracted_part)
                    if norm_part == part:
                        suffix = TextureProcessor.extract_suffix(tex_name)
                        if suffix:
                            target_map[suffix] = tex_name

            if target_map:
                TextureProcessor._assign_textures_to_nodes(
                    slot, target_map, loaded_imgs)

    # ========== TEXTURE PRIORITY ==========

    # Computes sort key for texture priority (base > numbered > qualified variants)
    @staticmethod
    def _texture_priority_key(filepath: str) -> tuple:
        name = os.path.basename(filepath)
        suffix = TextureProcessor.extract_suffix(name)

        if suffix and suffix != 'Skin':
            base = name.rsplit('_', 1)[0]
        else:
            base = os.path.splitext(name)[0]

        if suffix:
            name_without_suffix = name.rsplit('_', 1)[0] + name[name.rfind('.'):]
            part = TextureProcessor.extract_part(name_without_suffix)
        else:
            part = TextureProcessor.extract_part(name)

        has_trailing_number = bool(part and re.search(r'\d+$', part))

        if has_trailing_number:
            num = int(re.search(r'(\d+)$', part).group(1))
            return (1, -num, -len(base))
        elif part and base.endswith(part):
            return (2, 0, 0)
        else:
            return (0, 0, base)

    # ========== TEXTURE MAPPING ==========

    # Maps texture files to their corresponding material slots based on part names
    @staticmethod
    def map_textures(files: list[str], mesh: bpy.types.Object) -> None:
        files.sort(key=TextureProcessor._texture_priority_key)
        shader_type = TextureProcessor.detect_shader_type(mesh)
        from ..material.material_manager import MaterialManager
        prefix = MaterialManager.PREFIXES.get(shader_type, MaterialManager.PREFIXES['ww'])

        cached_textures = set()
        if "ww_imported_textures" in mesh:
            cached_textures = set(mesh["ww_imported_textures"].split("|"))

        new_texture_names = set()
        for path in files:
            new_texture_names.add(os.path.basename(path))

        for tex_name in cached_textures:
            if tex_name and tex_name not in new_texture_names:
                img = bpy.data.images.get(tex_name)
                if img:
                    img.use_fake_user = False
                    if img.users == 0:
                        bpy.data.images.remove(img)

        images_to_remove = set()
        for slot in mesh.material_slots:
            if slot.material and slot.material.node_tree and slot.material.name.startswith(prefix):
                for node in slot.material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image:
                        images_to_remove.add(node.image)
                        node.image = None

        for img in images_to_remove:
            img.use_fake_user = False
            if img.users == 0:
                bpy.data.images.remove(img)

        for path in files:
            TextureProcessor.load_texture(path, shader_type)

        texture_map: dict[str, dict[str, str]] = {}
        skin_texture = None

        for path in files:
            name = os.path.basename(path)
            suffix = TextureProcessor.extract_suffix(name)
            if suffix == 'Skin':
                skin_texture = path
                continue
            if 'Switch_' in name or 'Switch02_' in name or 'Switch03_' in name or 'Damage_' in name:
                continue
            if suffix:
                name_without_suffix = name.rsplit(
                    '_', 1)[0] + name[name.rfind('.'):]
                part = TextureProcessor.extract_part(name_without_suffix)
            else:
                part = TextureProcessor.extract_part(name)
            if part and suffix:
                norm_part = TextureProcessor.PART_MAP.get(part, part)
                norm_suffix = TextureProcessor.SUFFIX_MAP.get(suffix, suffix)
                if norm_part not in texture_map:
                    texture_map[norm_part] = {}
                texture_map[norm_part][suffix] = path
                texture_map[norm_part][norm_suffix] = path

        loaded_imgs = {img.name: img for img in bpy.data.images}

        for slot in mesh.material_slots:
            if not slot.material or not slot.material.node_tree:
                continue
            if not slot.material.name.startswith(prefix):
                continue

            part = slot.material.name.replace(prefix, "").split()[0]
            norm_part = TextureProcessor.PART_MAP.get(part, part)
            target_map = texture_map.get(norm_part)
            if not target_map and norm_part == 'Fur':
                target_map = texture_map.get('Cloth')

            for node in slot.material.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    suffix = node.name
                    if suffix == 'Ramp' and skin_texture:
                        tex_name = os.path.basename(skin_texture)
                        if tex_name in loaded_imgs:
                            node.image = loaded_imgs[tex_name]
                            if shader_type == 'gw':
                                node.interpolation = 'Closest'
                                node.extension = 'EXTEND'
                            continue

            if target_map:
                use_rgid = TextureProcessor._assign_textures_to_nodes(
                    slot, target_map, loaded_imgs)
                if shader_type == 'ww':
                    TextureProcessor._apply_ww_input_settings(
                        slot, target_map, norm_part, use_rgid)
                else:
                    TextureProcessor._apply_gw_input_settings(
                        slot, target_map, norm_part, use_rgid)

        mesh["ww_imported_textures"] = "|".join(new_texture_names)
        mesh["ww_texture_form_index"] = 0

        TextureProcessor._map_textures_to_seethrough(
            mesh, files, shader_type)

    # ========== TEXTURE FORM ==========

    # Returns groups of textures that compete for the same material slot (>1 version)
    @staticmethod
    def get_texture_form_variants(mesh: bpy.types.Object) -> dict[tuple[str, str], list[str]]:
        if "ww_imported_textures" not in mesh:
            return {}

        texture_names = [n for n in mesh["ww_imported_textures"].split("|") if n]
        groups: dict[tuple[str, str], list[str]] = {}

        for tex_name in texture_names:
            if 'Switch_' in tex_name or 'Switch02_' in tex_name or 'Switch03_' in tex_name or 'Damage_' in tex_name:
                continue
            suffix = TextureProcessor.extract_suffix(tex_name)
            if not suffix or suffix == 'Skin':
                continue

            name_without_suffix = tex_name.rsplit('_', 1)[0] + tex_name[tex_name.rfind('.'):]
            part = TextureProcessor.extract_part(name_without_suffix)
            if not part:
                continue

            norm_part = TextureProcessor.PART_MAP.get(part, part)
            norm_suffix = TextureProcessor.SUFFIX_MAP.get(suffix, suffix)
            key = (norm_part, norm_suffix)
            if key not in groups:
                groups[key] = []
            groups[key].append(tex_name)

        result = {}
        for key, names in groups.items():
            if len(names) > 1:
                names.sort(key=TextureProcessor._texture_priority_key)
                names.reverse()
                result[key] = names
        return result

    # Returns current form display info (1-based index, total count)
    @staticmethod
    def get_current_form_info(mesh: bpy.types.Object) -> tuple[int, int]:
        variants = TextureProcessor.get_texture_form_variants(mesh)
        if not variants:
            return 0, 0
        max_variants = max(len(v) for v in variants.values())
        current_index = mesh.get("ww_texture_form_index", 0)
        return (current_index % max_variants) + 1, max_variants

    # Cycles to the next texture form variant for all multi-version texture groups
    @staticmethod
    def apply_texture_form_change(mesh: bpy.types.Object) -> tuple[int, int]:
        variants = TextureProcessor.get_texture_form_variants(mesh)
        if not variants:
            return 0, 0

        max_variants = max(len(v) for v in variants.values())
        current_index = mesh.get("ww_texture_form_index", 0)
        new_index = (current_index + 1) % max_variants
        mesh["ww_texture_form_index"] = new_index

        shader_type = TextureProcessor.detect_shader_type(mesh)
        from ..material.material_manager import MaterialManager
        prefix = MaterialManager.PREFIXES.get(shader_type, MaterialManager.PREFIXES['ww'])

        form_map: dict[str, dict[str, str]] = {}
        for (norm_part, norm_suffix), names in variants.items():
            idx = new_index % len(names)
            tex_name = names[idx]
            if norm_part not in form_map:
                form_map[norm_part] = {}
            form_map[norm_part][norm_suffix] = tex_name

        loaded_imgs = {img.name: img for img in bpy.data.images}

        for slot in mesh.material_slots:
            if not slot.material or not slot.material.node_tree:
                continue
            if not slot.material.name.startswith(prefix):
                continue
            if "Seethrough" in slot.material.name:
                continue

            part = slot.material.name.replace(prefix, "").split()[0]
            norm_part = TextureProcessor.PART_MAP.get(part, part)

            if norm_part not in form_map:
                continue

            target_suffixes = form_map[norm_part]

            for node in slot.material.node_tree.nodes:
                if node.type != 'TEX_IMAGE':
                    continue
                node_suffix = node.name
                if node_suffix == 'Ramp':
                    continue

                norm_node_suffix = TextureProcessor.SUFFIX_MAP.get(node_suffix, node_suffix)

                if norm_node_suffix in target_suffixes:
                    tex_name = target_suffixes[norm_node_suffix]
                    if tex_name in loaded_imgs:
                        node.image = loaded_imgs[tex_name]
                elif node_suffix == 'HN' and 'N' in target_suffixes:
                    tex_name = target_suffixes['N']
                    if tex_name in loaded_imgs:
                        node.image = loaded_imgs[tex_name]

        return new_index + 1, max_variants

    # ========== TEXTURE VARIANTS ==========

    # Returns available texture variants for a mesh (Normal, Injured, Wet)
    @staticmethod
    def get_texture_variants(mesh: bpy.types.Object) -> dict[str, list[bpy.types.Image]]:
        variants: dict[str, list[bpy.types.Image]] = {
            'normal': [], 'injured': [], 'wet': []}
        d_regex = re.compile(
            r'_(?:D|D\d+)\.(?:png|jpg|jpeg|tga|tiff)$', re.IGNORECASE)

        for img in bpy.data.images:
            if img.name.endswith(('.png', '.jpg', '.jpeg', '.tga', '.tiff')):
                if d_regex.search(img.name):
                    if 'Switch02_' in img.name or 'Switch03_' in img.name:
                        variants['wet'].append(img)
                    elif 'Switch_' in img.name or 'Damage_' in img.name:
                        variants['injured'].append(img)
                    else:
                        variants['normal'].append(img)
        return variants

    # ========== AVAILABILITY CHECK ==========

    # Checks which texture types are available for the model
    @staticmethod
    def check_texture_availability(mesh: bpy.types.Object) -> dict[str, bool]:
        availability: dict[str, bool] = {
            'normal': False, 'injured': False, 'wet': False}
        mesh_base_textures = set()

        if mesh.material_slots:
            for slot in mesh.material_slots:
                if slot.material and slot.material.node_tree:
                    for node in slot.material.node_tree.nodes:
                        if node.type == 'TEX_IMAGE' and node.name == 'D' and node.image:
                            clean_name = node.image.name
                            if 'Damage_D' in clean_name:
                                standardized_name = clean_name.replace(
                                    'Damage_D', '_D')
                            else:
                                standardized_name = re.sub(
                                    r'Switch0?2_D|Switch0?3_D|Switch_D', 'D', clean_name)
                                standardized_name = re.sub(
                                    r'_D\d+\.', '_D.', standardized_name)
                            mesh_base_textures.add(standardized_name)

        if not mesh_base_textures:
            return availability

        availability['normal'] = True

        for img in bpy.data.images:
            img_name = img.name
            if 'Switch_D' in img_name:
                base_name = img_name.replace('Switch_D', 'D')
                if base_name in mesh_base_textures:
                    availability['injured'] = True
            elif 'Damage_D' in img_name:
                base_name = img_name.replace('Damage_D', '_D')
                if base_name in mesh_base_textures:
                    availability['injured'] = True
            elif 'Switch02_D' in img_name:
                base_name = img_name.replace('Switch02_D', 'D')
                if base_name in mesh_base_textures:
                    availability['wet'] = True
            elif 'Switch03_D' in img_name:
                base_name = img_name.replace('Switch03_D', 'D')
                if base_name in mesh_base_textures:
                    availability['wet'] = True
            if availability['injured'] and availability['wet']:
                break

        return availability

    # ========== PIPELINE APPLICATION ==========

    # Applies a specific texture pipeline state to the model
    @staticmethod
    def apply_texture_pipeline(mesh: bpy.types.Object, pipeline_type: str) -> None:
        current_state = TextureProcessor.get_current_pipeline_state(mesh)
        variants = TextureProcessor.get_texture_variants(mesh)
        has_wet_03 = any('Switch03_D' in img.name for img in variants['wet'])

        for slot in mesh.material_slots:
            if not slot.material or not slot.material.node_tree:
                continue
            for node in slot.material.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.name == 'D' and node.image:
                    current_name = node.image.name
                    name_without_ext = re.sub(
                        r'\.(?:png|jpg|jpeg|tga|tiff)$', '', current_name, flags=re.IGNORECASE)
                    base_name = re.sub(
                        r'_(?:D\d*|Switch_D|Switch0[23]_D|Damage_D)$', '', name_without_ext)
                    base_pattern = re.escape(base_name)
                    target_texture = None

                    if pipeline_type == 'normal':
                        for img in variants['normal']:
                            if re.search(rf"{base_pattern}_(?:D|D\d+)\.", img.name):
                                target_texture = img
                                break
                    elif pipeline_type == 'injured':
                        for img in variants['injured']:
                            if re.search(f"{base_pattern}_Switch_D\\.", img.name):
                                target_texture = img
                                break
                        if not target_texture:
                            for img in variants['injured']:
                                if re.search(f"{base_pattern}_Damage_D\\.", img.name):
                                    target_texture = img
                                    break
                        if not target_texture:
                            for img in variants['normal']:
                                if re.search(rf"{base_pattern}_(?:D|D\d+)\.", img.name):
                                    target_texture = img
                                    break
                    elif pipeline_type == 'wet':
                        target_suffix_regex = r'_Switch02_D\.'
                        if current_state == 'wet_02' and has_wet_03:
                            target_suffix_regex = r'_Switch03_D\.'
                        for img in variants['wet']:
                            if re.search(f"{base_pattern}{target_suffix_regex}", img.name):
                                target_texture = img
                                break
                        if not target_texture:
                            for img in variants['wet']:
                                if re.search(f"{base_pattern}_Switch02_D\\.", img.name):
                                    target_texture = img
                                    break
                        if not target_texture:
                            for img in variants['normal']:
                                if re.search(rf"{base_pattern}_(?:D|D\d+)\.", img.name):
                                    target_texture = img
                                    break

                    if target_texture and target_texture != node.image:
                        node.image = target_texture

    # ========== PIPELINE STATE ==========

    # Returns the current active texture pipeline state
    @staticmethod
    def get_current_pipeline_state(mesh: bpy.types.Object) -> str | None:
        has_any_texture = False
        for slot in mesh.material_slots:
            if not slot.material or not slot.material.node_tree:
                continue
            for node in slot.material.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.name == 'D' and node.image:
                    has_any_texture = True
                    img_name = node.image.name
                    if 'Switch03_D' in img_name:
                        return 'wet_03'
                    elif 'Switch02_D' in img_name:
                        return 'wet_02'
                    elif 'Switch_D' in img_name or 'Damage_D' in img_name:
                        return 'injured'
        if not has_any_texture:
            return None
        return 'normal'
