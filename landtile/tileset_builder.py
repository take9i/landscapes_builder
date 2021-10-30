#%%
import os
import json
from landtile.tile import get_bounds, num2lonlat

def get_base_tileset(tiles, stop_z):
    def get_geom_error(z):
        return 2 ** (19 - z)

    def build_tileinfos(z, x, y):
        def get_tileinfo(z, x, y):
            return {
                'transform': None,
                'boundingVolume': {
                    'region': get_bounds(z, x, y)
                },
                'geometricError': get_geom_error(z),
                'content': {
                    'url': f'{z}_{x}_{y}.b3dm'
                }
            }

        if z == stop_z:
            return get_tileinfo(z, x, y)
        else:
            tileinfo = get_tileinfo(z, x, y)
            tileinfo['children'] = [build_tileinfos(z+1, i, j) 
                                    for i in range(x*2, x*2+2) for j in range(y*2, y*2+2)]
            del tileinfo['content']
            return tileinfo

    values = lambda i: [t[i] for t in tiles]
    zs, xs, ys = values(0), values(1), values(2)
    z, x1, y1, x2, y2 = min(zs), min(xs), min(ys), max(xs) + 1, max(ys) + 1
    w, n = num2lonlat(z, x1, y1)
    e, s = num2lonlat(z, x2, y2)
    root_bounds = [w, s, e, n]
    return {
      'asset': {
        'version': '1.0'
      },
      'geometricError': get_geom_error(z),
      'root': {
        'boundingVolume': {
          'region': root_bounds
        },
        'geometricError': get_geom_error(z),
        'refine': 'REPLACE',
        'children': [build_tileinfos(z, x, y) for x in range(x1, x2) for y in range(y1, y2)]
      }
    }

def build(tiles, dst_dir):
  stop_z = min([z for (z, x, y) in tiles])
  open('_tileset.json', 'w').write(json.dumps(get_base_tileset(tiles, stop_z)))
  os.system(f'./tileset_maker.js _tileset.json {dst_dir}/tileset.json')

#%%
if __name__ == '__main__':
  TILES = [
      (15, 29079, 12944),  # 片瀬海岸
      (15, 29080, 12944),  # 龍口寺
      (15, 29081, 12944),  # 津西
      (15, 29079, 12945),  # 江の島参道
      (15, 29080, 12945),  # 湘南港
      (15, 29081, 12945),  # 鎌倉高校前
      (15, 29079, 12946),  # 江の島岩屋
      (15, 29080, 12946),  # 江の島灯台
  ]
  DST_DIR = 'dst/gsi_enoshima_5m_unleveled/terrain'
  build(TILES, DST_DIR)
