// src/theme.ts
import { createSystem, defaultConfig } from "@chakra-ui/react";

// Configure color mode in the theme
const customConfig = {
  ...defaultConfig,
  theme: {
    config: {
      initialColorMode: "light", // or "dark"
      useSystemColorMode: true,
    },
  },
};

export const theme = createSystem(customConfig);