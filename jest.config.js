const SCHEDULER = "<rootDir>/esp/public/media/scripts/ajaxschedulingmodule";

module.exports = {
  testEnvironment: "jsdom",
  testEnvironmentOptions: {
    // The scheduler builds its links relative to the page it is served from.
    url: "http://localhost/manage/TestProgram/2026_Summer/ajax_scheduling",
  },
  roots: [SCHEDULER],
  testMatch: ["**/spec/**/*Spec.js"],
  setupFiles: [`${SCHEDULER}/spec/support/setup.js`],
  restoreMocks: true,
  setupFilesAfterEnv: [`${SCHEDULER}/spec/support/cleanup.js`],
  transform: {
    "/ajaxschedulingmodule/ESP/.+\\.js$": `${SCHEDULER}/spec/support/exposeGlobals.js`,
  },
  coverageProvider: "v8",
  collectCoverageFrom: [
    "esp/public/media/scripts/ajaxschedulingmodule/ESP/**/*.js",
    // Page entry point: fetches data and starts the scheduler on load.
    "!esp/public/media/scripts/ajaxschedulingmodule/ESP/Main.js",
  ],
};
