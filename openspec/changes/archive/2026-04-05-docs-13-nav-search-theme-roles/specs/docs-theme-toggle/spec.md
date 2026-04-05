## ADDED Requirements

### Requirement: Dual CSS theme definitions
The stylesheet SHALL define CSS custom properties for both light and dark themes using `[data-theme="light"]` and `[data-theme="dark"]` selectors on the `<html>` element. A `@media (prefers-color-scheme)` fallback SHALL apply when no explicit `data-theme` attribute is set.

#### Scenario: Dark theme variables
- **WHEN** the `data-theme` attribute is set to `dark`
- **THEN** the site SHALL use a dark navy background (`#0a192f`), light text (`#ccd6f6`), and a subdued cyan accent (`#57e6c4`)

#### Scenario: Light theme variables
- **WHEN** the `data-theme` attribute is set to `light`
- **THEN** the site SHALL use a white/off-white background, dark text, and a SpecFact teal accent (`#0d9488`)

#### Scenario: System preference fallback
- **WHEN** no `data-theme` attribute is set on `<html>`
- **THEN** the site SHALL use `@media (prefers-color-scheme: dark)` and `@media (prefers-color-scheme: light)` to match the user's OS preference

### Requirement: Theme toggle button
A theme toggle button SHALL be rendered in the site header via `docs/_includes/theme-toggle.html`. The button SHALL display a sun icon in dark mode and a moon icon in light mode.

#### Scenario: Toggle from dark to light
- **WHEN** the user clicks the theme toggle button while in dark mode
- **THEN** the site SHALL switch to light mode immediately and store `"light"` in `localStorage` under the key `specfact-theme`

#### Scenario: Toggle from light to dark
- **WHEN** the user clicks the theme toggle button while in light mode
- **THEN** the site SHALL switch to dark mode immediately and store `"dark"` in `localStorage`

### Requirement: Theme persistence prevents FOUC
A `theme.js` script SHALL be loaded in the `<head>` element (before body renders) to read the stored theme from `localStorage` and set the `data-theme` attribute before any content is painted.

#### Scenario: Returning visitor sees stored theme
- **WHEN** a user who previously selected light mode visits any page
- **THEN** the page SHALL render in light mode without any flash of dark mode

### Requirement: Theme-aware Mermaid diagrams
Mermaid.js SHALL be re-initialized with appropriate `themeVariables` when the theme changes. Dark mode SHALL use the existing dark mermaid theme. Light mode SHALL use mermaid's `default` theme with SpecFact teal accents.

#### Scenario: Mermaid diagrams update on toggle
- **WHEN** the user toggles from dark to light mode
- **THEN** all Mermaid diagrams on the page SHALL re-render with light-mode colors

### Requirement: Theme-aware syntax highlighting
Rouge syntax highlighting token classes SHALL have color overrides for both light and dark themes so that code blocks are readable in both modes.

#### Scenario: Code blocks readable in light mode
- **WHEN** the site is in light mode
- **THEN** code block backgrounds SHALL be light with dark syntax-highlighted text
- **AND** all token classes (keywords, strings, comments, etc.) SHALL have sufficient contrast against the light background
