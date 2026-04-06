/**
 * Minimal Jest globals for migrated ajax scheduler tests.
 */

global.contiguous_tolerance = '15';

global.palette = function(_name, count) {
  const out = [];
  for (let i = 0; i < count; i += 1) {
    const r = ((i * 37) % 255).toString(16).padStart(2, '0');
    const g = ((i * 67) % 255).toString(16).padStart(2, '0');
    const b = ((i * 97) % 255).toString(16).padStart(2, '0');
    out.push(`#${r}${g}${b}`);
  }
  return out;
};

global.$j = {
  each: function(obj, callback) {
    if (Array.isArray(obj)) {
      obj.forEach((item, index) => callback.call(item, index, item));
      return;
    }
    Object.keys(obj || {}).forEach((key) => callback.call(obj[key], key, obj[key]));
  }
};
