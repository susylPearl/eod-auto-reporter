"""
Material Design 3 (Material You) theme tokens and helper widgets.

All color tuples are (light_mode, dark_mode).
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

# ── Core palette ─────────────────────────────────────────────────────────────
PRIMARY = ("#6750A4", "#D0BCFF")
ON_PRIMARY = ("#FFFFFF", "#381E72")
PRIMARY_CONTAINER = ("#EADDFF", "#4F378B")
ON_PRIMARY_CONTAINER = ("#21005D", "#EADDFF")

SECONDARY = ("#625B71", "#CCC2DC")
ON_SECONDARY = ("#FFFFFF", "#332D41")
SECONDARY_CONTAINER = ("#E8DEF8", "#4A4458")
ON_SECONDARY_CONTAINER = ("#1D192B", "#E8DEF8")

TERTIARY = ("#7D5260", "#EFB8C8")
TERTIARY_CONTAINER = ("#FFD8E4", "#633B48")

ERROR = ("#B3261E", "#F2B8B5")
ERROR_CONTAINER = ("#F9DEDC", "#8C1D18")
ON_ERROR_CONTAINER = ("#410E0B", "#F9DEDC")

# ── Surfaces ─────────────────────────────────────────────────────────────────
SURFACE = ("#FFFBFE", "#1C1B1F")
SURFACE_DIM = ("#DED8E1", "#141218")
SURFACE_CONTAINER_LOWEST = ("#FFFFFF", "#0F0D13")
SURFACE_CONTAINER_LOW = ("#F7F2FA", "#1D1B20")
SURFACE_CONTAINER = ("#F3EDF7", "#211F26")
SURFACE_CONTAINER_HIGH = ("#ECE6F0", "#2B2930")
SURFACE_CONTAINER_HIGHEST = ("#E6E0E9", "#36343B")
ON_SURFACE = ("#1C1B1F", "#E6E1E5")
ON_SURFACE_VARIANT = ("#49454F", "#CAC4D0")
OUTLINE = ("#79747E", "#938F99")
OUTLINE_VARIANT = ("#CAC4D0", "#49454F")
INVERSE_SURFACE = ("#313033", "#E6E1E5")
INVERSE_ON_SURFACE = ("#F4EFF4", "#313033")

# ── Status ───────────────────────────────────────────────────────────────────
SUCCESS = ("#1B873B", "#7DD99B")
SUCCESS_CONTAINER = ("#D4F5DE", "#1A3A25")
WARNING = ("#9A6700", "#FFCF5C")
WARNING_CONTAINER = ("#FFF3CD", "#3D2E00")
INFO = ("#0969DA", "#79C0FF")
INFO_CONTAINER = ("#DBEAFE", "#0D2847")

# ── Sidebar / Nav rail ───────────────────────────────────────────────────────
NAV_BG = ("#F3EDF7", "#1D1B20")
NAV_INDICATOR = ("#E8DEF8", "#4A4458")
NAV_TEXT = ("#49454F", "#CAC4D0")
NAV_TEXT_ACTIVE = ("#1D192B", "#E8DEF8")

# ── Shorthand aliases ────────────────────────────────────────────────────────
MUTED = ON_SURFACE_VARIANT
ACCENT = PRIMARY
CARD_BG = SURFACE_CONTAINER_LOWEST
CARD_BORDER = OUTLINE_VARIANT


# ── Helper widgets ───────────────────────────────────────────────────────────

def m3_card(parent: Any, **kw: Any) -> ctk.CTkFrame:
    kw.setdefault("corner_radius", 12)
    kw.setdefault("fg_color", CARD_BG)
    kw.setdefault("border_color", CARD_BORDER)
    kw.setdefault("border_width", 1)
    return ctk.CTkFrame(parent, **kw)


def m3_filled_card(parent: Any, **kw: Any) -> ctk.CTkFrame:
    kw.setdefault("corner_radius", 12)
    kw.setdefault("fg_color", SURFACE_CONTAINER)
    kw.setdefault("border_width", 0)
    return ctk.CTkFrame(parent, **kw)


def m3_section_title(parent: Any, text: str, **kw: Any) -> ctk.CTkLabel:
    kw.setdefault("font", ctk.CTkFont(size=14, weight="bold"))
    kw.setdefault("text_color", ON_SURFACE)
    kw.setdefault("anchor", "w")
    return ctk.CTkLabel(parent, text=text, **kw)


def m3_body(parent: Any, text: str, **kw: Any) -> ctk.CTkLabel:
    kw.setdefault("font", ctk.CTkFont(size=13))
    kw.setdefault("text_color", ON_SURFACE_VARIANT)
    kw.setdefault("anchor", "w")
    kw.setdefault("justify", "left")
    return ctk.CTkLabel(parent, text=text, **kw)


def m3_chip(
    parent: Any,
    text: str,
    active: bool = True,
    command: Any = None,
    **kw: Any,
) -> ctk.CTkButton:
    return ctk.CTkButton(
        parent,
        text=text,
        height=32,
        corner_radius=8,
        font=ctk.CTkFont(size=12),
        fg_color=SECONDARY_CONTAINER if active else SURFACE_CONTAINER_HIGH,
        text_color=ON_SECONDARY_CONTAINER if active else ON_SURFACE_VARIANT,
        hover_color=SECONDARY_CONTAINER,
        border_width=1,
        border_color=SECONDARY_CONTAINER if active else OUTLINE,
        command=command,
        **kw,
    )


def m3_filled_button(parent: Any, text: str, command: Any = None, **kw: Any) -> ctk.CTkButton:
    kw.setdefault("height", 40)
    kw.setdefault("corner_radius", 20)
    kw.setdefault("font", ctk.CTkFont(size=13, weight="bold"))
    kw.setdefault("fg_color", PRIMARY)
    kw.setdefault("text_color", ON_PRIMARY)
    kw.setdefault("hover_color", PRIMARY_CONTAINER)
    return ctk.CTkButton(parent, text=text, command=command, **kw)


def m3_tonal_button(parent: Any, text: str, command: Any = None, **kw: Any) -> ctk.CTkButton:
    kw.setdefault("height", 40)
    kw.setdefault("corner_radius", 20)
    kw.setdefault("font", ctk.CTkFont(size=13))
    kw.setdefault("fg_color", SECONDARY_CONTAINER)
    kw.setdefault("text_color", ON_SECONDARY_CONTAINER)
    kw.setdefault("hover_color", SURFACE_CONTAINER_HIGHEST)
    return ctk.CTkButton(parent, text=text, command=command, **kw)


def m3_outlined_button(parent: Any, text: str, command: Any = None, **kw: Any) -> ctk.CTkButton:
    kw.setdefault("height", 40)
    kw.setdefault("corner_radius", 20)
    kw.setdefault("font", ctk.CTkFont(size=13))
    kw.setdefault("fg_color", "transparent")
    kw.setdefault("text_color", PRIMARY)
    kw.setdefault("hover_color", SURFACE_CONTAINER)
    kw.setdefault("border_width", 1)
    kw.setdefault("border_color", OUTLINE)
    return ctk.CTkButton(parent, text=text, command=command, **kw)


def m3_text_field(parent: Any, **kw: Any) -> ctk.CTkEntry:
    kw.setdefault("height", 40)
    kw.setdefault("corner_radius", 12)
    kw.setdefault("font", ctk.CTkFont(size=13))
    kw.setdefault("fg_color", SURFACE_CONTAINER)
    kw.setdefault("text_color", ON_SURFACE)
    kw.setdefault("border_color", OUTLINE_VARIANT)
    kw.setdefault("border_width", 1)
    return ctk.CTkEntry(parent, **kw)
