import React from "react";
import { Box, Flex, Heading } from "@chakra-ui/react";
import ColorModeToggle from "./ColorModeToggle";

export const Header = () => (
  <Flex
    as="header"
    justify="space-between"
    align="center"
    padding="1rem"
    bg="gray.100"
    _dark={{ bg: "gray.900" }}
  >
    <Heading size="md">ESP Website</Heading>
    <ColorModeToggle />
  </Flex>
);