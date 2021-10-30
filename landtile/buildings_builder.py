#%%
import collections as co
import numpy as np
from shapely.geometry.polygon import orient
from landtile import earcut
from landtile import building
from landtile import mesh as lmesh


def build_mesh(polygon, alt, height):
    polygon = orient(polygon, 1.0)  # force orient to ccw
    vertices = polygon.exterior.coords[:]
    data = earcut.flatten([vertices])
    faces = earcut.earcut(data['vertices'], data['holes'], data['dimensions'])
    faces = np.array(faces).reshape((-1, 3))
    
    base, top = alt, alt + height
    v3s = [(v[0], v[1], base) for v in vertices] + \
        [(v[0], v[1], top) for v in vertices]
    floor_faces = [f[::-1] for f in faces]
    cvs = len(vertices)
    ceil_faces = [[f + cvs for f in face] for face in faces]
    facets = []
    for i in range(cvs):
        j = (i + 1) % cvs
        nf = [i, j, j + cvs, i + cvs, i]
        facets.append(nf[:3])
        facets.append(nf[2:])
    whole_faces = floor_faces + ceil_faces + facets
    return lmesh.build_mesh(v3s, whole_faces)

# --

def build(dem, df):
    meshes, materials, properties = [], [], []
    for key, row in df.iterrows():
        alt = building.get_alt(row.geometry, row.floor, dem)
        height = row.floor * 4 if row.height == 0 else row.height
        if row['type'] in ['普通無壁舎', '堅ろう無壁舎']:
            mesh = build_mesh(row.geometry, alt + height - 4, 1)
        else:
            mesh = build_mesh(row.geometry, alt, height)
        meshes.append(mesh)
        materials.append(building.get_material(row['type']))
        properties.append({'rID': row.rID, 'type': row['type']})

    # fold meshes by material
    meshes_by = co.defaultdict(lambda: [])
    for mesh, mat, prop in zip(meshes, materials, properties):
        meshes_by[mat].append(mesh)
    fold_meshes = [lmesh.merge_meshes(meshes) for meshes in meshes_by.values()]
    fold_materials = list(meshes_by.keys())
    fold_properties = [{'rID': mat, 'type': mat} for mat, _ in meshes_by.items()]

    return fold_meshes, fold_materials, fold_properties


#%%
from landtile import buildings_extender as be
from landtile import dem_digger as dd

if __name__ == '__main__':
    GPKG = 'enoshima_shape.gpkg'
    DEM = 'enoshima_dem.vrt'
    Z, X, Y = 15, 29079, 12944
    df = be.extend(GPKG, Z, X, Y)
    dem = dd.undig(DEM, Z, X, Y)  # 整地しない場合
    meshes, materials, properties = build(dem, df)
    lmesh.write_obj(meshes, materials, f'{Z}_{X}_{Y}_bldgs.obj')
    lmesh.write_batchtable(properties, f'{Z}_{X}_{Y}_bldgs.json')
