#!/usr/bin/env node
/*eslint no-console: "off"*/

const fs = require('fs');
const Cesium = require('cesium');

const DEG2RAD = Math.PI / 180;

if (require.main === module) {
  if (process.argv.length !== 4) {
    console.log('usage: tileset_maker2.js src_json dst_json');
    process.exit();
  }

  function calc_transforms(parent) {
    function get_mat(tile) {
      const [w, s, e, n] = tile.boundingVolume.region;
      return Cesium.Transforms.headingPitchRollToFixedFrame(
        Cesium.Cartesian3.fromDegrees(w, s, 0), new Cesium.HeadingPitchRoll()
      );
    }

    if ('children' in parent) {
      parent.children.forEach(child => {
        if (parent.transform) {
          // calc mat for cancel parent mat
          const piMat = Cesium.Matrix4.inverse(get_mat(parent), new Cesium.Matrix4());
          const mat = Cesium.Matrix4.multiply(piMat, get_mat(child), new Cesium.Matrix4());
          child.transform = Cesium.Matrix4.toArray(mat);
        } else {
          child.transform = Cesium.Matrix4.toArray(get_mat(child));
        }

        calc_transforms(child);
      });
    }
  }

  function adjust_region(tile) {
    const [w, s, e, n] = tile.boundingVolume.region;
    tile.boundingVolume.region =
      [w * DEG2RAD, s * DEG2RAD, e * DEG2RAD, n * DEG2RAD, 0, 100];

    if ('children' in tile) {
      tile.children.forEach(child => {
        adjust_region(child);
      });
    }
  }

  const tileset = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  calc_transforms(tileset.root);
  adjust_region(tileset.root);
  fs.writeFileSync(process.argv[3], JSON.stringify(tileset, null, '  '));
}

