const fs = require('fs');
const vm = require('vm');

function loadLegacyScript(filePath) {
  const code = fs.readFileSync(filePath, 'utf-8');
  const names = [];
  const pattern = /function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\(/g;
  let match;
  while ((match = pattern.exec(code)) !== null) {
    names.push(match[1]);
  }

  const exportLines = names
    .map((name) => `if (typeof ${name} !== 'undefined') global.${name} = ${name};`)
    .join('\n');

  vm.runInNewContext(`${code}\n${exportLines}`, global, { filename: filePath });
}

module.exports = {
  loadLegacyScript,
};
