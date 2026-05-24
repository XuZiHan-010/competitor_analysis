# Design tokens — "Research Intelligence Brief"

> This document explains the design vocabulary used in `apps/web/src/app/globals.css`.
> When you add a new color or font, update both files together.

## Aesthetic direction

Editorial / research-publication. Think *Bloomberg Terminal* meets *The Economist* meets *Linear*. Warm-paper light theme, deep-ink dark theme. Distinctive variable serif (Fraunces) for headlines, geometric sans (Geist) for body, with proper CJK fallbacks (Noto Serif / Sans SC, PingFang SC, Microsoft YaHei).

**Why**: competitor analysis = research / intelligence work. Editorial gravitas separates this from the typical SaaS aesthetic and reads as "professional, takes itself seriously" to both technical judges and traditional-enterprise users like Henkel strategy team.

---

## Color tokens

All colors are defined as `oklch()` so they degrade gracefully across displays and let us reason about lightness independently of hue.

### Semantic (used by shadcn components — don't bypass)

| Token | Light | Dark | Use |
|---|---|---|---|
| `--background` | warm cream `oklch(0.975 0.008 85)` | deep ink `oklch(0.16 0.012 245)` | page background |
| `--foreground` | deep ink | warm cream | body text |
| `--card` | nearly-white cream | slightly lifted ink | card surfaces (a touch above bg) |
| `--popover` | brightest cream | mid ink | popovers, dropdowns, dialog |
| `--primary` | deep teal-blue `oklch(0.38 0.065 220)` | bright teal `oklch(0.72 0.11 210)` | brand actions, links, focus rings |
| `--primary-foreground` | bg color | bg color | text on primary surfaces |
| `--secondary` / `--muted` / `--accent` | warm cream-gray | mid ink | subdued surfaces; semantically synonymous in this system |
| `--muted-foreground` | warm slate | warm gray | secondary text, captions |
| `--destructive` | editorial deep red `oklch(0.55 0.18 27)` | bright red `oklch(0.65 0.19 25)` | delete, error, blocker |
| `--border` / `--input` | soft warm tan | mid ink | dividers, input borders |
| `--ring` | primary @ 45% | primary @ 50% | focus halo |
| `--radius` | `0.5rem` | same | base radius; sm/md/lg/xl scale from it |

### Editorial extras (custom, not from shadcn defaults)

| Token | Light | Dark | Use |
|---|---|---|---|
| `--paper` | brightest cream `oklch(0.98 0.006 85)` | inverted to warm cream | callouts, "lifted paper" surfaces |
| `--ink` | alias of `--foreground` light | alias of `--background` dark | semantic alias when you mean "ink as a brand color" not "text" |
| `--accent-warm` | ochre `oklch(0.72 0.13 65)` | brighter ochre `oklch(0.78 0.14 70)` | extension-layer markers, highlights, "marked-up paper" feel |

### Chart palette (5 colors, both themes)

Used for any data viz. Hierarchy preserves: primary → ochre → sage → red → plum.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--chart-1` | primary teal | bright teal | first / dominant series |
| `--chart-2` | ochre | bright ochre | second series, contrast pair |
| `--chart-3` | sage green | brighter sage | third series; nature/health connotation |
| `--chart-4` | editorial red | bright red | warnings, decline |
| `--chart-5` | muted plum | brighter plum | fifth series, rare highlight |

---

## Typography

### Font stacks

| Variable | Stack | Use |
|---|---|---|
| `--font-sans` | Geist Sans → Noto Sans SC → PingFang SC → Microsoft YaHei → system | body, buttons, inputs |
| `--font-mono` | Geist Mono → Cascadia Code → Consolas → monospace | IDs, timestamps, source codes, "Brief / N.001" markers |
| `--font-display` | Fraunces (variable serif) → Noto Serif SC → PingFang SC → Source Han Serif SC → Georgia | h1-h3 headlines, brand wordmark, dialog titles |
| `--font-heading` | same as `--font-display` | alias for places where "heading" is more semantic |

### Why Fraunces

Variable serif with `opsz` (optical size), `SOFT`, and `WONK` axes. At display sizes (`opsz` 144) it has presence and editorial gravitas. Mixing `SOFT` 100 on a single word creates a subtle "highlighted phrase" effect we use for the primary keyword in each headline (see `/tasks/new` "竞品情报" italicized in primary).

### Tabular numerals

Use the `.tabular` utility class anywhere numbers need to align in columns: `00 / 01 / 02` section ordinals, `45 字` counters, timestamps, token counts. Driven by `font-variant-numeric: tabular-nums`.

### CJK leading

Default `line-height` works for Latin. For dense CJK blocks (long paragraphs in reports), bump to `leading-relaxed` (1.625) or `leading-loose` (2). The body element already applies `font-feature-settings: kern, liga, calt, ss01` which improves both Latin and CJK rendering.

---

## Motion tokens

Defined as CSS variables under `@theme inline` so Tailwind generates `animate-{name}` utilities.

| Token | Animation | Use |
|---|---|---|
| `--animate-fade-in` | 0.4s opacity | mounting chips, toast appears |
| `--animate-slide-up` | 0.5s, eased | section reveals on page load, staggered with delays |
| `--animate-thinking-pulse` | 2s infinite | "AI is thinking" indicator |

### Staggered reveals

Pages use `animate-[slide-up_0.6s_cubic-bezier(0.16,1,0.3,1)_X_both]` where `X` is `0.05s`, `0.15s`, `0.25s` etc. to create a cascade. The cubic-bezier is "Smooth out" — fast at start, settles gently. Always include `_both` so the start state isn't visible.

---

## Utility classes (defined in globals.css)

- `.bg-paper-grain` — subtle radial-dot noise on warm cream, applied to body. Avoid using on small surfaces (looks like compression artifacts).
- `.rule-fade` — horizontal divider that fades to transparent at both ends. Use between major sections, not within forms.
- `.drop-cap` — first-letter styling for the first paragraph of report sections. Use sparingly (one per page max).
- `.tabular` — tabular numerals for alignment.
- `.display` — applies the display font + features (use when you can't use `<h1>-<h3>`).

---

## When to break the system

The system favors restraint. If you find yourself wanting to add a new color, ask:
1. Can `--accent-warm` (ochre) do what I need?
2. Can `--chart-N` cover it?
3. Is this a one-off where a hardcoded `oklch()` value inline is honest?

Don't introduce a new semantic token unless 3+ places will use it. The cost of fragmenting the palette is higher than the cost of one-off colors.

---

## What this system explicitly avoids

- **Inter / Roboto / system-ui as the brand font** — too generic, dilutes editorial identity.
- **Purple-to-blue gradients** — the AI default; instantly reads as "AI slop".
- **Floating cards with heavy shadows** — competing aesthetic; we use 1px tan shadows and editorial rules instead.
- **Emoji as decoration** — replaced with lucide-react icons (Lock, Pencil, GripVertical, etc.) wrapped in tinted square badges.
- **More than 1 accent color competing for primary attention** — primary teal + ochre accent is the limit; everything else lives in chart palette or muted scale.
