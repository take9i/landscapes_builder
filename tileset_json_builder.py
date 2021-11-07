#%%
import subprocess
import json
import math
import numpy as np
from landtile.tile import get_bounds, num2lonlat

def get_transform(z, x, y):
    result = subprocess.Popen(
        f'./transform.js {z} {x} {y}',
        stdout=subprocess.PIPE, shell=True
    ).communicate()[0]
    return json.loads(result)

def build(tiles):
    def get_geom_error(z):
        return 2 ** (19 - z)

    def get_region(bounds):
        w, s, e, n = [math.radians(a) for a in bounds]
        return [w, s, e, n, 0, 100]

    def build_tileinfos(z, x, y):
        def get_tileinfo(z, x, y):
            return {
                'transform': get_transform(z, x, y),
                'boundingVolume': {
                    'region': get_region(get_bounds(z, x, y))
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

    tiles = np.array(tiles, dtype='int32')
    z = int(min(tiles[:, 0]))
    x1, x2 = int(min(xs := tiles[:, 1])), int(max(xs) + 1)
    y1, y2 = int(min(ys := tiles[:, 2])), int(max(ys) + 1)
    w, n = num2lonlat(z, x1, y1)
    e, s = num2lonlat(z, x2, y2)
    stop_z = z

    return {
      'asset': {
        'version': '1.0'
      },
      'geometricError': get_geom_error(z),
      'root': {
        'boundingVolume': {
          'region': get_region([w, s, e, n])
        },
        'geometricError': get_geom_error(z),
        'refine': 'REPLACE',
        'children': [build_tileinfos(z, x, y) for x in range(x1, x2) for y in range(y1, y2)]
      }
    }

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
  build(TILES)
