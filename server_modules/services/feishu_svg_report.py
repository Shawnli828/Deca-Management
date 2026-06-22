from __future__ import annotations

from html import escape
from pathlib import Path
import subprocess


WIDTH = 1800
HEIGHT = 1140
BLUE = "#2f7df6"
ORANGE = "#e5673b"
TEXT = "#111827"
MUTED = "#64748b"
LINE = "#e5e7eb"
CARD_BG = "#f8fafc"
CARD_BORDER = "#dbe4f0"
GREEN = "#177f78"
AMBER = "#a46405"


def compact_metric(value):
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    abs_number = abs(number)
    if abs_number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    if abs_number >= 1_000:
        return f"{number / 1_000:.1f}K"
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.1f}"


def compact_axis_metric(value):
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    if abs(number) >= 1_000:
        return f"{number / 1_000:.1f}K"
    if number.is_integer():
        return str(int(number))
    return f"{number:.1f}"


def rate_metric(value):
    if value is None:
        return "-"
    try:
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return "-"


def post_coverage(global_data):
    published = int((global_data or {}).get("rfPublished") or 0)
    expected = int((global_data or {}).get("rfExpected") or 0)
    return f"{published}/{expected}" if expected else str(published)


def svg_text(text):
    return escape(str(text or ""), quote=False)


def text(x, y, value, *, size=24, weight=500, fill=TEXT, anchor="start", extra=""):
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}" text-anchor="{anchor}" {extra}>{svg_text(value)}</text>'
    )


def line(x1, y1, x2, y2, *, stroke=LINE, width=1, dash=""):
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{width}"{dash_attr}/>'


def rounded_rect(x, y, width, height, *, radius=20, fill="#ffffff", stroke=CARD_BORDER, stroke_width=1):
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
    )


def padded_range(values):
    finite = [float(value) for value in values if value is not None]
    if not finite:
        return 0, 1
    min_value = min(finite)
    max_value = max(finite)
    if min_value == max_value:
        pad = max(1, abs(max_value) * 0.1)
        return max(0, min_value - pad), max_value + pad
    pad = (max_value - min_value) * 0.12
    return max(0, min_value - pad), max_value + pad


def smooth_path(points):
    if not points:
        return ""
    if len(points) == 1:
        return f"M{points[0][0]:.1f} {points[0][1]:.1f}"
    path = f"M{points[0][0]:.1f} {points[0][1]:.1f}"
    for index, point in enumerate(points[1:], start=1):
        prev = points[index - 1]
        mid_x = (prev[0] + point[0]) / 2
        path += f" C{mid_x:.1f} {prev[1]:.1f} {mid_x:.1f} {point[1]:.1f} {point[0]:.1f} {point[1]:.1f}"
    return path


def overview_trend(card_data):
    for group in card_data.get("trendGroups") or []:
        if str(group.get("key") or "").lower() == "overview":
            return group.get("trend") or []
        if str(group.get("label") or "") == "总览":
            return group.get("trend") or []
    return card_data.get("trend") or []


def kpi_cards(global_data):
    items = [
        ("总播放", compact_metric(global_data.get("totalPlays")), BLUE),
        ("RF Total View", compact_metric(global_data.get("rfPlays")), TEXT),
        ("Clone Total View", compact_metric(global_data.get("clonePlays")), TEXT),
        ("Onboarding Unique", compact_metric(global_data.get("onboarding")), GREEN),
        ("转化", rate_metric(global_data.get("downloadRate")), AMBER),
        ("Post", post_coverage(global_data), TEXT),
    ]
    output = []
    x0 = 44
    y0 = 144
    gap_x = 18
    gap_y = 18
    card_w = 562
    card_h = 126
    for index, (label, value, color) in enumerate(items):
        col = index % 3
        row = index // 3
        x = x0 + col * (card_w + gap_x)
        y = y0 + row * (card_h + gap_y)
        output.append(rounded_rect(x, y, card_w, card_h, radius=16, fill=CARD_BG))
        output.append(text(x + 24, y + 42, label, size=21, weight=650, fill=MUTED))
        output.append(text(x + 24, y + 95, value, size=42, weight=760, fill=color))
    return "\n".join(output)


