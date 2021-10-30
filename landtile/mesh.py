# mesh utilities
import os
import json
import numpy as np
from stl import mesh

def build_mesh(vertices, faces):
    vs = np.array(vertices)
    fs = np.array(faces)
    hedron = mesh.Mesh(np.zeros(len(faces), dtype=mesh.Mesh.dtype))
    for i, f in enumerate(fs):
        for j in range(3):
            hedron.vectors[i][j] = vs[f[j],:]
    return hedron

def merge_meshes(meshes):
    return mesh.Mesh(np.concatenate([m.data.copy() for m in meshes]))

def write_obj(meshes, materials, path):
    base = os.path.splitext(os.path.basename(path))[0]
    with open(path, 'w') as fd:
        print = lambda s: fd.write(s + '\n')
        print('# take9 handwrite obj file:')
        print('mtllib common.mtl')
        iv, inv = 1, 1
        for mesh, material in zip(meshes, materials):
            mesh.update_normals()
            print(f'o {base}_{iv}')
            print(f'usemtl {material}')
            for vs in mesh.vectors:
                for x, y, z in vs:
                    print(f'v {x} {z} {-y}')
            for x, y, z in mesh.normals:
                print(f'vn {x} {z} {-y}')
            print('s off')
            for i, vs in enumerate(mesh.vectors):
                j, k = i * 3 + iv, i + inv
                print(f'f {j}//{k} {j+1}//{k} {j+2}//{k}')
            iv += len(mesh.vectors) * 3
            inv += len(mesh.vectors)

def write_batchtable(properties, path):
    batchtable = {}
    batchtable['batchId'] = [i for i, _ in enumerate(properties)]
    for k in properties[0].keys():
        batchtable[k] = [p[k] for p in properties] 
    with open(path, 'wb') as fd:
        fd.write(json.dumps(batchtable, indent=2, ensure_ascii=False).encode('utf-8'))
