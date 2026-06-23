# Deca Growth Design System

## Direction

Deca Growth uses a Notion-inspired operational workspace style: clean white surfaces, dense but readable data, restrained controls, and chart colors that remain distinct for analysis. The UI should feel like a daily workbench, not a landing page.

## Principles

- Data first: tables, KPIs, and charts carry the hierarchy.
- Clean minimalism: use pure white and neutral light-gray surfaces with subtle borders.
- Low decoration: no large hero treatments, no decorative gradients, no bento filler.
- Stable density: keep repeated controls compact and predictable.
- Chart clarity: preserve distinct series colors; use neutral reference lines and grid lines.
- Sober geometry: buttons and inputs use 8px radius; cards and panels use 12px radius; pills only for status badges and compact tabs.

## Tokens

- Page: `#ffffff`
- Canvas: `#ffffff`
- Surface: `#f8f9fb`
- Surface soft: `#f9fafb`
- Border: `#e5e7eb`
- Border strong: `#d1d5db`
- Text: `#111827`
- Secondary text: `#64748b`
- Muted text: `#94a3b8`
- Primary action: `#111827`
- Primary action text: `#ffffff`
- Blue metric / View: `#2f80ed`
- Orange metric / Download: `#df6b3b`
- Green success: `#0f766e`
- Amber warning: `#9a5b04`
- Red error: `#c9352b`

## Typography

- Font stack: `Inter`, `-apple-system`, `BlinkMacSystemFont`, `"Segoe UI"`, `"PingFang SC"`, sans-serif.
- Page titles: 28-34px, 650 weight.
- Panel titles: 15-18px, 650 weight.
- KPI values: 24-34px, 650 weight.
- Table body: 12-14px, 450-550 weight.
- Labels: 11-12px, 600 weight, muted color.
- Letter spacing stays 0.

## Components

- Buttons: 8px radius, 44-46px height, subtle border for secondary actions.
- Primary buttons: near-black background; use blue only for data, links, or existing system emphasis.
- Inputs/selects: white surface, neutral border, 8px radius, 44px height.
- Panels: white canvas, 12px radius, `1px` neutral border, minimal shadow.
- KPI cards: neutral light-gray fill, 12px radius, no heavy shadow.
- Tables: white rows, neutral hairlines, muted headers.
- Status messages: soft semantic backgrounds, border + concise text.
- Chart legends: clickable text or compact controls with visible color strokes.
- Chart grid: neutral gray; reference lines dashed and neutral.

## Feishu Report Page

- The top control area is a compact workspace toolbar, not a hero.
- Preview area is the primary content, split into overview and product analysis.
- Overview and product panels share the same panel anatomy.
- Chart series colors must stay distinct; do not collapse them into monochrome.
- The 1K RF Avg goal line is neutral and should not compete with country series colors.

## App-Wide Pages

- Other tools reuse the same pure-white workspace shell as Feishu Report.
- Page heads are compact bordered toolbars, not decorative hero blocks.
- Product, country, API, publish-check, cloud-phone, slideshow, and report pages share the same button, input, table, KPI, and panel treatments.
- Keep chart and semantic colors only where they encode data or state.
- Avoid adding new page-specific gradients or heavy shadows; add page-specific visual hierarchy through spacing, labels, table structure, and selected states.
