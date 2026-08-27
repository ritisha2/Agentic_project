---
name: Blueprint Tactical
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
  on-surface-variant: '#454936'
  inverse-surface: '#2e3132'
  inverse-on-surface: '#f0f1f2'
  outline: '#757964'
  outline-variant: '#c5c9b0'
  surface-tint: '#536600'
  primary: '#536600'
  on-primary: '#ffffff'
  primary-container: '#d4f658'
  on-primary-container: '#5b7000'
  inverse-primary: '#b3d338'
  secondary: '#0056c6'
  on-secondary: '#ffffff'
  secondary-container: '#006df8'
  on-secondary-container: '#fefcff'
  tertiary: '#ad1e7a'
  on-tertiary: '#ffffff'
  tertiary-container: '#ffe0ec'
  on-tertiary-container: '#ba2a84'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#cff053'
  primary-fixed-dim: '#b3d338'
  on-primary-fixed: '#171e00'
  on-primary-fixed-variant: '#3e4c00'
  secondary-fixed: '#d9e2ff'
  secondary-fixed-dim: '#b0c6ff'
  on-secondary-fixed: '#001945'
  on-secondary-fixed-variant: '#00429c'
  tertiary-fixed: '#ffd8e8'
  tertiary-fixed-dim: '#ffafd5'
  on-tertiary-fixed: '#3d0027'
  on-tertiary-fixed-variant: '#8a005f'
  background: '#f8f9fa'
  on-background: '#191c1d'
  surface-variant: '#e1e3e4'
  pitch-charcoal: '#0F1012'
  slate-gray: '#16181C'
  dot-grid: '#E2E4E6'
  muted-body: '#666666'
  pure-black: '#000000'
  pure-white: '#FFFFFF'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 64px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.04em
  headline-lg:
    fontFamily: Inter
    fontSize: 40px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.03em
  headline-md:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.3'
    letterSpacing: -0.02em
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: -0.01em
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: '0'
  label-mono:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: 0.1em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
rounded:
  sm: 0.5rem
  DEFAULT: 1rem
  md: 1.5rem
  lg: 2rem
  xl: 3rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 24px
  margin-safe: 32px
  section-gap: 120px
  container-max: 1280px
---

## Brand & Style

This design system is built on a "Schematic Minimalist" philosophy, evoking the precision of architectural blueprints combined with a high-tech, AI-driven edge. It targets enterprise-grade technical decision-makers who value efficiency, transparency, and modularity.

The aesthetic utilizes extreme whitespace, ultra-thin hairlines, and high-frequency utility patterns (dotted grids) to create a sense of infinite, structured space. By mixing a stark neutral foundation with high-visibility neon accents, the UI signals a "utility-first" tool that is both professional and cutting-edge. The emotional response is one of surgical precision and systematic clarity.

## Colors

The palette is anchored by a high-contrast foundation. In light mode, surfaces rely on `pure-white` and `neutral-off-white`, while dark mode utilizes `pitch-charcoal` and `slate-gray`. 

**Functional Application:**
- **Primary (Neon Lime):** Reserved exclusively for critical action triggers and primary CTAs.
- **Secondary (Cobalt Blue):** Used for informational banners and structural highlights.
- **Tertiary (Vibrant Pink):** Applied to micro-interactions, specific data highlights, or "active" status indicators.
- **Grid Pattern:** A subtle light-gray dotted grid (#E2E4E6) should be applied to the main background of primary sections to reinforce the schematic aesthetic.

## Typography

The typography system uses a dual-threat approach: **Inter** for high-impact geometric headlines and readable body text, and **JetBrains Mono** for technical utility.

Tracking is intentionally tight on headlines to create a "locked-in" professional look. Labels must always be in uppercase monospace to denote technical categories or metadata. Use `-0.04em` letter spacing for large display type to maintain the dense, modern aesthetic found in high-end tech brands.

## Layout & Spacing

This design system uses a **Fixed Grid** model for desktop to ensure schematic alignment. The layout is based on a 12-column grid with 24px gutters.

- **Vertical Rhythm:** Large section gaps (120px+) are encouraged to emphasize the "infinite canvas" feel.
- **Alignment:** Elements should align strictly to the dotted grid background where possible.
- **Mobile Adaptivity:** On mobile, margins reduce to 16px and the grid collapses to a single column, but the "blueprint" border lines remain to maintain structural integrity.

## Elevation & Depth

Depth is conveyed through **Structural Tiering** rather than shadows. 
- **Hairline Borders:** Surfaces are separated by ultra-thin 1px borders (#E2E4E6 in light, #2A2D32 in dark).
- **Tonal Layering:** Use slight shifts between #FFFFFF and #F8F9FA to indicate hierarchy. 
- **Zero Shadows:** Avoid ambient shadows. If depth is required, use a solid 1px offset "hard shadow" in a primary accent color for a brutalist effect, but prioritize flat outlines.
- **Blueprint Cards:** Cards should look like technical drawings—sharp corners or very minimal radius, 1px outlines, and inner labels in monospace.

## Shapes

The shape language is a "Binary Contrast." 
- **Containers & Cards:** Use sharp or very slightly softened corners (0px to 4px) to maintain the schematic, architectural feel.
- **Interactive Elements:** Buttons and Chips use a **full pill (rounded-full)** shape. This contrast ensures that clickable elements are immediately distinguishable from structural layouts.

## Components

### Buttons
- **Primary:** Full pill shape, Neon Lime (#D4F658) background, Pure Black text. Must include a directional arrow icon (e.g., `arrow-up-right`).
- **Secondary:** Transparent background, 1px Black outline, Pure Black text, pill shape.
- **Icon Style:** Use "thin" or "light" weight icons to match the 1px border aesthetic.

### Cards
- **Schematic Card:** 1px border, off-white background, no shadow. Content should be organized with clear vertical and horizontal dividers that look like grid lines.

### Inputs & Form Fields
- Underline-only or 1px bordered boxes. Use monospace labels sitting just above the input area. Focus state uses a 1px solid Cobalt Blue border.

### Chips / Category Labels
- Small pill-shaped containers with JetBrains Mono text. Backgrounds should be very light tints of the accent colors (e.g., Cobalt Blue at 10% opacity).

### List Items
- Separated by 1px horizontal hairlines. Hover states should trigger a subtle color shift to the off-white neutral or a light lime tint on the leading edge.