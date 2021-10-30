#%%
from landtile import road
from landtile import mesh as lmesh


def build_mesh(segments, alts, base, top):
    f = lambda p, z: (p[0], p[1], z)
    meshes = []
    for s, (z1, z2) in zip(segments, alts):
        l1, r1, r2, l2 = s.exterior.coords[:4]
        z1b, z2b, z1t, z2t = z1 + base, z2 + base, z1 + top, z2 + top
        vertices = [f(l1, z1b), f(r1, z1b),  f(r2, z2b), f(l2, z2b),
                    f(l1, z1t), f(r1, z1t),  f(r2, z2t), f(l2, z2t)]
        faces = [[0,2,1],[0,3,2], [4,1,5],[4,0,1], [7,5,6],[7,4,5], [5,2,6],[5,1,2], [6,3,7],[6,2,3], [7,0,4],[7,3,0]]
        meshes.append(lmesh.build_mesh(vertices, faces))
    return lmesh.merge_meshes(meshes)

# --

def build(dem, df):
    meshes, materials, properties = [], [], []
    for key, row in df.iterrows():
        try:
            width = road.get_width(row.rnkWidth, row.Width)
            segments = road.build_segments(row.geometry, width)
            alts = road.get_segment_alts(segments, row.geometry, dem)
            if row.lvOrder == 0 and row.state == '通常部':
                meshes.append(build_mesh(segments, alts, -10, 0))
            elif row.lvOrder > 0 or row.state == '橋・高架':
                h = row.lvOrder * 10
                meshes.append(build_mesh(segments, alts, h-2, h))
            else:
                continue
            materials.append(road.get_material(row.rdCtg))
            properties.append({
                'type': row['type'], 'rdCtg': row.rdCtg, 'state': row.state
            })
        except ValueError as e:
            print(key, e)
    return meshes, materials, properties


#%%
from landtile import roads_weaver as rw
from landtile import dem_digger as dd

if __name__ == '__main__':
    GPKG = 'enoshima_shape.gpkg'
    DEM = 'enoshima_dem.vrt'
    Z, X, Y = 15, 29079, 12944
    df = rw.weave(GPKG, Z, X, Y)
    dem = dd.undig(DEM, Z, X, Y)  # 整地しない場合
    meshes, materials, properties = build(dem, df)
    # lmesh.merge_meshes(meshes).save('~roads.stl')
    lmesh.write_obj(meshes, materials, f'{Z}_{X}_{Y}_roads.obj')
    lmesh.write_batchtable(properties, f'{Z}_{X}_{Y}_roads.json')
