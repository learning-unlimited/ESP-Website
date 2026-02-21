module.exports = {
    "env": {
        "browser": true,
        "es6": true,
        "jquery": true
    },
    "extends": "eslint:recommended",
    "parserOptions": {
        "ecmaVersion": 2018,
        "sourceType": "script"
    },
    "rules": {
        "no-unused-vars": ["warn", { "vars": "all", "args": "none" }],
        "no-console": "off",
        "no-undef": "warn"
    },
    "globals": {
        "$": "readonly",
        "$j": "readonly",
        "django": "readonly",
        "Scheduler": "readonly",
        "Timeslots": "readonly",
        "Sections": "readonly",
        "Matrix": "readonly",
        "Directory": "readonly",
        "ChangelogFetcher": "readonly",
        "ApiClient": "readonly",
        "ModeratorDirectory": "readonly",
        "MessagePanel": "readonly",
        "SectionCommentDialog": "readonly",
        "SectionInfoPanel": "readonly",
        "printJS": "readonly",
        "has_moderator_module": "readonly",
        "jqueryui_version": "readonly",
        "json_get": "readonly",
        "json_fetch": "readonly"
    }
};
