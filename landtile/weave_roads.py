#%%
import psycopg2
import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString
import json
import numpy as np
import common.tile_utils as tu
import misc

def get_df(tz, tx, ty):
    w, s, e, n = tu.get_tile_bounds(tz, tx, ty)
    sql = f'with tmp as (select st_makeenvelope({w}, {s}, {e}, {n}, 4612) as enve) select type, rdctg, state, lvorder, rnkwidth, width, st_intersection(geom, tmp.enve) as geom from rdcl join tmp on st_intersects(geom, tmp.enve);'
    conn = psycopg2.connect(database='gsi', user='')
    df = gpd.GeoDataFrame.from_postgis(sql, conn)
    proj = misc.get_cesium_proj_str(tz, tx, ty)
    return df[df.geom.is_valid].to_crs(proj)

def build_network(df):
    node = lambda coord: '_'.join(map(str, coord))
    get_edge = lambda r: [node(r.geom.coords[0]), node(r.geom.coords[-1]), 
                          {k: v for k, v in r.items() if v == v}]
                          # filter np.nan by 'v == v'  
    g = nx.Graph()
    g.add_edges_from([get_edge(row) for key, row in df.iterrows()])
    return g

def weave_roads(g):
    def get_foldable_nodes(g):
        cand_nodes = [v for v, d in g.degree if d == 2]
        get_class = lambda e: [e[k] for k in e.keys() if k != 'geom']
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
        attrs['geom'] = join_geom(g[node][a]['geom'], g[node][b]['geom'])
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
                'coordinates': edge['geom'].coords[:]
            },
            'properties': {k:np_conv(v) for k, v in edge.items() if k != 'geom'}
        }

    geoj = {
        'type': 'FeatureCollection',
        'features': [get_feature(g[e1][e2]) for e1, e2 in g.edges]
    }
    open(path, 'w').write(json.dumps(geoj, ensure_ascii=False))


#%%
import os
import sys

if __name__ == '__main__':
    # sys.argv = ['foo', 15, 29080, 12944, 'a.geojson']
    if len(sys.argv) != 5:
        sys.exit('usage: tz tx ty dst_geojson')
        
    tz, tx, ty = [int(v) for v in sys.argv[1:4]]
    df = get_df(tz, tx, ty)
    df = df[(df.geom.type == 'LineString')]
    df = df[~df.apply(lambda r: r.geom.is_ring, axis=1)]
    df = df[(df['type'] == '通常部') & 
        df.rnkwidth.isin(['3m-5.5m未満', '5.5m-13m未満', '13m-19.5m未満', '19.5m以上'])] 
    if df.empty:
        raise ValueError('there is no target road')

    g = build_network(df)
    weave_roads(g)
    write_geojson(g, sys.argv[4])


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


