# Technical Audit: UI/UX Migration Roadmap (Bootstrap 2.3.2 to 5.3)

# Technical Audit: Bootstrap 5 Migration Roadmap
**Lead Contributor:** @Janvi-kapoor  
**Related Issues:** #3810 (Parent), #3809 (Bootstrap 5), #3808 (Bootswatch)

---

## 1. Executive Summary
This document provides a comprehensive audit of the legacy styling architecture within the ESP-Website. The primary objective is to identify and map hardcoded CSS/LESS values to **Bootstrap 5 Semantic Variables**. This decoupling is essential to ensure full compatibility with the proposed **Bootswatch 5 integration**, allowing for dynamic theme switching without UI regressions.

## 2. Technical Scope
The audit focuses on the following directories (identified via `ThemeController` mapping):
- `esp/public/media/less/`
- `esp/public/media/default_styles/`
- `esp/esp/templates/` (Inline styles and legacy component structures)

---

## 3. Structural Mapping: Legacy vs. Modern Variable System

### 🎨 3.1 Color Palette & Semantic Theming
Legacy hardcoded colors in `.less` files must be mapped to the BS5 Utility API to support light/dark mode and Bootswatch skins.

| Component Area | Legacy Property | Hardcoded Value | BS5 Semantic Variable | Priority |
| :--- | :--- | :--- | :--- | :--- |
| Global Branding | `@blue` | `#049cdb` | `var(--bs-primary)` | High |
| Admin Toolbar | `background-color` | `#333` | `var(--bs-dark)` | Medium |
| Login Notifications | `color` (Text) | `#BCCAF5` | `var(--bs-primary-bg-subtle)`| Medium |
| Borders/Dividers | `@gray-lighter`| `#eee` | `var(--bs-border-color)` | Low |

### 📐 3.2 Typography & Spacing (A11y Compliance)
We are moving from fixed-pixel (`px`) definitions to relative units (`rem`) and CSS variables to ensure responsiveness and accessibility.

| Element | Current Style | Target Standard | Rationale |
| :--- | :--- | :--- | :--- |
| Global Font Size | `14px` | `var(--bs-body-font-size)` | Dynamic scaling |
| Heading Tags | Fixed `@baseLineHeight`| `var(--bs-headings-line-height)`| Vertical rhythm |
| Margin/Padding | `10px`, `15px` | Spacing Utilities (`p-3`, `m-2`) | Consistent guttering |

---

## 4. Component Refactoring Audit

### 🛠 4.1 Login Box (`loginbox_content.html`)
- **Current State:** Uses legacy `table`-based layout for forms with `glyphicon` font icons.
- **Proposed Change:** - Wrap in `.container` and `.card` components.
  - Migrate `glyphicon-log-in` to **Bootstrap Icons (SVG)**: `bi-box-arrow-in-right`.
  - Replace `btn-inverse` with `btn-dark` or `btn-outline-primary`.

### 🛠 4.2 Admin Bar
- **Current State:** Absolute positioning with hardcoded Z-index and background.
- **Proposed Change:** Integrate with BS5 `navbar` utilities for better mobile stacking.

---

## 5. Implementation Roadmap (Phase 1)
1. [ ] **Audit Completion:** Finalize mapping for all 47 LESS files in the media directory.
2. [ ] **Variables SCSS:** Create a bridge file that translates `@legacy-vars` to `$bs5-vars`.
3. [ ] **Component POC:** Refactor the Login Module as a proof-of-concept for the migration.

---
**Note:** This audit is a prerequisite for the Sass/SCSS compiler migration (#4719).