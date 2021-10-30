#%%
import road
import misc

def build_mesh(segments, alts, base, top):
    f = lambda p, z: (p[0], p[1], z)
    meshes = []
    for s, (z1, z2) in zip(segments, alts):
        l1, r1, r2, l2 = s.exterior.coords[:4]
        z1b, z2b, z1t, z2t = z1 + base, z2 + base, z1 + top, z2 + top
        vertices = [f(l1, z1b), f(r1, z1b),  f(r2, z2b), f(l2, z2b),
                    f(l1, z1t), f(r1, z1t),  f(r2, z2t), f(l2, z2t)]
        faces = [[0,2,1],[0,3,2], [4,1,5],[4,0,1], [7,5,6],[7,4,5], [5,2,6],[5,1,2], [6,3,7],[6,2,3], [7,0,4],[7,3,0]]
        meshes.append(misc.build_mesh(vertices, faces))
    return misc.merge_meshes(meshes)

def build_meshes(df, dem):
    meshes, materials, properties = [], [], []
    for key, row in df.iterrows():
        try:
            width = road.get_width(row.rnkwidth, row.width)
            segments = road.build_segments(row.geom, width)
            alts = road.get_segment_alts(segments, row.geom, dem)
            if row.lvorder == 0 and row.state == '通常部':
                meshes.append(build_mesh(segments, alts, -10, 0))
            elif row.lvorder > 0 or row.state == '橋・高架':
                h = row.lvorder * 10
                meshes.append(build_mesh(segments, alts, h-2, h))
            else:
                continue
            materials.append(road.get_material(row.rdctg))
            properties.append({
                'type': row['type'], 'rdctg': row.rdctg, 'state': row.state
            })
        except ValueError as e:
            print(key, e)
    return meshes, materials, properties


#%%
import sys
import geopandas as gpd
from dem import Dem
import misc

if __name__ == '__main__':
    # sys.argv = ['foo', '~dem.tif', '15_29079_12944_roads.geojson', '15_29079_12944_roads.obj', '15_29079_12944_roads.json']
    if len(sys.argv) != 5:
        sys.exit('usage: src_dem roads_geojson dst_obj dst_json')

    dem = Dem(sys.argv[1])
    df = gpd.read_file(sys.argv[2])
    df = df.rename(columns={'geometry': 'geom'})  # db readでのcolumn nameに
    meshes, materials, properties = build_meshes(df, dem)
    # misc.merge_meshes(meshes).save('~roads.stl')
    misc.write_obj(meshes, materials, sys.argv[3])
    misc.write_batchtable(properties, sys.argv[4])

