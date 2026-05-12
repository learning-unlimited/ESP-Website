const path = require('path');
const { loadLegacyScript } = require('./legacyLoader');

describe('CellColors (migrated from Jasmine)', () => {
  beforeAll(() => {
    const root = path.resolve(__dirname, '..');
    loadLegacyScript(path.join(root, 'spec', 'TestFixtures.js'));
    loadLegacyScript(path.join(root, 'ESP', 'CellColors.js'));
  });

  test('returns rgb object with numeric channels', () => {
    const cc = new global.CellColors();
    const section = global.section_1();
    section.emailcode = 'S1111s1';

    const color = cc.color(section);
    expect(color).toEqual(
      expect.objectContaining({
        r: expect.any(Number),
        g: expect.any(Number),
        b: expect.any(Number),
      })
    );
  });

  test('returns different colors for different classes', () => {
    const cc = new global.CellColors();
    const section1 = global.section_1();
    const section2 = global.section_2();
    section1.emailcode = 'S1111s1';
    section2.emailcode = 'A2222s1';

    expect(cc.color(section1)).not.toEqual(cc.color(section2));
  });
});
