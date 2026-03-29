# Design System Specification

## 1. Overview & Creative North Star
### The Vigilant Academic
This design system is built for the high-stakes environment of live event management. Moving away from the cluttered, "spreadsheet" aesthetic of traditional administrative tools, we adopt **The Vigilant Academic** as our North Star. This philosophy blends the authoritative clarity of high-end editorial journals with the hyper-functional responsiveness required in high-pressure corridors and outdoor environments.

The system breaks the "template" look through **intentional asymmetry** and **tonal layering**. We treat the mobile screen not as a flat canvas, but as a series of physical, tactile sheets. By utilizing high-contrast typography and wide breathing room (even in data-dense views), we ensure that the interface is glanceable under direct sunlight or while moving through a crowd.

---

## 2. Colors & Surface Philosophy
The palette is rooted in a professional foundation of deep teals and authoritative blues, contrasted against a pristine, "Paper White" background.

### The Color Tokens
- **Primary Action (`primary` #003d9a):** Reserved exclusively for high-priority navigation and primary buttons.
- **Brand Thematics (`tertiary_container` #006666):** Used for educational headers, branding accents, and secondary status indicators to honor the legacy ESP aesthetic.
- **Surface Palette:** We utilize a tiered system from `surface-container-lowest` (#ffffff) to `surface-container-highest` (#e1e3e4).

### The "No-Line" Rule
To achieve a premium, custom feel, **1px solid borders are strictly prohibited** for sectioning. Structural boundaries must be defined solely through background color shifts. For example, a card (`surface-container-lowest`) sits on a background of `surface-container-low` (#f3f4f5) to create a clear but soft distinction.

### The "Glass & Gradient" Rule
Flat buttons are for secondary actions only. For primary conversion points, use a subtle **Signature Gradient** transitioning from `primary` (#003d9a) to `primary_container` (#0053cb). This provides a "soul" and professional polish that feels custom-built. Floating elements, such as Live Overlays, should utilize **Glassmorphism** (semi-transparent `surface` colors with a 12px backdrop-blur) to maintain context of the content beneath.

---

## 3. Typography
The typography system pairs **Public Sans** (Display/Headlines) with **Inter** (Body/Labels) to balance editorial character with technical legibility.

- **Display & Headlines (Public Sans):** Large, bold, and authoritative. These are designed to be read at arm's length in high-pressure scenarios. 
  - *Headline-LG (2rem)*: Used for screen titles.
- **Body & Titles (Inter):** Highly legible and neutral. 
  - *Title-MD (1.125rem)*: Used for card headers and primary data points.
  - *Body-LG (1rem)*: The standard for all readable content to ensure accessibility in outdoor glare.

---

## 4. Elevation & Depth
Hierarchy is achieved through **Tonal Layering** rather than traditional drop shadows.

### The Layering Principle
Depth is created by "stacking" surface tiers.
- **Level 0 (Base):** `surface` (#f8f9fa)
- **Level 1 (Sections):** `surface-container-low` (#f3f4f5)
- **Level 2 (Cards):** `surface-container-lowest` (#ffffff)

### Ambient Shadows
When an element must float (e.g., a "New Alert" FAB), use an **Ambient Shadow**:
- **Color:** Tinted `on-surface` (#191c1d) at 6% opacity.
- **Blur:** Large (16px to 24px) with 0 spread to mimic natural light.

### The "Ghost Border" Fallback
If high-contrast environments demand a border for accessibility, use the **Ghost Border**: the `outline-variant` token (#bec9c8) at 15% opacity. Never use 100% opaque borders.

---

## 5. Components

### Primary Buttons
- **Min-Height:** 48px (exceeding the 44px tap target mandate).
- **Style:** `primary` gradient fill with `on-primary` (#ffffff) text.
- **Corner Radius:** `lg` (0.5rem) for a modern, friendly but professional feel.

### Summary Cards
- **Construction:** Use `surface-container-lowest` background. 
- **Rule:** **No divider lines.** Separate content using `spacing-4` (1rem) vertical white space or a subtle `surface-container-high` (#e7e8e9) background block for secondary metadata.

### Pulsing Live Badges
- **Visuals:** A small circular dot using `secondary` (#096969) for "Live" status.
- **Motion:** A double-ring pulse animation. The outer ring expands and fades from 40% opacity to 0% to signify real-time data streaming.

### High-Contrast Progress Bars (Capacity)
For instant glanceability regarding room or event capacity:
- **Healthy (<80%):** Fill with `secondary` (#096969).
- **Warning (>80%):** Fill with a custom Amber/Warning token.
- **Over Capacity:** Fill with `error` (#ba1a1a).
- **Track:** Use `surface-container-highest` (#e1e3e4) for the unfilled portion of the bar to ensure high contrast against the card background.

### Toggle Switches & Tab Bars
- **Toggle:** Uses `primary` for the 'on' state and `surface-container-highest` for the 'off' track. The thumb must be `surface-container-lowest` for maximum physical pop.
- **Tab Bar:** Fixed to the bottom. Uses a glassmorphic background with a `tertiary_fixed` (#93f2f2) indicator for the active state.

---

## 6. Do's and Don'ts

### Do
- **DO** use the `spacing-5` (1.25rem) as the standard horizontal gutter for all mobile screens to ensure the content doesn't feel "cramped" against the device edges.
- **DO** use `headline-sm` for important metrics within cards.
- **DO** prioritize high-contrast text ratios (min 4.5:1) for all labels, especially when used outdoors.

### Don't
- **DON'T** use 1px dividers to separate list items. Use background tonal shifts or `spacing-2` gaps.
- **DON'T** use the `error` color for anything other than critical capacity or system failures.
- **DON'T** use rounded corners larger than `xl` (0.75rem) for functional containers; keep the "Academic" feel sharp and intentional.