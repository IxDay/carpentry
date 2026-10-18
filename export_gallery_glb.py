#!/usr/bin/env python3
"""Export the gallery joints (search_results/) to animated .glb files.

Usage: uv run export_gallery_glb.py [output_dir]   (default: gallery_glb/)

Each file holds one node per timber. The "assemble" animation slides the
timbers together along the sliding axis and apart again, like the
"Open/close joint" button in the app. Units are metres.
"""
import os
import sys

sys.dont_write_bytecode = True  # upstream tracks setup/__pycache__ in git
ROOT = os.path.dirname(os.path.abspath(__file__))
SETUP = os.path.join(ROOT, "setup")
sys.path.insert(0, SETUP)
os.chdir(SETUP)  # the app loads textures by relative path

import numpy as np
import pygltflib as gl

# Build geometry without an OpenGL context: skip the GPU buffer uploads.
import Buffer
Buffer.Buffer.__init__ = lambda self, parent: setattr(self, "parent", parent)
Buffer.Buffer.buffer_vertices = lambda self: None
Buffer.Buffer.buffer_indices = lambda self: None

from Types import Types
from Geometries import Geometries, joint_face_indices, joint_line_indices

# Animation timing, from ViewSettings.set_joint_opening_distance
OPEN_SPEED = 1.2  # open_ratio units per second
HOLD = 0.75       # seconds held open and closed

WOOD = [0.87, 0.72, 0.53, 1.0]
LINE = [0.0, 0.0, 0.0, 1.0]


class _Parent:
    pass


class GlbBuilder:
    def __init__(self):
        self.gltf = gl.GLTF2(scene=0, scenes=[gl.Scene(nodes=[])], asset=gl.Asset(generator="tsugite export_gallery_glb.py"))
        self.blob = bytearray()

    def accessor(self, data, type_, target=None, minmax=False):
        data = np.ascontiguousarray(data)
        component = gl.UNSIGNED_INT if data.dtype == np.uint32 else gl.FLOAT
        while len(self.blob) % 4: self.blob.append(0)
        self.gltf.bufferViews.append(gl.BufferView(buffer=0, byteOffset=len(self.blob), byteLength=data.nbytes, target=target))
        self.blob.extend(data.tobytes())
        acc = gl.Accessor(bufferView=len(self.gltf.bufferViews)-1, componentType=component, count=len(data), type=type_)
        if minmax:
            acc.min = data.min(axis=0).tolist() if data.ndim > 1 else [float(data.min())]
            acc.max = data.max(axis=0).tolist() if data.ndim > 1 else [float(data.max())]
        self.gltf.accessors.append(acc)
        return len(self.gltf.accessors)-1

    def material(self, name, color, texture=None):
        pbr = gl.PbrMetallicRoughness(baseColorFactor=color, metallicFactor=0.0, roughnessFactor=0.9)
        if texture is not None:
            pbr.baseColorFactor = [1.0, 1.0, 1.0, 1.0]
            pbr.baseColorTexture = gl.TextureInfo(index=texture)
        self.gltf.materials.append(gl.Material(name=name, pbrMetallicRoughness=pbr, doubleSided=True))
        return len(self.gltf.materials)-1

    def texture(self, path):
        data = open(path, "rb").read()
        while len(self.blob) % 4: self.blob.append(0)
        self.gltf.bufferViews.append(gl.BufferView(buffer=0, byteOffset=len(self.blob), byteLength=len(data)))
        self.blob.extend(data)
        self.gltf.images.append(gl.Image(bufferView=len(self.gltf.bufferViews)-1, mimeType="image/jpeg"))
        self.gltf.samplers.append(gl.Sampler(magFilter=gl.LINEAR, minFilter=gl.LINEAR_MIPMAP_LINEAR, wrapS=gl.REPEAT, wrapT=gl.REPEAT))
        self.gltf.textures.append(gl.Texture(source=len(self.gltf.images)-1, sampler=len(self.gltf.samplers)-1))
        return len(self.gltf.textures)-1

    def save(self, path):
        self.gltf.buffers = [gl.Buffer(byteLength=len(self.blob))]
        self.gltf.set_binary_blob(bytes(self.blob))
        self.gltf.save_binary(path)


def quads_to_triangles(verts, quad_indices, scale):
    """Unshared vertices per quad, so every face gets its own flat normal."""
    quads = np.asarray(quad_indices, dtype=np.int64).reshape(-1, 4)
    corners = verts[quads]  # (q, 4, 8): position, color, uv
    pos = corners[:, :, 0:3]*scale
    normal = np.cross(pos[:, 1]-pos[:, 0], pos[:, 2]-pos[:, 0])
    length = np.linalg.norm(normal, axis=1, keepdims=True)
    normal = np.where(length > 0, normal/np.maximum(length, 1e-12), [0.0, 0.0, 1.0])
    positions = pos.reshape(-1, 3).astype(np.float32)
    normals = np.repeat(normal, 4, axis=0).astype(np.float32)
    uvs = corners[:, :, 6:8].reshape(-1, 2).astype(np.float32)
    base = (np.arange(len(quads))*4)[:, None]
    tris = (base+np.array([0, 1, 2, 0, 2, 3])).reshape(-1).astype(np.uint32)
    return positions, normals, uvs, tris