def trend_chart(rows):
    rows = [
        {
            "label": row.get("label") or row.get("date") or "",
            "view": int(row.get("view") or 0),
            "download": int(row.get("download") or 0),
        }
        for row in rows or []
    ]
    if not rows:
        return text(900, 650, "暂无趋势数据", size=26, weight=650, fill=MUTED, anchor="middle")

    chart_x = 142
    chart_y = 568
    chart_w = 1460
    chart_h = 470
    pad_left = 0
    pad_right = 0
    plot_x = chart_x
    plot_y = chart_y
    plot_w = chart_w
    plot_h = chart_h
    view_min, view_max = padded_range([row["view"] for row in rows])
    dl_min, dl_max = padded_range([row["download"] for row in rows])

    def x_for(index):
        if len(rows) <= 1:
            return plot_x + plot_w / 2
        return plot_x + (plot_w / (len(rows) - 1)) * index

    def y_for(value, min_value, max_value):
        ratio = (float(value) - min_value) / max(1, max_value - min_value)
        return plot_y + plot_h - ratio * plot_h

    view_points = [(x_for(i), y_for(row["view"], view_min, view_max), row["view"]) for i, row in enumerate(rows)]
    download_points = [(x_for(i), y_for(row["download"], dl_min, dl_max), row["download"]) for i, row in enumerate(rows)]
    output = []

    for index in range(4):
        ratio = index / 3
        y = plot_y + ratio * plot_h
        view_value = view_max - ratio * (view_max - view_min)
        dl_value = dl_max - ratio * (dl_max - dl_min)
        output.append(line(chart_x, y, chart_x + chart_w, y, stroke=LINE, width=1.2))
        output.append(text(chart_x - 16, y + 6, compact_axis_metric(view_value), size=18, weight=550, fill=MUTED, anchor="end"))
        output.append(text(chart_x + chart_w + 58, y + 6, compact_axis_metric(dl_value), size=18, weight=550, fill=MUTED))

    output.append(f'<path d="{smooth_path([(x, y) for x, y, _ in view_points])}" fill="none" stroke="{BLUE}" stroke-width="4" stroke-linecap="round"/>')
    output.append(f'<path d="{smooth_path([(x, y) for x, y, _ in download_points])}" fill="none" stroke="{ORANGE}" stroke-width="4" stroke-linecap="round" stroke-dasharray="14 14"/>')

    for x, y, value in view_points:
        output.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{BLUE}"/>')
        label_y = max(plot_y + 24, y - 16)
        output.append(text(x, label_y, compact_axis_metric(value), size=18, weight=760, fill=BLUE, anchor="middle"))

    for x, y, value in download_points:
        output.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{ORANGE}"/>')
        label_y = min(plot_y + plot_h - 8, y + 28)
        output.append(text(x, label_y, compact_axis_metric(value), size=18, weight=760, fill=ORANGE, anchor="middle"))

    label_indexes = list(range(len(rows))) if len(rows) <= 5 else sorted(set([0, 2, 4, len(rows) - 1]))
    for index in label_indexes:
        x = x_for(index)
        anchor = "middle"
        output.append(text(x, plot_y + plot_h + 52, rows[index]["label"], size=20, weight=500, fill="#334155", anchor=anchor))

    return "\n".join(output)


def overview_svg(card_data):
    global_data = card_data.get("global") or {}
    trend = overview_trend(card_data)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        "<defs>",
        "<filter id=\"shadow\" x=\"-5%\" y=\"-5%\" width=\"110%\" height=\"110%\"><feDropShadow dx=\"0\" dy=\"8\" stdDeviation=\"12\" flood-color=\"#0f172a\" flood-opacity=\"0.05\"/></filter>",
        "</defs>",
        f'<rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" fill="#ffffff"/>',
        f'<g font-family="-apple-system, BlinkMacSystemFont, Helvetica Neue, PingFang SC, Noto Sans CJK SC, Arial, sans-serif">',
        rounded_rect(4, 16, WIDTH - 8, HEIGHT - 32, radius=22, fill="#ffffff", stroke=CARD_BORDER, stroke_width=1.2),
        text(44, 72, "总览 · 甲方产品", size=28, weight=760, fill=TEXT),
        text(44, 110, f"业务日 {card_data.get('bizDate') or '-'} · 内容窗口 {card_data.get('window') or '-'}", size=24, weight=650, fill=MUTED),
        rounded_rect(1558, 46, 210, 38, radius=19, fill="#ffffff", stroke=CARD_BORDER),
        text(1663, 72, "Webhook 总览卡片", size=20, weight=720, fill="#475569", anchor="middle"),
        kpi_cards(global_data),
        line(34, 444, WIDTH - 34, 444, stroke=LINE, width=1),
        text(44, 500, "View / Download 趋势", size=28, weight=760, fill=TEXT),
        text(44, 550, "全部汇总", size=22, weight=760, fill=TEXT),
        line(1498, 492, 1528, 492, stroke=BLUE, width=5),
        text(1540, 499, "View", size=22, weight=700, fill=MUTED),
        line(1624, 492, 1654, 492, stroke=ORANGE, width=5),
        text(1666, 499, "Download", size=22, weight=700, fill=MUTED),
        trend_chart(trend),
        "</g>",
        "</svg>",
    ]
    return "\n".join(parts)


def svg_to_png_bytes(svg):
    if not svg:
        raise RuntimeError("SVG content is empty.")
    root = Path(__file__).resolve().parents[2]
    script = """
const sharp = require('sharp');
const chunks = [];
process.stdin.on('data', chunk => chunks.push(chunk));
process.stdin.on('end', async () => {
  try {
    const input = Buffer.concat(chunks);
    const output = await sharp(input, { density: 144 }).png().toBuffer();
    process.stdout.write(output);
  } catch (error) {
    console.error(error && error.message ? error.message : error);
    process.exit(1);
  }
});
"""
    try:
        result = subprocess.run(
            ["node", "-e", script],
            input=svg.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=root,
            timeout=30,
            check=False,
        )
    except FileNotFoundError as error:
        raise RuntimeError("Node.js is required to render the Feishu SVG report image.") from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("Rendering the Feishu SVG report image timed out.") from error
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Failed to render Feishu SVG report image: {detail or 'unknown error'}")
    if not result.stdout:
        raise RuntimeError("SVG renderer returned an empty PNG.")
    return result.stdout
