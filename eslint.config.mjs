import js from "@eslint/js";
import globals from "globals";

export default [
  js.configs.recommended,
  {
    files: ["**/*.{js,mjs,cjs}"],
    languageOptions: {
      globals: {
        ...globals.browser,

        $j: "readonly",
        ApiClient: "readonly",
        Timeslots: "readonly",
        Sections: "readonly",
        has_moderator_module: "readonly",
        ModeratorDirectory: "readonly",
        MessagePanel: "readonly",
        SectionCommentDialog: "readonly",
        SectionInfoPanel: "readonly",
        Matrix: "readonly",
        Directory: "readonly",
        ChangelogFetcher: "readonly",
        printJS: "readonly",
        jqueryui_version: "readonly",
        check_csrf_cookie: "readonly",
      },
    },
  },
];
