#%%
from shapely.geometry import Point, MultiPoint, Polygon, MultiLineString
from shapely.ops import nearest_points

def build_segments(center_line, width):
    def get_side_lines(center_line, width):
        hw = width / 2
        left_line = center_line.parallel_offset(
            hw, 'left', join_style=3).simplify(0.5, preserve_topology=False)
        right_line = center_line.parallel_offset(
            hw, 'right', join_style=3).simplify(0.5, preserve_topology=False)
        if left_line.is_empty or right_line.is_empty:
            raise ValueError('left/right line is empty')
        elif type(left_line) == MultiLineString or type(right_line) == MultiLineString:
            raise ValueError('left/right line is multiline')
        right_line.coords = list(right_line.coords)[::-1]
        return left_line, right_line

    def get_crossbars(left_line, right_line):
        left_mp = MultiPoint(left_line.coords)
        right_mp = MultiPoint(right_line.coords)
        left_ps = list(left_mp.geoms)
        right_ps = list(right_mp.geoms)
        l2rs = []
        for il, l in enumerate(left_mp.geoms):
            r = nearest_points(l, right_mp)[1]
            l2rs.append((il, right_ps.index(r)))
        for ir, r in enumerate(right_mp.geoms):
            l = nearest_points(r, left_mp)[1]
            l2rs.append((left_ps.index(l), ir))
        crossbars = sorted(set(l2rs), key=lambda x: (x[0], x[1]))
        return left_ps, right_ps, crossbars

    def slim_crossbars(left_ps, right_ps, left2rights, ratio):
        def f(p, q, r): return (p.x * (1 - r) +
                                q.x * r, p.y * (1 - r) + q.y * r)
        nleft_ps, nright_ps, nl2rs = [], [], []
        for il, ir in left2rights:
            l, r = left_ps[il], right_ps[ir]
            nl, nr = f(l, r, ratio), f(l, r, 1 - ratio)
            inl, inr = len(nleft_ps), len(nright_ps)
            nleft_ps.append(nl)
            nright_ps.append(nr)
            nl2rs.append((inl, inr))
        return nleft_ps, nright_ps, nl2rs

    left_line, right_line = get_side_lines(center_line, width * 1.2)
    left_ps, right_ps, crossbars = get_crossbars(left_line, right_line)
    valids = [((il1 <= il2) and (ir1 <= ir2))
              for (il1, ir1), (il2, ir2) in zip(crossbars[:-1], crossbars[1:])]
    if not all(valids):
        # TODO: fix incorrect ladder case
        raise ValueError('incorrect ladder')
    left_ps, right_ps, crossbars = slim_crossbars(
        left_ps, right_ps, crossbars, 0.1/1.2)
    return [Polygon([left_ps[il1], right_ps[ir1], right_ps[ir2], left_ps[il2]])
            for (il1, ir1), (il2, ir2) in zip(crossbars[:-1], crossbars[1:])]

def get_segment_alts(segments, center_line, dem):
    poss = [MultiPoint(s.exterior.coords[:2]).centroid.coords[0] for s in segments] + \
        [MultiPoint(segments[-1].exterior.coords[2:4]).centroid.coords[0]]
    center_poss = [nearest_points(center_line, Point(p))[
        0].coords[0] for p in poss]
    alts = [dem.get_alt(p) for p in center_poss]
    return [(a1, a2) for a1, a2 in zip(alts[:-1], alts[1:])]

def get_width(rnkwidth, width):
    table = {
        '3m-5.5m未満': lambda _: 5,
        '5.5m-13m未満': lambda _: 10,
        '13m-19.5m未満': lambda _: 15,
        '19.5m以上': lambda w: 20 if w != w else w  # w=np.nan, 20
    }
    return table[rnkwidth](width)

def get_material(rdctg):
    table = {
        '高速自動車国道等': 'motorway',
        '国道': 'trunk',
        '都道府県道': 'primary',
        '市区町村道等': 'secondary'
    }
    return table[rdctg]

#%%
if False:  # plot segments for debug
    from shapely.geometry import Point, MultiPoint, Polygon, LineString, MultiLineString
    import matplotlib.pyplot as plt
    import matplotlib
    import geopandas as gpd
    import misc

    proj = misc.get_cesium_proj_str(15, 29080, 12944)
    df = gpd.read_file('~weaved_roads.geojson').to_crs(proj)
    df = df.rename(columns={'geometry': 'geom'})  # dbからread時のcolumn nameに
    # geom = df.loc[34].geom
    geom = df.loc[85].geom

    segments = build_segments(geom, 10)
    wsegments = build_segments(geom, 20)

    matplotlib.rcParams['figure.figsize'] = 16, 16
    plt.gca().set_aspect('equal', adjustable='box')
    for s in segments:
        plt.plot(*s.exterior.xy, 'r')
    for s in wsegments:
        plt.plot(*s.exterior.xy, 'g')
    plt.show()

