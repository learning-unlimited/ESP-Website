module.exports = {
  testEnvironment: 'jsdom',
  testMatch: [
    '**/esp/public/media/scripts/ajaxschedulingmodule/spec-jest/**/*.test.js'
  ],
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  collectCoverageFrom: [
    'esp/public/media/scripts/ajaxschedulingmodule/ESP/**/*.js',
    '!esp/public/media/scripts/ajaxschedulingmodule/ESP/**/*.spec.js',
    '!esp/public/media/scripts/ajaxschedulingmodule/spec/**'
  ],
  coveragePathIgnorePatterns: [
    '/node_modules/',
    'spec/',
    'lib/'
  ]
};
