import bmesh
import bpy

from ..core.object_manager import ObjectManager
from ..core.utils import Utils
from ..material.material_manager import MaterialManager


# ========== SEETHROUGH MANAGER ==========

# Handles creation of seethrough geometry for face/eye rendering (both WW and GW shaders)
class SeeThroughManager:

    # ========== SHADER CONFIG ==========

    SEETHROUGH_OUTPUT = "Seethrough"
    SHADER_GROUP_PATTERNS = {
        'ww': "Wuthering Waves [{}]",
        'gw': "Gathering Wives [{}]",
    }

    # ========== CREATION ==========

    # Creates face/eye seethrough geometry and joins it back to the mesh
    @staticmethod
    def create_seethrough_mesh(mesh: bpy.types.Object, mesh_name: str, shader_type: str = 'gw') -> None:
        face_eye_slots = []
        for i, slot in enumerate(mesh.material_slots):
            if not slot.material:
                continue
            mat_name = slot.material.name
            if "Face" in mat_name or "Eye" in mat_name:
                face_eye_slots.append(i)

        if not face_eye_slots:
            return

        Utils.ensure_object_mode()
        bpy.ops.object.select_all(action='DESELECT')
        mesh.select_set(True)
        bpy.context.view_layer.objects.active = mesh

        bpy.ops.object.duplicate(linked=False)
        seethrough_mesh = bpy.context.active_object

        cleaned_name = ObjectManager._clean_mesh_name(mesh_name)
        seethrough_mesh.name = f"{cleaned_name} Seethrough"

        mods_to_remove = [mod for mod in seethrough_mesh.modifiers if "Outlines" in mod.name]
        for mod in mods_to_remove:
            seethrough_mesh.modifiers.remove(mod)

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')

        bm = bmesh.from_edit_mesh(seethrough_mesh.data)

        faces_to_keep = set()
        for face in bm.faces:
            if face.material_index in face_eye_slots:
                faces_to_keep.add(face)

        faces_to_delete = [f for f in bm.faces if f not in faces_to_keep]
        bmesh.ops.delete(bm, geom=faces_to_delete, context='FACES')

        bmesh.update_edit_mesh(seethrough_mesh.data)
        bpy.ops.object.mode_set(mode='OBJECT')

        slots_to_remove = []
        for i, _slot in enumerate(seethrough_mesh.material_slots):
            if i not in face_eye_slots:
                slots_to_remove.append(i)

        for i in reversed(slots_to_remove):
            seethrough_mesh.active_material_index = i
            bpy.ops.object.material_slot_remove()

        SeeThroughManager._duplicate_materials(seethrough_mesh, cleaned_name, shader_type)

        bpy.ops.object.select_all(action='DESELECT')
        seethrough_mesh.select_set(True)
        mesh.select_set(True)
        bpy.context.view_layer.objects.active = mesh
        bpy.ops.object.join()

    # ========== MATERIAL DUPLICATION ==========

    # Duplicates and renames materials for seethrough rendering
    @staticmethod
    def _duplicate_materials(seethrough_mesh: bpy.types.Object, cleaned_name: str, shader_type: str = 'gw') -> None:
        prefix = MaterialManager.PREFIXES.get(shader_type, MaterialManager.PREFIXES['gw'])
        created_materials = {}

        for slot in seethrough_mesh.material_slots:
            if not slot.material:
                continue

            orig_mat = slot.material

            part_type = ""
            if "Face" in orig_mat.name:
                part_type = "Face"
            elif "Eye" in orig_mat.name:
                part_type = "Eye"

            if not part_type:
                continue

            if part_type in created_materials:
                slot.material = created_materials[part_type]
            else:
                new_mat = orig_mat.copy()
                new_mat.name = f"{prefix}{cleaned_name} {part_type} Seethrough"
                slot.material = new_mat
                created_materials[part_type] = new_mat

                SeeThroughManager._setup_seethrough_output(new_mat, part_type, shader_type)
                SeeThroughManager._configure_material_settings(new_mat)

    # ========== SHADER OUTPUT ==========

    # Reconnects shader output to Seethrough socket
    @staticmethod
    def _setup_seethrough_output(material: bpy.types.Material, part_type: str, shader_type: str = 'gw') -> None:
        if not material.node_tree:
            return

        group_pattern = SeeThroughManager.SHADER_GROUP_PATTERNS.get(
            shader_type, SeeThroughManager.SHADER_GROUP_PATTERNS['gw'])
        output_name = SeeThroughManager.SEETHROUGH_OUTPUT

        node_tree = material.node_tree
        output_node = None
        shader_group = None

        for node in node_tree.nodes:
            if node.type == 'OUTPUT_MATERIAL':
                output_node = node
            elif node.type == 'GROUP' and node.node_tree:
                if group_pattern.format(part_type) in node.node_tree.name:
                    shader_group = node

        if not output_node or not shader_group:
            return

        if output_name not in shader_group.outputs:
            return

        for link in list(node_tree.links):
            if link.to_node == output_node and link.to_socket.name == "Surface":
                node_tree.links.remove(link)

        node_tree.links.new(
            shader_group.outputs[output_name],
            output_node.inputs["Surface"]
        )

    # Configures seethrough material settings (Alpha Hashed, No Shadow, Raytrace Refraction)
    @staticmethod
    def _configure_material_settings(material: bpy.types.Material) -> None:
        material.use_backface_culling = True
        material.blend_method = 'HASHED'
        material.shadow_method = 'NONE'
        material.use_screen_refraction = True
        material.show_transparent_back = False
        material.use_sss_translucency = False
        material.alpha_threshold = 0.5
        material.refraction_depth = 0.0
        material.pass_index = 0
