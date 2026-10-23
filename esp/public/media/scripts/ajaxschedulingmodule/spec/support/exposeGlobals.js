/**
 * Jest transform for the scheduler's browser scripts.
 *
 * In the browser each script's top-level function declarations become globals
 * that the other scripts use. Jest runs every file in its own module scope, so
 * this re-exposes them on the global object. The scripts themselves are left
 * untouched, and the extra code goes on a new last line so that line numbers
 * (and therefore coverage) still match the source file.
 */
const TOP_LEVEL_FUNCTION = /^function\s+([A-Za-z_$][\w$]*)\s*\(/gm;

module.exports = {
  process(sourceText) {
    const names = Array.from(sourceText.matchAll(TOP_LEVEL_FUNCTION), (match) => match[1]);
    const assignments = names.map((name) => `globalThis.${name} = ${name};`).join(" ");
    return { code: `${sourceText}\n${assignments}\n` };
  },
};
