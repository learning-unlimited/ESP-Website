import js from "@eslint/js";
import globals from "globals";

//  Browser scripts ESLint enforces today.  The media directory is dominated by
//  vendored libraries (jQuery, YUI, prototype, jqGrid, ...) and by Django
//  templates that happen to end in .js, neither of which we can usefully lint,
//  so this list is an opt-in ratchet: add a file here once it is clean.
const lintedScripts = [
    "esp/esp/themes/theme_data/floaty/scripts/main.js",
    "esp/public/media/scripts/ajax_tools.js",
    "esp/public/media/scripts/ajaxschedulingmodule/ESP/Scheduler.js",
];

//  The browser's own Scheduler (the Prioritized Task Scheduling API) collides
//  with the ajax scheduler's Scheduler constructor, which is the name pages
//  actually use.
const browserGlobals = { ...globals.browser };
delete browserGlobals.Scheduler;

//  jQuery hands handlers a fixed argument list, so a handler that needs a later
//  argument has to name the earlier ones.
const noUnusedVars = ["error", { args: "after-used", argsIgnorePattern: "^_" }];

export default [
    //  Lint nothing by default, then un-ignore the files below.  Without this
    //  ESLint applies its default config -- and so reports parse errors -- to
    //  every other .js file in the repository.
    {
        ignores: [
            "**/*.{js,mjs,cjs}",
            "!eslint.config.mjs",
            ...lintedScripts.map((file) => `!${file}`),
        ],
    },
    {
        ...js.configs.recommended,
        files: ["eslint.config.mjs"],
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: "module",
            globals: globals.nodeBuiltin,
        },
    },
    {
        ...js.configs.recommended,
        files: lintedScripts,
        languageOptions: {
            ecmaVersion: 2022,
            //  These are served to the browser with a plain <script> tag, not as
            //  ES modules, so top-level declarations are globals rather than
            //  module-scoped bindings.
            sourceType: "script",
            globals: {
                ...browserGlobals,
                $j: "readonly",
                check_csrf_cookie: "readonly",
                jqueryui_version: "readonly",
                printJS: "readonly",
                //  Ajax scheduler collaborators, each loaded from its own file by
                //  templates/program/modules/ajaxschedulingmodule/ajax_scheduling.html
                ApiClient: "readonly",
                ChangelogFetcher: "readonly",
                Directory: "readonly",
                Matrix: "readonly",
                MessagePanel: "readonly",
                ModeratorDirectory: "readonly",
                SectionCommentDialog: "readonly",
                SectionInfoPanel: "readonly",
                Sections: "readonly",
                Timeslots: "readonly",
                has_moderator_module: "readonly",
            },
        },
        rules: {
            ...js.configs.recommended.rules,
            "no-unused-vars": noUnusedVars,
        },
    },
];
