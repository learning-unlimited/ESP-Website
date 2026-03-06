// src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { Provider, createSystem, defaultConfig } from "@chakra-ui/react";
import { theme as baseTheme } from "./theme";

const system = createSystem(defaultConfig, baseTheme);

import App from "./App";

const rootElement = document.getElementById("root") as HTMLElement;

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <Provider value={system}>
      <App />
    </Provider>
  </React.StrictMode>
);