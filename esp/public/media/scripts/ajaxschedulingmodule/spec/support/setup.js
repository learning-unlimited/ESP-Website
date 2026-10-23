/**
 * Recreates the page that ajax_scheduling.html builds before the scheduler
 * starts: the third-party libraries, the template variables, and then the
 * scheduler scripts themselves, loaded in the same order as the template.
 */
const path = require("path");

const SCHEDULER_DIR = path.resolve(__dirname, "../..");
const SCRIPTS_DIR = path.resolve(SCHEDULER_DIR, "..");

// Third-party libraries, pinned in package.json to the versions the page loads
const jQuery = require("jquery");
global.jQuery = global.$j = jQuery;
jQuery.migrateMute = true;
require("jquery-migrate");
require("jquery-ui/dist/jquery-ui.js");
require(path.join(SCHEDULER_DIR, "lib/fixed_table_rc.js"));
global.palette = require("google-palette");
global._ = require(path.join(SCRIPTS_DIR, "lodash.compat.min.js"));

// Template variables
Object.assign(global, {
  base_url: "TestProgram/2026_Summer",
  prog_id: "1",
  program_base_url: "/json/TestProgram/2026_Summer/",
  has_autoscheduler_frontend: "False",
  has_moderator_module: "False",
  // The default value of the timeblock_contiguous_tolerance tag
  contiguous_tolerance: "20",
  moderator_title: "Moderator",
  jqueryui_version: "1.13.2",
});

// Stands in for csrf_init.js, which reads the token from a cookie
global.csrf_token = () => "abcd";

[
  "CellColors",
  "Timeslots",
  "ApiClient",
  "Cell",
  "Sections",
  "Directory",
  "Moderators",
  "Matrix",
  "MessagePanel",
  "SectionCommentDialog",
  "SectionInfoPanel",
  "ChangelogFetcher",
  "Scheduler",
].forEach((name) => require(path.join(SCHEDULER_DIR, "ESP", `${name}.js`)));
