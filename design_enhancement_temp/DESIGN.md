---
name: Luma Alpha Kinetic
colors:
  surface: '#f8f9fa'
  surface-dim: '#d9dadb'
  surface-bright: '#f8f9fa'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f4f5'
  surface-container: '#edeeef'
  surface-container-high: '#e7e8e9'
  surface-container-highest: '#e1e3e4'
  on-surface: '#191c1d'
  on-surface-variant: '#44474c'
  inverse-surface: '#2e3132'
  inverse-on-surface: '#f0f1f2'
  outline: '#74777d'
  outline-variant: '#c4c6cd'
  surface-tint: '#4f6073'
  primary: '#041627'
  on-primary: '#ffffff'
  primary-container: '#1a2b3c'
  on-primary-container: '#8192a7'
  inverse-primary: '#b7c8de'
  secondary: '#006a6a'
  on-secondary: '#ffffff'
  secondary-container: '#90efef'
  on-secondary-container: '#006e6e'
  tertiary: '#00191a'
  on-tertiary: '#ffffff'
  tertiary-container: '#002f31'
  on-tertiary-container: '#00a1a7'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d2e4fb'
  primary-fixed-dim: '#b7c8de'
  on-primary-fixed: '#0b1d2d'
  on-primary-fixed-variant: '#38485a'
  secondary-fixed: '#93f2f2'
  secondary-fixed-dim: '#76d6d5'
  on-secondary-fixed: '#002020'
  on-secondary-fixed-variant: '#004f4f'
  tertiary-fixed: '#63f7ff'
  tertiary-fixed-dim: '#00dce5'
  on-tertiary-fixed: '#002021'
  on-tertiary-fixed-variant: '#004f53'
  background: '#f8f9fa'
  on-background: '#191c1d'
  surface-variant: '#e1e3e4'
typography:
  display-lg:
    fontFamily: Source Serif 4
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Source Serif 4
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
  headline-md-mobile:
    fontFamily: Source Serif 4
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
  terminal-header:
    fontFamily: JetBrains Mono
    fontSize: 18px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: 0.05em
  body-main:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: '1.6'
  data-tabular:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: '1.0'
  label-caps:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '700'
    lineHeight: '1'
    letterSpacing: 0.1em
spacing:
  unit: 4px
  gutter: 16px
  margin-safe: 32px
  container-max: 1440px
---

## Brand & Style
The design system facilitates a "High-Signal" environment for financial intelligence, merging the gravitas of traditional institutional banking with the velocity of modern algorithmic trading. It operates on a dual-pathway aesthetic: one side is a refined, editorial-grade light mode for deep analysis, and the other is a high-performance, dark-mode terminal for real-time execution.

The style is defined by **Precision-Industrialism**. It rejects soft metaphors in favor of structural integrity. This is achieved through:
- **Zero-Radius Geometry:** Every element is sharp-edged, reflecting mathematical certainty.
- **Micro-Borders:** A 1px structural grid system that defines hierarchy without relying on shadows.
- **High-Information Density:** Maximized screen real estate with minimized visual noise to ensure data remains the primary focus.
- **Dual-State Logic:** The UI transitions between "Library Mode" (Light) for research and "Command Mode" (Dark) for active monitoring.

## Colors
The palette is engineered for visual endurance and semantic clarity.

### Luma Alpha (Light Mode)
- **Base:** #F8F9FA (Bone) provides a low-strain, high-end paper feel.
- **Ink:** #080808 (Deep Black) for maximum legibility of text and symbols.
- **Accents:** #1A2B3C (Royal Navy) denotes institutional stability; #008080 (Teal Precision) is used for positive delta and primary actions.

### Kinetic Neural (Dark Mode)
- **Base:** #080808 (Total Charcoal) for maximum contrast against data points.
- **Neural Accents:** #00F5FF (Neural Cyan) and #BF00FF (Vibrant Orchid) are reserved strictly for data visualizations, trend lines, and predictive indicators.
- **Borders:** Subtle #1A1A1A defines the grid containers in dark mode.

## Typography
The typographic hierarchy bridges the gap between a high-end financial journal and a developer terminal.

- **Headlines (Source Serif 4):** Used for narrative analysis, section headers, and "Editorial" views. It establishes authority.
- **UI & Interface (Inter):** The workhorse for navigation, descriptions, and labels. High x-height for clarity at small sizes.
- **Data & Terminal (JetBrains Mono):** Reserved for ticker symbols, numerical values, and code snippets. Monospacing ensures that columns of numbers align perfectly for rapid visual scanning.
- **Styling:** In the Kinetic Neural mode, switch secondary headers to JetBrains Mono to emphasize the technical nature of the platform.

## Layout & Spacing
The layout follows a **Rigid Modular Grid**. 

- **The 4px Baseline:** All spacing, padding, and margins must be multiples of 4px to maintain mathematical rhythm.
- **The 12-Column Grid:** Use a standard 12-column layout for desktop with 16px gutters. Elements should align strictly to the grid edges.
- **Data Densification:** In "Command Mode," reduce gutters to 8px and margins to 16px to maximize data visualization surface area.
- **Responsive Behavior:** On mobile, the grid collapses to 4 columns. Narrative text (Serif) increases in leading for better readability, while data tables switch to a horizontal scroll or condensed "Card-List" hybrid.

## Elevation & Depth
This system eschews traditional depth markers like shadows in favor of **Planar Layering**.

- **1px Borders:** Hierarchy is defined by #E2E8F0 (Light) or #1A1A1A (Dark) borders. 
- **Z-Axis:** Instead of shadows, use "Surface Lifting" via color. A "hovered" card changes its background color slightly (e.g., from #F8F9FA to #FFFFFF) rather than casting a shadow.
- **Glassmorphism (Kinetic Only):** Use very subtle 10% opacity blurs (Backdrop-filter: blur(12px)) only for persistent overlays like floating command bars or modal backgrounds, maintaining the "Neural" futuristic aesthetic.
- **Inset Borders:** For active input states or selected data cells, use a 2px inset border in the primary accent color.

## Shapes
**Sharpness is the core differentiator.**

- **Corner Radius:** All components—buttons, inputs, cards, and modals—must have a `0px` border-radius.
- **Strict Rectangles:** Circular elements are strictly forbidden unless used for status indicators (pills) or user avatars.
- **Directional UI:** Use 45-degree angled cuts only for specific "Alpha" callouts or decorative accents in the Kinetic mode to suggest forward momentum.

## Components

- **Buttons:** Sharp 1px borders. Primary buttons use solid #1A2B3C with white text. Secondary buttons use ghost styling (border only). On hover, fill shifts to the accent color instantly (no transition timing) to feel "responsive."
- **Data Tables:** The heart of the system. Use JetBrains Mono for all numeric values. Headers are uppercase Inter at 11px. Zebra striping is prohibited; use 1px horizontal dividers only.
- **Input Fields:** Bottom-border only for a "form" feel in Luma Alpha; full 1px box for Kinetic Neural. No focus rings; use a color shift of the border to #00F5FF.
- **Chips/Indicators:** Rectangular blocks. Positive change is Teal Precision with white text; negative is a high-chroma Red (#D32F2F).
- **Cards:** No shadows. Defined by a 1px #E2E8F0 border. In Kinetic mode, cards may feature a "Neural Glow" — a 1px border using a subtle gradient.
- **Interactive Charts:** Lines should be 1.5px thick. Area charts should use a sharp step-curve rather than smooth Bezier interpolation to emphasize precision over aesthetics.