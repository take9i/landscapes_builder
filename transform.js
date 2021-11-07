#!/usr/bin/env node
/*eslint no-console: "off"*/

const C = require('cesium');

const DEG2RAD = Math.PI / 180;

// gmaps zxy to lonlat (at left-top corner)
const zxy2lonlat = (tz, tx, ty) => {
  const n = Math.pow(2.0, tz);
  const lon = tx / n * 360.0 - 180.0
  const radlat = Math.atan(Math.sinh(Math.PI * (1 - 2 * ty / n)))
  const lat = radlat / (Math.PI / 180)
  return [lon, lat]
}

const get_bounds = (tz, tx, ty) => {
  const [w, n] = zxy2lonlat(tz, tx, ty)
  const [e, s] = zxy2lonlat(tz, tx + 1, ty + 1)
  return [w, s, e, n]
}

const get_transform = (tz, tx, ty) => {
  const [w, s] = zxy2lonlat(tz, tx, ty + 1)
  return C.Transforms.eastNorthUpToFixedFrame(C.Cartesian3.fromDegrees(w, s, 0));
}

if (require.main === module) {
  if (process.argv.length !== 5) {
    console.log('usage: transform.js z x y');
    process.exit();
  }

  const [z, x, y] = process.argv.slice(2, 5).map((a) => +a)
  const mat = get_transform(z, x, y);
  // console.log(JSON.stringify(mat));
  console.log(JSON.stringify(C.Matrix4.toArray(mat)));
}
