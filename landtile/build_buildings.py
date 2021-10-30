#%%
import numpy as np
import mapbox_earcut as earcut
import stl
import building
import misc

def build_mesh(polygon, alt, height):
    vertices = polygon.exterior.coords[::-1]
    faces = earcut.triangulate_float32(
        vertices, np.array([len(vertices)])).reshape((-1, 3))
    
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
    return misc.build_mesh(v3s, whole_faces)

def build_meshes(df, dem):
    meshes, materials, properties = [], [], []
    for key, row in df.iterrows():
        alt = building.get_alt(row.geom, row.floor, dem)
        height = row.floor * 4 if row.height == 0 else row.height
        if row['type'] in ['普通無壁舎', '堅ろう無壁舎']:
            mesh = build_mesh(row.geom, alt + height - 4, 1)
        else:
            mesh = build_mesh(row.geom, alt, height)
        meshes.append(mesh)
        materials.append(building.get_material(row['type']))
        properties.append({'rid': row.rid, 'type': row['type']})
    return meshes, materials, properties


#%%
import sys
import collections as co
import geopandas as gpd
from dem import Dem
import misc

if __name__ == '__main__':
    # sys.argv = ['foo', '~dem.tif', '15_29079_12944_bldgs.geojson', '15_29079_12944_bldgs.obj', '15_29079_12944_bldgs.json']
    if len(sys.argv) != 5:
        sys.exit('usage: src_dem bldgs_geojson dst_obj dst_json')

    dem = Dem(sys.argv[1])
    df = gpd.read_file(sys.argv[2])
    df = df.rename(columns={'geometry': 'geom'})  # db readでのcolumn nameに
    meshes, materials, properties = build_meshes(df, dem)
    # misc.write_obj(meshes, materials, sys.argv[3])
    # misc.write_batchtable(properties, sys.argv[4])

    # fold meshes by material
    meshes_dict = co.defaultdict(lambda: [])
    for mesh, mat, prop in zip(meshes, materials, properties):
        meshes_dict[mat].append(mesh)
    merged_meshes = [misc.merge_meshes(meshes)
                     for meshes in meshes_dict.values()]
    merged_materials = list(meshes_dict.keys())
    merged_properties = [{'rid': mat, 'type': mat}
                         for mat, _ in meshes_dict.items()]
    misc.write_obj(merged_meshes, merged_materials, sys.argv[3])
    misc.write_batchtable(merged_properties, sys.argv[4])
