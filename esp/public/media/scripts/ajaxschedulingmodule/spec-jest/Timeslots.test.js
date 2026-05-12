const path = require('path');
const { loadLegacyScript } = require('./legacyLoader');

describe('Timeslots (migrated from Jasmine)', () => {
  beforeAll(() => {
    const root = path.resolve(__dirname, '..');
    loadLegacyScript(path.join(root, 'spec', 'TestFixtures.js'));
    loadLegacyScript(path.join(root, 'ESP', 'Timeslots.js'));
  });

  test('returns timeslot by id', () => {
    const times = global.time_fixture();
    const t = new global.Timeslots(times);

    expect(t.get_by_id(3)).toEqual(times[3]);
    expect(t.get_by_id(5)).toEqual(times[5]);
  });

  test('one-hour section schedules in single timeslot', () => {
    const times = global.time_fixture();
    const t = new global.Timeslots(times);
    const section = global.section_1();

    expect(t.get_timeslots_to_schedule_section(section, 3)).toEqual([3]);
  });

  test('two-hour section spans consecutive timeslots', () => {
    const times = global.time_fixture();
    const t = new global.Timeslots(times);
    const section = global.section_2();

    expect(t.get_timeslots_to_schedule_section(section, 3)).toEqual([3, 5]);
  });
});
