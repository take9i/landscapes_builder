#%%
import os
import numpy as np
import pandas as pd
from PIL import Image 
from landtile import tile as ltile
from landtile import mesh as lmesh
from landtile.dem import Dem


def crop_dem(src_path, tz, tx, ty, dst_path):
    w, h = ltile.get_meter_size(tz, tx, ty)
    os.system(f'gdal_translate -of "GTiff" -projwin 0 {h} {w} 0 {src_path} {dst_path}')

def create_stl(dem_path, tz, tx, ty):
    os.system(f'docker run --rm -v $(pwd):/home cognitiveearth/tin-terrain tin-terrain dem2tin --input {dem_path} --output ~~dem.obj --max-error 0.1')

    df = pd.read_table('~~dem.obj', header=None, sep=' ', names=['t', 'c1', 'c2', 'c3'])
    vdf = df[df.t == 'v']
    vertices = np.vstack([vdf.c1, vdf.c2, vdf.c3]).T
    fdf = df[df.t == 'f']
    faces = np.vstack([fdf.c1, fdf.c2, fdf.c3]).T.astype(int) - 1

    return lmesh.build_mesh(vertices, faces)

def write_obj(mesh, width, height, dst_obj):
    mesh.update_normals()
    base = os.path.splitext(os.path.basename(dst_obj))[0]
    with open(dst_obj, 'w') as fd:
        print = lambda s: fd.write(s + '\n')
        print(f'mtllib {base}.mtl')
        print(f'o {base}')
        print('usemtl None')
        for vs in mesh.vectors:
            for x, y, z in vs:
                print(f'v {x} {z} {-y}')
        for vs in mesh.vectors:
            for x, y, z in vs:
                print(f'vt {x / width} {y / height}')
        for x, y, z in mesh.normals:
            print(f'vn {x} {z} {-y}')
        print('s off')
        for i, vs in enumerate(mesh.vectors):
            j, k = i * 3 + 1, i + 1
            print(f'f {j}/{j}/{k} {j+1}/{j+1}/{k} {j+2}/{j+2}/{k}')

def write_mtl(texname, dst_mtl):
    with open(dst_mtl, 'w') as fd:
        print = lambda s: fd.write(s + '\n')
        print('newmtl None')
        print('Kd 1.0 1.0 1.0')
        print(f'map_Kd {texname}')

# --

def create(dem, tz, tx, ty, dst_name):
    os.system(f'rm -f ~~dem_[bc].tif')
    dem.save('~~dem_b.tif')
    crop_dem('~~dem_b.tif', tz, tx, ty, '~~dem_c.tif')

    mesh = create_stl('~~dem_c.tif', tz, tx, ty)
    width, height = ltile.get_meter_size(tz, tx, ty)
    write_obj(mesh, width, height, f'{dst_name}.obj')
    write_mtl(f'{os.path.basename(dst_name)}.png', f'{dst_name}.mtl')

def make_image(src_dir, tz, tx, ty, fetch_bias_z=2):
    w = 2 ** fetch_bias_z
    img = Image.new('RGB', (256 * w, 256 * w))
    for jj, j in enumerate(range(ty * w, ty * w + w)):
        for ii, i in enumerate(range(tx * w, tx * w + w)):
            path = os.path.join(src_dir, f'{tz + fetch_bias_z}/{i}/{j}.png')
            if os.path.exists(path):
                img.paste(Image.open(path), (ii * 256, jj * 256))
    return img


#%%
if __name__ == '__main__':
    Z, X, Y = 15, 29079, 12944
    dem = Dem(f'{Z}_{X}_{Y}_dem.tif')
    basename = f'{Z}_{X}_{Y}'
    create(dem, Z, X, Y, f'{Z}_{X}_{Y}_terrain')

    make_image('../map_drawer/maptiles/', Z, X, Y).save(f'{basename}.png')