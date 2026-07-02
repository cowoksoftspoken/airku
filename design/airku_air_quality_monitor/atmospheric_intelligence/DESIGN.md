---
name: Atmospheric Intelligence
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#393939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353534'
  on-surface: '#e5e2e1'
  on-surface-variant: '#bbcabc'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#869488'
  outline-variant: '#3c4a3f'
  surface-tint: '#49e08d'
  primary: '#53e894'
  on-primary: '#00391d'
  primary-container: '#2ccb7b'
  on-primary-container: '#00502b'
  inverse-primary: '#006d3d'
  secondary: '#adc6ff'
  on-secondary: '#002e6a'
  secondary-container: '#0566d9'
  on-secondary-container: '#e6ecff'
  tertiary: '#ffc379'
  on-tertiary: '#472a00'
  tertiary-container: '#f79f0e'
  on-tertiary-container: '#623c00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#6afda7'
  primary-fixed-dim: '#49e08d'
  on-primary-fixed: '#00210f'
  on-primary-fixed-variant: '#00522d'
  secondary-fixed: '#d8e2ff'
  secondary-fixed-dim: '#adc6ff'
  on-secondary-fixed: '#001a42'
  on-secondary-fixed-variant: '#004395'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  display-aqi:
    fontFamily: Plus Jakarta Sans
    fontSize: 72px
    fontWeight: '700'
    lineHeight: 80px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  container-padding: 20px
  stack-gap: 16px
  grid-gutter: 12px
  border-width: 1px
---

## Brand & Style

The design system is engineered for high-performance health monitoring, blending the precision of IoT technology with a human-centric health focus. The visual narrative centers on clarity, trust, and proactive intelligence.

The primary aesthetic is **Corporate Modern with Glassmorphism accents**. It utilizes a deep dark mode foundation to minimize eye strain and emphasize critical air quality data. Glassmorphic layers are used sparingly to create a sense of depth and lightness, suggesting the "transparency" of air. Subtle, flowing gradients represent air currents, while crisp, geometric iconography ensures the interface feels like a professional-grade instrument. 

The emotional response should be one of "Informed Calm"—the user feels in control of their environment through data that is both beautiful and actionable.

## Colors

This design system utilizes a "Status-First" color logic. The background is a true deep charcoal (#121212) to provide maximum contrast for status indicators.

- **Primary (Good):** Emerald Green (#2CCB7B) signals safety and health.
- **Secondary (AI):** Soft Blue (#60A5FA) is reserved strictly for AI insights, recommendations, and smart features.
- **Moderate:** Amber (#F59E0B) for caution.
- **Unhealthy:** Crimson (#EF4444) for immediate attention.
- **Neutral:** A scale of cool grays provides structure without competing with status colors.

Glassmorphism effects use a 5-10% white tint with a 20px background blur to create layered hierarchy on the dark background.

## Typography

The design system uses **Plus Jakarta Sans** for its modern, tech-forward feel and excellent legibility in high-density data views.

The typography scale features a specific `display-aqi` tier for the primary air quality index number, ensuring the most vital information is seen instantly. Headlines use tighter letter spacing and heavier weights to maintain a sophisticated editorial feel. Labels and small metadata should use Medium or SemiBold weights to remain crisp against the dark background. 

For mobile, the largest headlines scale down to prevent awkward line breaks, while the body text remains consistent to ensure accessibility.

## Layout & Spacing

This design system follows an **8px soft grid** system. All margins, padding, and gaps should be multiples of 8 (or 4 for fine-grained components).

The layout utilizes a **fluid grid** with safe margins of 20px on mobile. 
- **Cards** typically span the full width of the container on mobile, or 2-column spans in grid views (e.g., humidity and temperature stats).
- **Vertical Rhythm:** A consistent 16px (stack-gap) is maintained between primary dashboard modules.
- **Safe Areas:** Ensure interactive elements (buttons, navigation icons) have a minimum touch target of 44px.

## Elevation & Depth

Hierarchy is established through **Tonal Layers and Glassmorphism** rather than traditional heavy shadows.

- **Level 0 (Background):** Deep charcoal #121212.
- **Level 1 (Cards):** Surface color #1E1E1E with a subtle 1px inner stroke of white at 10% opacity.
- **Level 2 (Active States/Overlays):** Glassmorphic panels using `backdrop-filter: blur(20px)` and a semi-transparent background.
- **Shadows:** Only used for floating action buttons or high-priority modals. Shadows should be ultra-diffused (30-40px blur) with a color tint derived from the status color (e.g., a faint green glow when AQI is Good).

## Shapes

The design system uses a **Rounded** language to balance the "industrial" feel of IoT data with "human" health accessibility.

- **Standard Cards:** 1rem (16px) corner radius.
- **Buttons & Chips:** Fully pill-shaped (rounded-full) to distinguish interactive elements from static data cards.
- **Input Fields:** 0.5rem (8px) for a more structured, precise feel.
- **Progress Bars:** Fully rounded ends to suggest smooth, continuous data flow.

## Components

### Cards
Cards are the primary container. They should use the Level 1 elevation (Surface color) with a 1px subtle border. High-priority cards (like AI Recommendations) should use a Glassmorphic background with a Soft Blue accent border.

### Navigation Bar
The bottom navigation utilizes a "Frosted" glass effect. Active states are indicated by a status-colored dot or a color shift in the icon to the AI Soft Blue. Icons should be "Linear" style with a 1.5pt stroke weight.

### Status Indicators
AQI levels are shown via high-contrast badges. The text inside status badges should be bold and uppercase for maximum legibility. Use a "Glow" effect (outer shadow with 0.4 opacity) for the current AQI status to make it the focal point of the dashboard.

### Buttons
Primary buttons are pill-shaped with a subtle gradient. Secondary buttons use an "Outline" style with a 1px border. Interactive elements should have a slight "scale-down" animation (0.98x) on press to feel tactile.

### Input Fields
Inputs for sensor IPs or settings should be dark-themed with a 1px border that glows when focused. Labels should be placed above the field in `label-sm` typography.