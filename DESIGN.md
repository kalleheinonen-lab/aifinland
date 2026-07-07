# Design Tokens

This document describes the design tokens consumed by the AI Finland frontend application.

## Source

All design tokens originate from the **organization design standards**. They define the visual language for colors, spacing, border radii, and typography used across all organization products.

## Token Categories

### Colors

| Token | Value | Usage |
|-------|-------|-------|
| `primary` | `#dd5bec` | Primary brand color, CTAs, active states |
| `secondary` | `#000000` | Secondary actions, text |
| `tertiary` | `#4e36a1` | Accent, supporting elements |
| `surface` | `#fdfcfd` | Default background |
| `surface-dim` | `#f7f5f7` | Dimmed/muted backgrounds |
| `error` | `#DC2626` | Error states, destructive actions |
| `success` | `#059669` | Success states, confirmations |
| `warning` | `#D97706` | Warning states, caution indicators |

### Border Radius

| Token | Value |
|-------|-------|
| `sm` | `6px` |
| `md` | `10px` |
| `lg` | `14px` |
| `xl` | `20px` |
| `2xl` | `24px` |
| `full` | `9999px` |

### Spacing

| Token | Value |
|-------|-------|
| `xs` | `4px` |
| `sm` | `8px` |
| `md` | `16px` |
| `lg` | `24px` |
| `xl` | `32px` |
| `2xl` | `48px` |
| `3xl` | `64px` |

### Typography

| Token | Value |
|-------|-------|
| `font-sans` | `Inter, sans-serif` |

## Integration Approach

Design tokens are integrated into the frontend via two mechanisms:

### 1. Tailwind Theme Extension (`tailwind.config.ts`)

The Tailwind CSS configuration extends the default theme with organization tokens. This allows using tokens as Tailwind utility classes:

```html
<div class="bg-primary text-surface rounded-md p-md">
```

### 2. CSS Custom Properties (`src/styles/design-tokens.css`)

All tokens are also exposed as CSS custom properties for use in contexts where Tailwind utilities are insufficient:

```css
.custom-element {
  background: var(--color-primary);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
}
```

## Updating Tokens

When the organization design standards are updated:

1. Update `tailwind.config.ts` with new token values
2. Update `src/styles/design-tokens.css` with corresponding CSS custom properties
3. Update this document to reflect changes