def timber_primitives(builder, verts, quad_indices, scale, material, textured=False):
    if len(quad_indices) == 0: return None
    positions, normals, uvs, tris = quads_to_triangles(verts, quad_indices, scale)
    attributes = gl.Attributes(
        POSITION=builder.accessor(positions, gl.VEC3, gl.ARRAY_BUFFER, minmax=True),
        NORMAL=builder.accessor(normals, gl.VEC3, gl.ARRAY_BUFFER))
    if textured: attributes.TEXCOORD_0 = builder.accessor(uvs, gl.VEC2, gl.ARRAY_BUFFER)
    return gl.Primitive(
        attributes=attributes,
        indices=builder.accessor(tris, gl.SCALAR, gl.ELEMENT_ARRAY_BUFFER),
        material=material, mode=gl.TRIANGLES)


def line_primitive(builder, verts, line_indices, scale, material):
    if len(line_indices) == 0: return None
    idx = np.asarray(line_indices, dtype=np.int64)
    used, remap = np.unique(idx, return_inverse=True)
    positions = (verts[used, 0:3]*scale).astype(np.float32)
    return gl.Primitive(
        attributes=gl.Attributes(POSITION=builder.accessor(positions, gl.VEC3, gl.ARRAY_BUFFER, minmax=True)),
        indices=builder.accessor(remap.astype(np.uint32), gl.SCALAR, gl.ELEMENT_ARRAY_BUFFER),
        material=material, mode=gl.LINES)


def export_joint(type, hfs, path):
    mesh = Geometries(type, mainmesh=False, hfs=hfs)
    verts = type.vertices.reshape(-1, type.vertex_no_info)
    scale = type.ratio/1000.0  # app units -> mm -> m

    b = GlbBuilder()
    side_mat = b.material("wood", WOOD)
    end_mat = b.material("end grain", WOOD, texture=b.texture(os.path.join(SETUP, "textures", "end_grain.jpg")))
    line_mat = b.material("outline", LINE)

    # Same opening as Show.draw_geometries: open_ratio up to 1+0.5*(noc-2)
    max_open = 1+0.5*(type.noc-2)
    t_move = max_open/OPEN_SPEED
    times = np.array([0, HOLD, HOLD+t_move, 2*HOLD+t_move, 2*HOLD+2*t_move], dtype=np.float32)
    ratios = [max_open, max_open, 0, 0, max_open]  # starts open, assembles, opens again

    # glTF is Y-up; turn the app's Z axis (the sliding axis) upright
    b.gltf.nodes.append(gl.Node(name="joint", rotation=[-0.7071068, 0.0, 0.0, 0.7071068], children=[]))
    b.gltf.scenes[0].nodes.append(0)

    channels, samplers = [], []
    time_acc = b.accessor(times, gl.SCALAR, minmax=True)
    for n in range(type.noc):
        ax = type.fixed.sides[n][0].ax
        nend, end, _, faces = joint_face_indices(mesh, [], mesh.voxel_matrix, type.fixed.sides[n], n, ax*type.vn)
        _, lines = joint_line_indices(mesh, [], n, ax*type.vn)
        prims = [timber_primitives(b, verts, faces[nend.start_index:nend.start_index+nend.count], scale, side_mat),
                 timber_primitives(b, verts, faces[end.start_index:end.start_index+end.count], scale, end_mat, textured=True),
                 line_primitive(b, verts, lines, scale, line_mat)]
        b.gltf.meshes.append(gl.Mesh(name="timber_"+str(n), primitives=[p for p in prims if p is not None]))
        b.gltf.nodes.append(gl.Node(name="timber_"+str(n), mesh=len(b.gltf.meshes)-1))
        b.gltf.nodes[0].children.append(len(b.gltf.nodes)-1)

        direction = (2*n+1-type.noc)/(type.noc-1)
        if direction == 0: continue
        moves = np.zeros((len(times), 3), dtype=np.float32)
        moves[:, type.sax] = [direction*r*type.component_size*scale for r in ratios]
        b.gltf.nodes[-1].translation = moves[0].tolist()
        samplers.append(gl.AnimationSampler(input=time_acc, output=b.accessor(moves, gl.VEC3), interpolation="LINEAR"))
        channels.append(gl.AnimationChannel(sampler=len(samplers)-1, target=gl.AnimationChannelTarget(node=len(b.gltf.nodes)-1, path="translation")))
    b.gltf.animations.append(gl.Animation(name="assemble", channels=channels, samplers=samplers))
    b.save(path)


def main():
    out_dir = os.path.abspath(os.path.join(ROOT, sys.argv[1] if len(sys.argv) > 1 else "gallery_glb"))
    os.makedirs(out_dir, exist_ok=True)
    type = Types(_Parent(), fs=[[[2, 0]], [[2, 1]]], sax=2, dim=3)
    type.open_gallery()
    total = type.gallery_size()
    if total == 0: sys.exit("ERROR: no gallery data in "+type.gallery_location())
    for i in range(total):
        hfs = np.load(os.path.join(type.gallery_location(), "height_fields_"+str(i)+".npy")).astype(int)
        export_joint(type, hfs, os.path.join(out_dir, "joint_%03d.glb" % i))
    print("Exported %d joints to %s" % (total, out_dir))


if __name__ == "__main__":
    main()
