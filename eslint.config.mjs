import js from "@eslint/js";
import globals from "globals";
import { defineConfig } from "eslint/config";

export default defineConfig([
  {
    files: ["**/*.{js,mjs,cjs}"],
    plugins: { js },
    extends: ["js/recommended"],
    languageOptions: {
      globals: {
        ...globals.browser,

        // 👇 ADD THESE
        $j: "readonly",
        ApiClient: "readonly",
        Timeslots: "readonly",
        Sections: "readonly",
        requests: "readonly",
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
        ui: "readonly",
        evt: "readonly",  
        
      },
    },
  },
]);
