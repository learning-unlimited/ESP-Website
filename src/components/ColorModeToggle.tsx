import { useState } from "react";
import { IconButton } from "@chakra-ui/react";
import { SunIcon, MoonIcon } from "@chakra-ui/icons";

const ColorModeToggle = () => {
  const [dark, setDark] = useState(false);

  const toggleMode = () => {
    const newMode = !dark;
    setDark(newMode);

    if (newMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  };

  return (
    <IconButton aria-label="Toggle Dark Mode" onClick={toggleMode}>
      {dark ? <SunIcon /> : <MoonIcon />}
    </IconButton>
  );
};

export default ColorModeToggle;