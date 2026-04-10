"""CMS block renderer — converts block JSON to HTML.

Each block has the shape: {"id": str, "type": str, "props": dict}
Renders to HTML styled with HUBEX Warm Depth design tokens.
"""
from __future__ import annotations

import html as _html
from typing import Any, Iterable

from sqlalchemy.ext.asyncio import AsyncSession


# ── HUBEX Warm Depth palette ─────────────────────────────────────────────
COLOR_BG = "#111110"
COLOR_TEXT = "#E5E5E5"
COLOR_TEXT_MUTED = "#A1A1AA"
COLOR_BORDER = "rgba(255,255,255,0.08)"
COLOR_PANEL = "rgba(255,255,255,0.03)"
COLOR_PRIMARY = "#F5A623"  # amber
COLOR_ACCENT = "#2DD4BF"  # teal


def _esc(value: Any) -> str:
    if value is None:
        return ""
    return _html.escape(str(value), quote=True)


def _num(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _align(value: Any, default: str = "left") -> str:
    v = (value or "").lower()
    return v if v in ("left", "center", "right") else default


def _props(block: dict[str, Any]) -> dict[str, Any]:
    return block.get("props") or {}


# ── Block renderers ──────────────────────────────────────────────────────

def render_heading(block: dict[str, Any]) -> str:
    p = _props(block)
    level = p.get("level") or "h2"
    if level not in ("h1", "h2", "h3"):
        level = "h2"
    text = _esc(p.get("text", ""))
    align = _align(p.get("align"), "left")
    sizes = {"h1": 44, "h2": 30, "h3": 22}
    size = sizes[level]
    style = (
        f"font-size:{size}px;font-weight:700;color:#F5F5F5;"
        f"margin:24px 0 12px;text-align:{align};font-family:'Satoshi',sans-serif;"
    )
    return f'<{level} style="{style}">{text}</{level}>'


def render_text(block: dict[str, Any]) -> str:
    p = _props(block)
    # Content is rich HTML from WYSIWYG — trust but scope with styles.
    content = p.get("content", "") or ""
    style = (
        f"color:{COLOR_TEXT_MUTED};line-height:1.7;font-size:16px;"
        "margin:12px 0;font-family:'Inter',sans-serif;"
    )
    return f'<div class="hx-block-text" style="{style}">{content}</div>'


def render_image(block: dict[str, Any]) -> str:
    p = _props(block)
    src = _esc(p.get("src", ""))
    alt = _esc(p.get("alt", ""))
    caption = _esc(p.get("caption", ""))
    width = p.get("width")
    align = _align(p.get("align"), "center")
    if not src:
        return ""
    width_css = f"max-width:{_num(width, 800)}px;" if width else "max-width:100%;"
    margin = {
        "center": "margin:24px auto;",
        "left": "margin:24px 0;",
        "right": "margin:24px 0 24px auto;",
    }[align]
    wrapper_style = f"{margin}{width_css}text-align:{align};"
    img_style = "max-width:100%;height:auto;border-radius:10px;display:block;"
    cap_html = ""
    if caption:
        cap_html = (
            f'<figcaption style="color:{COLOR_TEXT_MUTED};font-size:13px;'
            f'margin-top:8px;text-align:{align};">{caption}</figcaption>'
        )
    return (
        f'<figure style="{wrapper_style}">'
        f'<img src="{src}" alt="{alt}" style="{img_style}" />'
        f"{cap_html}"
        "</figure>"
    )


def render_hero(block: dict[str, Any]) -> str:
    p = _props(block)
    title = _esc(p.get("title", ""))
    subtitle = _esc(p.get("subtitle", ""))
    bg_color = _esc(p.get("bg_color") or "#111110")
    cta_text = _esc(p.get("cta_text", ""))
    cta_link = _esc(p.get("cta_link", "#"))
    cta2_text = _esc(p.get("cta_secondary_text", ""))
    cta2_link = _esc(p.get("cta_secondary_link", "#"))

    section_style = (
        f"padding:96px 24px;text-align:center;"
        f"background:radial-gradient(ellipse at top,rgba(245,166,35,0.12),transparent),{bg_color};"
        "border-bottom:1px solid rgba(255,255,255,0.08);"
    )
    title_style = (
        "font-size:56px;font-weight:800;margin:0 0 16px;color:#F5F5F5;"
        "font-family:'Satoshi',sans-serif;letter-spacing:-0.02em;"
    )
    sub_style = (
        f"font-size:20px;color:{COLOR_TEXT_MUTED};max-width:640px;"
        "margin:0 auto 32px;line-height:1.6;"
    )
    btn1_style = (
        f"display:inline-block;padding:14px 28px;background:{COLOR_PRIMARY};"
        "color:#111110;border-radius:10px;font-weight:600;text-decoration:none;"
        "margin:0 6px;"
    )
    btn2_style = (
        f"display:inline-block;padding:14px 28px;background:transparent;"
        f"color:{COLOR_ACCENT};border-radius:10px;font-weight:600;"
        f"text-decoration:none;border:1px solid {COLOR_ACCENT};margin:0 6px;"
    )
    buttons = ""
    if cta_text:
        buttons += f'<a href="{cta_link}" style="{btn1_style}">{cta_text}</a>'
    if cta2_text:
        buttons += f'<a href="{cta2_link}" style="{btn2_style}">{cta2_text}</a>'
    btn_wrap = f'<div style="margin-top:32px;">{buttons}</div>' if buttons else ""
    return (
        f'<section style="{section_style}">'
        f'<h1 style="{title_style}">{title}</h1>'
        f'<p style="{sub_style}">{subtitle}</p>'
        f"{btn_wrap}"
        "</section>"
    )


def render_feature_grid(block: dict[str, Any]) -> str:
    p = _props(block)
    columns = _num(p.get("columns"), 3)
    if columns < 1:
        columns = 1
    if columns > 6:
        columns = 6
    items = p.get("items") or []
    cards: list[str] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        icon = _esc(it.get("icon", ""))
        title = _esc(it.get("title", ""))
        desc = _esc(it.get("description", ""))
        icon_html = (
            f'<div style="font-size:28px;margin-bottom:12px;">{icon}</div>' if icon else ""
        )
        card = (
            f'<div style="background:{COLOR_PANEL};border:1px solid {COLOR_BORDER};'
            'border-radius:12px;padding:28px;">'
            f'{icon_html}'
            f'<h3 style="color:{COLOR_PRIMARY};margin:0 0 12px;font-size:18px;">{title}</h3>'
            f'<p style="color:{COLOR_TEXT_MUTED};margin:0;line-height:1.6;">{desc}</p>'
            "</div>"
        )
        cards.append(card)
    grid_style = (
        f"display:grid;grid-template-columns:repeat({columns},1fr);gap:24px;"
        "max-width:1200px;margin:48px auto;padding:0 24px;"
    )
    return f'<section style="{grid_style}">{"".join(cards)}</section>'


def render_cta(block: dict[str, Any]) -> str:
    p = _props(block)
    title = _esc(p.get("title", ""))
    desc = _esc(p.get("description", ""))
    btn_text = _esc(p.get("button_text", ""))
    btn_link = _esc(p.get("button_link", "#"))
    style_variant = (p.get("style") or "amber").lower()
    bg = {
        "amber": "rgba(245,166,35,0.08)",
        "teal": "rgba(45,212,191,0.08)",
        "dark": "rgba(255,255,255,0.03)",
    }.get(style_variant, "rgba(245,166,35,0.08)")
    border = {
        "amber": "rgba(245,166,35,0.2)",
        "teal": "rgba(45,212,191,0.2)",
        "dark": "rgba(255,255,255,0.08)",
    }.get(style_variant, "rgba(245,166,35,0.2)")
    btn_bg = COLOR_PRIMARY if style_variant != "teal" else COLOR_ACCENT
    section_style = (
        f"padding:64px 24px;text-align:center;background:{bg};"
        f"border-top:1px solid {border};border-bottom:1px solid {border};"
    )
    btn_style = (
        f"display:inline-block;padding:12px 28px;background:{btn_bg};"
        "color:#111110;border-radius:8px;font-weight:600;text-decoration:none;"
    )
    btn_html = f'<a href="{btn_link}" style="{btn_style}">{btn_text}</a>' if btn_text else ""
    return (
        f'<section style="{section_style}">'
        f'<h2 style="font-size:32px;margin:0 0 12px;color:#F5F5F5;">{title}</h2>'
        f'<p style="color:{COLOR_TEXT_MUTED};margin:0 0 24px;">{desc}</p>'
        f"{btn_html}"
        "</section>"
    )


def render_spacer(block: dict[str, Any]) -> str:
    p = _props(block)
    height = _num(p.get("height"), 40)
    return f'<div style="height:{height}px;" aria-hidden="true"></div>'


def render_divider(block: dict[str, Any]) -> str:
    p = _props(block)
    style_variant = (p.get("style") or "solid").lower()
    width = _num(p.get("width"), 100)
    border_style = style_variant if style_variant in ("solid", "dashed", "dotted") else "solid"
    wrapper = f"margin:32px auto;width:{width}%;max-width:1200px;"
    hr_style = f"border:none;border-top:1px {border_style} {COLOR_BORDER};margin:0;"
    return f'<div style="{wrapper}"><hr style="{hr_style}" /></div>'


def render_columns(block: dict[str, Any]) -> str:
    p = _props(block)
    count = _num(p.get("count"), 2)
    if count < 1:
        count = 1
    if count > 6:
        count = 6
    items = p.get("items") or []
    col_html: list[str] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        content = it.get("content", "")
        # Content is either HTML string or list of sub-blocks
        if isinstance(content, list):
            inner = render_blocks_to_html_sync(content)
        else:
            inner = str(content or "")
        col_html.append(f'<div style="flex:1;min-width:0;">{inner}</div>')
    style = (
        f"display:grid;grid-template-columns:repeat({count},1fr);gap:24px;"
        "max-width:1200px;margin:24px auto;padding:0 24px;"
    )
    return f'<section style="{style}">{"".join(col_html)}</section>'


def render_html(block: dict[str, Any]) -> str:
    p = _props(block)
    # Raw HTML — trust the editor
    return str(p.get("content", "") or "")


def render_video(block: dict[str, Any]) -> str:
    p = _props(block)
    url = _esc(p.get("url", ""))
    caption = _esc(p.get("caption", ""))
    autoplay = bool(p.get("autoplay"))
    aspect = (p.get("aspect_ratio") or "16:9").replace(":", "/")
    if not url:
        return ""
    wrap_style = "max-width:960px;margin:32px auto;padding:0 24px;"
    ratio_style = f"position:relative;aspect-ratio:{aspect};border-radius:12px;overflow:hidden;border:1px solid {COLOR_BORDER};"
    # If it's YouTube/Vimeo, use iframe; otherwise use <video>
    lower = url.lower()
    if "youtube.com" in lower or "youtu.be" in lower or "vimeo.com" in lower:
        src = url
        if autoplay and "autoplay=" not in src:
            sep = "&" if "?" in src else "?"
            src = f"{src}{sep}autoplay=1"
        inner = (
            f'<iframe src="{src}" frameborder="0" allowfullscreen '
            'style="position:absolute;inset:0;width:100%;height:100%;"></iframe>'
        )
    else:
        auto_attr = " autoplay muted loop playsinline" if autoplay else " controls"
        inner = (
            f'<video src="{url}"{auto_attr} '
            'style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;"></video>'
        )
    cap = (
        f'<div style="color:{COLOR_TEXT_MUTED};font-size:13px;text-align:center;margin-top:8px;">{caption}</div>'
        if caption
        else ""
    )
    return (
        f'<div style="{wrap_style}">'
        f'<div style="{ratio_style}">{inner}</div>'
        f"{cap}"
        "</div>"
    )


def render_quote(block: dict[str, Any]) -> str:
    p = _props(block)
    text = _esc(p.get("text", ""))
    author = _esc(p.get("author", ""))
    role = _esc(p.get("role", ""))
    avatar = _esc(p.get("avatar", ""))
    wrap = (
        f"max-width:800px;margin:48px auto;padding:40px;"
        f"background:{COLOR_PANEL};border-left:4px solid {COLOR_PRIMARY};"
        "border-radius:12px;"
    )
    quote_style = (
        "font-size:22px;line-height:1.5;color:#F5F5F5;margin:0 0 20px;"
        "font-family:'Satoshi',sans-serif;font-style:italic;"
    )
    footer = ""
    if author:
        avatar_html = (
            f'<img src="{avatar}" alt="{author}" '
            'style="width:48px;height:48px;border-radius:50%;object-fit:cover;" />'
            if avatar
            else ""
        )
        footer = (
            '<div style="display:flex;align-items:center;gap:12px;">'
            f"{avatar_html}"
            f'<div><div style="color:{COLOR_PRIMARY};font-weight:600;">{author}</div>'
            f'<div style="color:{COLOR_TEXT_MUTED};font-size:13px;">{role}</div></div>'
            "</div>"
        )
    return (
        f'<blockquote style="{wrap}">'
        f'<p style="{quote_style}">“{text}”</p>'
        f"{footer}"
        "</blockquote>"
    )


def render_stats(block: dict[str, Any]) -> str:
    p = _props(block)
    items = p.get("items") or []
    cells: list[str] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        value = _esc(it.get("value", ""))
        label = _esc(it.get("label", ""))
        color = _esc(it.get("color") or COLOR_PRIMARY)
        cells.append(
            '<div style="text-align:center;">'
            f'<div style="font-family:\'IBM Plex Mono\',monospace;font-size:42px;'
            f'color:{color};font-weight:700;">{value}</div>'
            f'<div style="color:{COLOR_TEXT_MUTED};font-size:12px;text-transform:uppercase;'
            f'letter-spacing:0.08em;margin-top:4px;">{label}</div>'
            "</div>"
        )
    cols = max(1, min(len(cells), 6))
    grid = (
        f"display:grid;grid-template-columns:repeat({cols},1fr);gap:24px;"
        "max-width:1000px;margin:48px auto;padding:0 24px;"
    )
    return f'<section style="{grid}">{"".join(cells)}</section>'


def render_button(block: dict[str, Any]) -> str:
    p = _props(block)
    text = _esc(p.get("text", ""))
    link = _esc(p.get("link", "#"))
    style_variant = (p.get("style") or "primary").lower()
    size = (p.get("size") or "md").lower()
    align = _align(p.get("align"), "left")
    if not text:
        return ""
    padding = {"sm": "8px 16px", "md": "12px 24px", "lg": "16px 32px"}.get(size, "12px 24px")
    font_size = {"sm": "13px", "md": "15px", "lg": "17px"}.get(size, "15px")
    variants = {
        "primary": f"background:{COLOR_PRIMARY};color:#111110;border:none;",
        "secondary": f"background:transparent;color:{COLOR_ACCENT};border:1px solid {COLOR_ACCENT};",
        "ghost": f"background:rgba(255,255,255,0.05);color:#E5E5E5;border:1px solid {COLOR_BORDER};",
    }
    style = (
        f"display:inline-block;padding:{padding};border-radius:8px;font-weight:600;"
        f"text-decoration:none;font-size:{font_size};"
        f"{variants.get(style_variant, variants['primary'])}"
    )
    wrap = f'<div style="text-align:{align};margin:16px 0;">'
    return f'{wrap}<a href="{link}" style="{style}">{text}</a></div>'


def render_list(block: dict[str, Any]) -> str:
    p = _props(block)
    tag = "ol" if (p.get("type") == "ol") else "ul"
    items = p.get("items") or []
    lis = "".join(f"<li>{_esc(it)}</li>" for it in items)
    style = (
        f"color:{COLOR_TEXT_MUTED};max-width:800px;margin:16px auto;"
        "padding:0 24px 0 48px;line-height:1.8;font-size:16px;"
    )
    return f'<{tag} style="{style}">{lis}</{tag}>'


# ── HubEx integration blocks ─────────────────────────────────────────────
#
# These render "hydration shells" — a data-hubex-block element the frontend
# BlockRenderer picks up and replaces with a live Vue component. Static SSR
# is intentional: no blocking DB calls at render time, so a public CMS page
# never stalls on a device query.


def _hub_wrap(
    block_type: str,
    props: dict[str, Any],
    label: str = "",
    extra_style: str = "",
    inner_html: str = "",
) -> str:
    import json as _json

    raw = _json.dumps(props, default=str)
    attr = _html.escape(raw, quote=True)
    base_style = (
        f"max-width:960px;margin:16px auto;padding:20px;"
        f"background:{COLOR_PANEL};border:1px solid {COLOR_BORDER};border-radius:12px;"
    )
    lbl = (
        f'<div style="color:{COLOR_TEXT_MUTED};font-size:11px;text-transform:uppercase;'
        f'letter-spacing:0.08em;margin-bottom:8px;">{_esc(label)}</div>'
        if label
        else ""
    )
    return (
        f'<div class="hx-hub-block" data-hubex-block="{block_type}" '
        f'data-hubex-props="{attr}" style="{base_style}{extra_style}">'
        f"{lbl}{inner_html}"
        "</div>"
    )


def render_dashboard_embed(block: dict[str, Any]) -> str:
    p = _props(block)
    dashboard_id = _num(p.get("dashboard_id"), 0)
    height = _num(p.get("height"), 600)
    if not dashboard_id:
        return _hub_wrap(
            "dashboard_embed",
            p,
            "Dashboard embed",
            inner_html=f'<div style="color:{COLOR_TEXT_MUTED};padding:24px;">Dashboard not configured</div>',
        )
    src = f"/kiosk/{dashboard_id}"
    iframe = (
        f'<iframe src="{_esc(src)}" '
        f'style="width:100%;height:{height}px;border:0;border-radius:8px;background:#111110;" '
        'loading="lazy"></iframe>'
    )
    return _hub_wrap("dashboard_embed", p, "", "padding:0;background:transparent;border:0;", iframe)


def render_variable_value(block: dict[str, Any]) -> str:
    p = _props(block)
    label = _esc(p.get("label", "") or p.get("key", ""))
    unit = _esc(p.get("unit", ""))
    key = _esc(p.get("key", ""))
    placeholder = (
        f'<div style="font-family:\'IBM Plex Mono\',monospace;font-size:44px;'
        f'color:{COLOR_PRIMARY};font-weight:700;">—</div>'
        f'<div style="color:{COLOR_TEXT_MUTED};margin-top:6px;">'
        f'{label or key}{f" ({unit})" if unit else ""}</div>'
    )
    return _hub_wrap(
        "variable_value",
        p,
        "",
        "text-align:center;max-width:360px;",
        placeholder,
    )


def render_device_card(block: dict[str, Any]) -> str:
    p = _props(block)
    device_uid = _esc(p.get("device_uid", ""))
    return _hub_wrap(
        "device_card",
        p,
        f"Device: {device_uid}",
        "max-width:520px;",
        f'<div style="color:{COLOR_TEXT_MUTED};">Loading device…</div>',
    )


def render_device_list(block: dict[str, Any]) -> str:
    p = _props(block)
    columns = _num(p.get("columns"), 3)
    filter_label = _esc(p.get("filter", "all"))
    return _hub_wrap(
        "device_list",
        p,
        f"Devices ({filter_label})",
        f"max-width:1200px;",
        f'<div style="display:grid;grid-template-columns:repeat({columns},1fr);gap:16px;">'
        f'<div style="color:{COLOR_TEXT_MUTED};padding:24px;text-align:center;'
        f'grid-column:1/-1;">Loading devices…</div></div>',
    )


def render_tour_trigger(block: dict[str, Any]) -> str:
    p = _props(block)
    tour_id = _esc(p.get("tour_id", ""))
    button_text = _esc(p.get("button_text", "Take a tour"))
    style_variant = (p.get("style") or "primary").lower()
    variants = {
        "primary": f"background:{COLOR_PRIMARY};color:#111110;",
        "secondary": f"background:transparent;color:{COLOR_ACCENT};border:1px solid {COLOR_ACCENT};",
        "ghost": f"background:rgba(255,255,255,0.05);color:#E5E5E5;border:1px solid {COLOR_BORDER};",
    }
    btn_style = (
        "display:inline-block;padding:12px 24px;border-radius:8px;font-weight:600;"
        "text-decoration:none;border:none;cursor:pointer;font-size:15px;"
        f"{variants.get(style_variant, variants['primary'])}"
    )
    button = (
        f'<button type="button" data-tour-trigger="{tour_id}" style="{btn_style}">'
        f"{button_text}</button>"
    )
    return _hub_wrap(
        "tour_trigger",
        p,
        "",
        "text-align:center;background:transparent;border:0;padding:12px;",
        button,
    )


def render_alert_banner(block: dict[str, Any]) -> str:
    p = _props(block)
    return _hub_wrap(
        "alert_banner",
        p,
        "Active alerts",
        "",
        f'<div style="color:{COLOR_TEXT_MUTED};">No alerts yet…</div>',
    )


def render_metric_counter(block: dict[str, Any]) -> str:
    p = _props(block)
    label = _esc(p.get("label", "") or p.get("metric", ""))
    icon = _esc(p.get("icon", ""))
    color = _esc(p.get("color") or COLOR_ACCENT)
    icon_html = f'<div style="font-size:36px;">{icon}</div>' if icon else ""
    inner = (
        f'<div style="display:flex;align-items:center;gap:16px;">'
        f'{icon_html}'
        f'<div>'
        f'<div style="font-family:\'IBM Plex Mono\',monospace;font-size:36px;'
        f'color:{color};font-weight:700;">—</div>'
        f'<div style="color:{COLOR_TEXT_MUTED};font-size:12px;'
        f'text-transform:uppercase;letter-spacing:0.08em;">{label}</div>'
        "</div></div>"
    )
    return _hub_wrap("metric_counter", p, "", "max-width:360px;", inner)


def render_automation_status(block: dict[str, Any]) -> str:
    p = _props(block)
    automation_id = _num(p.get("automation_id"), 0)
    return _hub_wrap(
        "automation_status",
        p,
        f"Automation #{automation_id}" if automation_id else "Automation",
        "max-width:520px;",
        f'<div style="color:{COLOR_TEXT_MUTED};">Loading automation…</div>',
    )


# ── Dispatch map ─────────────────────────────────────────────────────────

BLOCK_RENDERERS = {
    "heading": render_heading,
    "text": render_text,
    "image": render_image,
    "hero": render_hero,
    "feature_grid": render_feature_grid,
    "cta": render_cta,
    "spacer": render_spacer,
    "divider": render_divider,
    "columns": render_columns,
    "html": render_html,
    "video": render_video,
    "quote": render_quote,
    "stats": render_stats,
    "button": render_button,
    "list": render_list,
    # HubEx integration blocks (live, hydrated on frontend)
    "dashboard_embed": render_dashboard_embed,
    "variable_value": render_variable_value,
    "device_card": render_device_card,
    "device_list": render_device_list,
    "tour_trigger": render_tour_trigger,
    "alert_banner": render_alert_banner,
    "metric_counter": render_metric_counter,
    "automation_status": render_automation_status,
}


# ── Public API ───────────────────────────────────────────────────────────

def render_blocks_to_html_sync(blocks: Iterable[dict[str, Any]] | None) -> str:
    """Synchronous block renderer — does not handle template vars."""
    if not blocks:
        return ""
    parts: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        renderer = BLOCK_RENDERERS.get(btype)
        if renderer is None:
            continue
        try:
            parts.append(renderer(block))
        except Exception:
            continue
    return "\n".join(parts)


async def render_blocks_to_html(
    blocks: Iterable[dict[str, Any]] | None,
    db: AsyncSession,
    user_id: int | None = None,
) -> str:
    """Render blocks to HTML and substitute template variables.

    `db` and `user_id` are used for resolving {{variable:...}} etc. placeholders.
    """
    html_out = render_blocks_to_html_sync(blocks)
    if not html_out:
        return ""
    # Late import to avoid circular
    from app.api.v1.cms_pages import render_template_vars
    return await render_template_vars(html_out, db, user_id)
