# Lyceum Logic Analyzer — Design System & Parameter Guide

This document defines the **Design System**, **CSS Tokens**, **UI Component Guidelines**, and **Logical Model Parameters** for the *Lyceum Logic Analyzer* application. It serves as the single source of truth for maintainers, developers, and designers working on either the frontend styles (`style.css`) or the backend parsing models.

---

## 1. Design Philosophy

The Lyceum design combines **antique wisdom** with **modern precision**. It features:
- **Classic Aesthetics**: Serif typography and warm gold tones inspired by ancient classical academies (Aristotle's Lyceum).
- **Modern Precision**: Dark mode backgrounds, glassmorphism, responsive CSS grids, and vibrant, micro-animated accents.

---

## 2. Design Tokens & CSS Custom Properties

These tokens are declared under `:root` in `style.css` and dictate the look and feel across the interface.

### Color Palette

| Token | Value | Visual Purpose |
| :--- | :--- | :--- |
| `--bg-dark` | `#0a0d16` | Deep navy/black background for high-contrast dark mode. |
| `--bg-card` | `rgba(21, 28, 44, 0.75)` | Semi-transparent card background (for glassmorphism). |
| `--bg-card-hover` | `rgba(28, 38, 59, 0.85)` | Slightly brighter hover state for interactive cards. |
| `--border-color` | `rgba(223, 168, 55, 0.15)` | Subtle classical gold border to blend with dark backgrounds. |
| `--border-color-hover` | `rgba(223, 168, 55, 0.35)` | Highlighted gold border on hover. |

### Text Colors

| Token | Value | Visual Purpose |
| :--- | :--- | :--- |
| `--text-primary` | `#f8fafc` | Crisp off-white for body text, headings, and readability. |
| `--text-secondary` | `#94a3b8` | Cool gray for descriptions and secondary metadata. |
| `--text-muted` | `#64748b` | Dark slate gray for helper text, labels, and borders. |

### Brand Accents (Classical Gold)

| Token | Value | Visual Purpose |
| :--- | :--- | :--- |
| `--color-gold` | `#dfa837` | Core gold color representing prestige, knowledge, and accents. |
| `--color-gold-hover` | `#fcd34d` | Bright yellow-gold for active links or hover indicators. |
| `--color-gold-muted` | `rgba(223, 168, 55, 0.3)` | Muted gold fill for badges and borders. |
| `--gold-gradient` | `linear-gradient(...)` | Linear gradient (`#dfa837` to `#b47e1b`) for primary buttons and logos. |

### Logic Status Colors

Used to indicate the formal validity or soundness of syllogisms.

| Token | Hex Value | RGBA Fill / Border |
| :--- | :--- | :--- |
| `--color-success` | `#10b981` (Green) | `rgba(16, 185, 129, 0.1)` / `...0.25` |
| `--color-danger` | `#f43f5e` (Crimson) | `rgba(244, 63, 94, 0.1)` / `...0.25` |
| `--color-warning` | `#f59e0b` (Amber) | `rgba(245, 158, 11, 0.1)` / `...0.25` |

### UI Syllogistic Term Diagram Colors

For color-coding term segments in syllogism propositions and Euler/Venn diagram visuals:

*   **Subject / Minor Term (S)**: `--color-term-s: #3b82f6;` (Vibrant Blue)
*   **Predicate / Major Term (P)**: `--color-term-p: #ec4899;` (Vibrant Pink/Purple)
*   **Middle Term (M)**: `--color-term-m: #eab308;` (Vibrant Yellow/Gold)

### Typography

*   **UI Elements**: `--font-ui: 'Outfit', sans-serif;`
*   **Classical/Decorative Headings**: `--font-classical: 'Playfair Display', serif;`

### Shadows & Blurs

*   **Card Shadow**: `--card-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.7);`
*   **Glass Backdrop Blur**: `--glass-blur: blur(12px);`
*   **Transition Curve**: `--transition-smooth: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);`

---

## 3. UI Component Class Reference

### Ambient Background Glows
Create atmospheric depth using fixed-position blurred orbs behind cards:
```html
<div class="background-decorations">
    <div class="glow-orb orb-1"></div> <!-- Gold top-right orb -->
    <div class="glow-orb orb-2"></div> <!-- Deep blue bottom-left orb -->
</div>
```

### Premium Glassmorphism Card
```html
<div class="card animate-slide-up">
    <div class="card-header">
        <h2><i class="icon-class"></i> Component Title</h2>
        <p>Subtitle or description goes here.</p>
    </div>
    <!-- Card content -->
</div>
```

### Form Elements & Textarea
Input wrappers provide vertical stack flexibility with subtle focus ring glow:
```html
<div class="essay-textarea-wrapper">
    <textarea placeholder="Paste your essay here..."></textarea>
</div>
```

### Buttons

*   **Primary Button** (`.btn-primary`): Gold-gradient filled, suited for main actions (e.g., "Analyze Logic").
*   **Secondary Button** (`.btn-secondary`): Outlined gold button with subtle background hover transition, suited for secondary utilities (e.g., "Load Sample").
*   **Tertiary/Destructive Button** (`.btn-tertiary`): Text button that highlights in crimson on hover (e.g., "Clear Essay").

### Syllogistic Highlight Syntax
Propositions highlight quantifier types and distributed terms with standard HTML:
```html
<div class="prop-row">
    <div class="prop-header">
        <span class="prop-label">Major Premise</span>
        <span class="prop-badge type-code">A</span>
    </div>
    <div class="prop-content">
        <span class="quantifier">All</span>
        <span class="subject">men</span>
        <span class="copula">are</span>
        <span class="predicate">mortal</span>
    </div>
    <div class="distribution-tags">
        <span class="dist-tag" data-dist="true">S: Distributed</span>
        <span class="dist-tag" data-dist="false">P: Undistributed</span>
    </div>
</div>
```

---

## 4. Logical Engine Parameters (Data Contracts)

The backend code defined in `src/text_logic_parser/models.py` maps natural language entities to standard syllogistic codes and distribution profiles.

### Categorical Proposition Types

| Proposition Type Code | Standard Form Pattern | Quantity | Quality | Subject Distributed? | Predicate Distributed? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **A** | All S are P | Universal | Affirmative | **Yes** | No |
| **E** | No S are P | Universal | Negative | **Yes** | **Yes** |
| **I** | Some S are P | Particular | Affirmative | No | No |
| **O** | Some S are not P | Particular | Negative | No | **Yes** |
| **Singular Affirmative** | S is a P | Singular | Affirmative | **Yes** | No |
| **Singular Negative** | S is not a P | Singular | Negative | **Yes** | **Yes** |

### Term Identifiers
When parsing a `Syllogism`, the terms are deduced as follows:
- **Minor Term (S)**: The grammatical subject of the conclusion proposition. (Associated with CSS variable `--color-term-s`).
- **Major Term (P)**: The grammatical predicate of the conclusion proposition. (Associated with CSS variable `--color-term-p`).
- **Middle Term (M)**: The common element appearing in both premises but completely omitted from the conclusion. (Associated with CSS variable `--color-term-m`).

---

## 5. UI Animations & Motion Guidelines

We enforce buttery smooth, non-intrusive CSS transitions for a premium interactive feel:

### Transitions
- Any interactive element (`.card`, `textarea`, `.btn-*`, `.prop-row`, `.fallacy-violation-card`) must use `--transition-smooth` (300ms cubic-bezier).

### Animations
*   **`.animate-fade-in`**: Fade opacity smoothly from `0` to `1`.
*   **`.animate-slide-up`**: Slips the card up from `30px` lower while fading in, providing a clean arrival.
*   **`spin`**: Rotates the loader ring infinitely at `1.2s`.
*   **`pulse`**: Infinite scale pulse (`0.85` to `1.15`) for the center core orb of the loading ring.
