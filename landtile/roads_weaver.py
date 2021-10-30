#%%
import os
import json
import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString
import numpy as np
from landtile import tile as ltile

def build_network(df):
    node = lambda coord: '_'.join(map(str, coord))
    get_edge = lambda r: [
        node(r.geometry.coords[0]), node(r.geometry.coords[-1]),
        {k: v for k, v in r.items() if v == v}]  # filter np.nan
    g = nx.Graph()
    g.add_edges_from([get_edge(row) for key, row in df.iterrows()])
    return g

def weave_roads(g):
    def get_foldable_nodes(g):
        cand_nodes = [v for v, d in g.degree if d == 2]
        get_class = lambda e: [e[k] for k in e.keys() if k != 'geometry']
        foldable_nodes = []
        for node in cand_nodes:
            edge1, edge2 = [g[node][nb] for nb in g.neighbors(node)]
            if get_class(edge1) == get_class(edge2):
                foldable_nodes.append(node)
        return foldable_nodes

    def trim_node(g, node):
        def join_geom(geom1, geom2):
            if geom1.coords[-1] == geom2.coords[0]:
                return LineString(geom1.coords[:] + geom2.coords[1:])
            elif geom1.coords[-1] == geom2.coords[-1]:
                return LineString(geom1.coords[:] + geom2.coords[-2::-1])
            elif geom1.coords[0] == geom2.coords[0]:
                return LineString(geom1.coords[::-1] + geom2.coords[1:])
            elif geom1.coords[0] == geom2.coords[-1]:
                return LineString(geom1.coords[::-1] + geom2.coords[-2::-1])
            else:
                raise ValueError('error!')

        a, b = g.neighbors(node)
        attrs = g[node][a].copy()
        attrs['geometry'] = join_geom(g[node][a]['geometry'], g[node][b]['geometry'])
        g.remove_node(node)
        g.add_edges_from([(a, b, attrs)])
    
    while True:
        foldable_nodes = get_foldable_nodes(g)
        if not foldable_nodes:
            break
        trim_node(g, foldable_nodes[0])

def write_geojson(g, path):
    def np_conv(v):
        if isinstance(v, np.integer):
            return int(v)
        elif isinstance(v, np.floating):
            return float(v)
        elif isinstance(v, np.ndarray):
            return v.tolist()
        else:
            return v
    
    def get_feature(edge):
        return {
            'type': 'Feature',
            'geometry': {
                'type': 'LineString',
                'coordinates': edge['geometry'].coords[:]
            },
            'properties': {k:np_conv(v) for k, v in edge.items() if k != 'geometry'}
        }

    geoj = {
        'type': 'FeatureCollection',
        'features': [get_feature(g[e1][e2]) for e1, e2 in g.edges]
    }
    open(path, 'w').write(json.dumps(geoj, ensure_ascii=False))

def write_empty_geojson(path):
    geoj = {
        'type': 'FeatureCollection',
        'features': []
    }
    open(path, 'w').write(json.dumps(geoj, ensure_ascii=False))

# --

def weave(shape_gpkg, tz, tx, ty):
    bbox = ltile.get_bounds(tz, tx, ty)
    proj = ltile.get_meter_proj(tz, tx, ty)
    df = gpd.read_file(shape_gpkg, layer='RdCL', bbox=bbox).to_crs(proj)
    df = df[df.geom_type == 'LineString']
    df = df[~df.apply(lambda r: r.geometry.is_ring, axis=1)]
    df = df[(df['type'] == '通常部') & 
        df.rnkWidth.isin(['3m-5.5m未満', '5.5m-13m未満', '13m-19.5m未満', '19.5m以上'])] 

    os.system(f'rm -f ~~weaved.geojson')
    if df.empty:
        write_empty_geojson('~~weaved.geojson')
        print('there is no target road!')
    else:
        g = build_network(df)
        weave_roads(g)
        write_geojson(g, '~~weaved.geojson')
    return gpd.read_file('~~weaved.geojson')

#%%
if __name__ == '__main__':
    Z, X, Y = 15, 29079, 12944
    df = weave('~xxx_shape.gpkg', tz, tx, ty)
    df.to_file(f'{Z}_{X}_{Y}_roads.geojson', driver='GeoJSON')

#%%
# # plot network
# import networkx as nx
# import matplotlib.pyplot as plt
# pos = {n:tuple(map(float, n.split('_'))) for n in g.nodes}
# nx.draw(g, pos, node_size=10)
# plt.show()


#%%
# # plot geojson
# import geopandas as gpd
# import matplotlib.pyplot as plt
# df = gpd.read_file('~weaved_roads.geojson')
# df.plot()
# plt.show()


