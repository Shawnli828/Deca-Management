# Deca Growth Design System

## Direction

Deca Growth uses a Notion-inspired operational workspace style: warm minimal surfaces, dense but readable data, restrained controls, and chart colors that remain distinct for analysis. The UI should feel like a daily workbench, not a landing page.

## Principles

- Data first: tables, KPIs, and charts carry the hierarchy.
- Warm minimalism: use white and warm off-white surfaces with subtle borders.
- Low decoration: no large hero treatments, no decorative gradients, no bento filler.
- Stable density: keep repeated controls compact and predictable.
- Chart clarity: preserve distinct series colors; use neutral reference lines and grid lines.
- Sober geometry: buttons and inputs use 8px radius; cards and panels use 12px radius; pills only for status badges and compact tabs.

## Tokens

- Page: `#faf9f7`
- Canvas: `#ffffff`
- Surface: `#f7f6f3`
- Surface soft: `#fbfaf8`
- Border: `#e6e1d9`
- Border strong: `#d8d1c7`
- Text: `#1f1f1d`
- Secondary text: `#6f6a62`
- Muted text: `#9a958c`
- Primary action: `#1f1f1d`
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
- Inputs/selects: white surface, warm border, 8px radius, 44px height.
- Panels: white canvas, 12px radius, `1px` warm border, minimal shadow.
- KPI cards: warm off-white fill, 12px radius, no heavy shadow.
- Tables: white rows, warm hairlines, muted headers.
- Status messages: soft semantic backgrounds, border + concise text.
- Chart legends: clickable text or compact controls with visible color strokes.
- Chart grid: neutral warm gray; reference lines dashed and neutral.

## Feishu Report Page

- The top control area is a compact workspace toolbar, not a hero.
- Preview area is the primary content, split into overview and product analysis.
- Overview and product panels share the same panel anatomy.
- Chart series colors must stay distinct; do not collapse them into monochrome.
- The 1K RF Avg goal line is neutral and should not compete with country series colors.
