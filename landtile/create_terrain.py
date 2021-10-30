#%%
import os
import numpy as np
import pandas as pd
from PIL import Image 
import misc

def create_stl(dem_path, tz, tx, ty):
    os.system(f'docker run --rm -v $(pwd):/home tin-terrain tin-terrain dem2tin --input {dem_path} --output ~ddem.obj --max-error 0.1')

    df = pd.read_table('~ddem.obj', header=None, sep=' ', names=['t', 'c1', 'c2', 'c3'])
    vdf = df[df.t == 'v']
    vertices = np.vstack([vdf.c1, vdf.c2, vdf.c3]).T
    fdf = df[df.t == 'f']
    faces = np.vstack([fdf.c1, fdf.c2, fdf.c3]).T.astype(np.int) - 1

    return misc.build_mesh(vertices, faces)

def make_tile_image(src_dir, tz, tx, ty):
    dz = 2  # 2 level下の画像を結合
    w = 2 ** dz
    img = Image.new('RGB', (256 * w, 256 * w))
    for jj, j in enumerate(range(ty * w, ty * w + w)):
        for ii, i in enumerate(range(tx * w, tx * w + w)):
            path = os.path.join(src_dir, f'{tz + dz}/{i}/{j}.png')
            if os.path.exists(path):
                img.paste(Image.open(path), (ii * 256, jj * 256))
    return img

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


#%%
import sys
import os
import misc

if __name__ == '__main__':
#     sys.argv = ['foo', '15_29079_12944_ddem.tif', 15, 29080, 12944, '15_29080_12944_terrain.obj']
    if len(sys.argv) != 6:
        sys.exit('usage: src_dem tz tx ty dst_obj')
        
    tz, tx, ty = [int(v) for v in sys.argv[2:5]]
    mesh = create_stl(sys.argv[1], tz, tx, ty)
    width, height = misc.get_cesium_tile_size(tz, tx, ty)
    bname = os.path.splitext(sys.argv[5])[0]
    write_obj(mesh, width, height, f'{bname}.obj')
    make_tile_image('../map_drawer/maptiles/', tz, tx, ty).save(f'{bname}.png')
    write_mtl(f'{bname}.png', f'{bname}.mtl')


#%%

# gdalwarp -t_srs EPSG:4612 15_29079_12944_ddem.tif a.tif
# ctb-tile -f Mesh -C -N -o ~t a.tif 

