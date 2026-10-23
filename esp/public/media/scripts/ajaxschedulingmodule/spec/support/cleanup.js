/**
 * The scheduler binds its event handlers to <body>, which lives for a whole
 * test file, so reset it between tests to keep them independent.
 */
afterEach(() => {
  $j("body").off().empty();
});
