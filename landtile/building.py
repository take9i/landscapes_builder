#%%
from shapely.geometry import Point, MultiPoint, Polygon, MultiLineString
from shapely.ops import nearest_points

def get_alt(polygon, floor, dem):
    minalt = min([dem.get_alt(c) for c in polygon.exterior.coords])
    maxalt = max([dem.get_alt(c) for c in polygon.exterior.coords])
    return maxalt - 4 if minalt + floor * 4 < maxalt else minalt

def get_material(the_type):
    if the_type in ['普通無壁舎', '堅ろう無壁舎']:
        return 'building3'
    elif the_type in ['堅ろう建物', '高層建物']:
        return 'building'
    else:
        return 'building2'
