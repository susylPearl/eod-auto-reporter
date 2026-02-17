"""
Desktop app utilities — fix CTkScrollableFrame scrolling on macOS + Tk 9.0.

ROOT CAUSE:
  Tk 9.0 on macOS generates <TouchpadScroll> events for trackpad two-finger
  scrolling (TIP 684). The old <MouseWheel> event is NO LONGER fired for
  trackpad gestures. CustomTkinter only binds <MouseWheel>, so trackpad
  scrolling is completely broken.

FIX:
  Bind <TouchpadScroll> globally. On each event, find which registered
  CTkScrollableFrame is under the pointer (bounding-box hit test) and
  scroll its canvas using pixel-precise deltas from tk::PreciseScrollDeltas.
  Also keep <MouseWheel> binding as fallback for external mice.
"""

from __future__ import annotations

import platform
import tkinter as tk
from typing import Any, Optional, Set

import customtkinter as ctk

_registered: Set[ctk.CTkScrollableFrame] = set()
_bound = False
_SCROLL_SLOW_FACTOR = 3.0


def _find_scroll_frame_at_pointer(event: Any) -> Optional[ctk.CTkScrollableFrame]:
    """Return the registered scroll frame under the mouse pointer, if any."""
    try:
        root = event.widget
        if not isinstance(root, (tk.Tk, tk.Toplevel)):
            root = root.winfo_toplevel()
        px = root.winfo_pointerx()
        py = root.winfo_pointery()
    except Exception:
        return None

    for frame in list(_registered):
        try:
            if not frame.winfo_exists():
                _registered.discard(frame)
                continue
            # Skip frames hidden by grid_forget / pack_forget (stale coords)
            if not frame.winfo_viewable():
                continue
            fx = frame.winfo_rootx()
            fy = frame.winfo_rooty()
            fw = max(1, frame.winfo_width())
            fh = max(1, frame.winfo_height())
            if fx <= px <= fx + fw and fy <= py <= fy + fh:
                return frame
        except Exception:
            continue
    return None


def _on_touchpad_scroll(event: Any) -> str:
    """Handle <TouchpadScroll> — Tk 9.0 macOS trackpad two-finger scroll."""
    frame = _find_scroll_frame_at_pointer(event)
    if frame is None:
        return ""

    canvas = getattr(frame, "_parent_canvas", None)
    if canvas is None:
        return "break"

    try:
        result = canvas.tk.call("tk::PreciseScrollDeltas", event.delta)
        dy = float(result[1])
    except Exception:
        return "break"

    if dy == 0:
        return "break"

    amount = int(-dy / _SCROLL_SLOW_FACTOR)
    if amount == 0:
        amount = -1 if dy > 0 else 1
    canvas.yview_scroll(amount, "units")
    return "break"


def _on_mousewheel(event: Any) -> str:
    """Handle <MouseWheel> — fallback for external mice / older Tk."""
    frame = _find_scroll_frame_at_pointer(event)
    if frame is None:
        return ""

    canvas = getattr(frame, "_parent_canvas", None)
    if canvas is None:
        return "break"

    delta = event.delta
    if platform.system() == "Darwin":
        scroll_amount = int(-delta / _SCROLL_SLOW_FACTOR)
        if scroll_amount == 0 and delta != 0:
            scroll_amount = -1 if delta > 0 else 1
    else:
        scroll_amount = int((-delta / 120) / _SCROLL_SLOW_FACTOR)
        if scroll_amount == 0 and delta != 0:
            scroll_amount = -1 if delta > 0 else 1

    canvas.yview_scroll(scroll_amount, "units")
    return "break"


def bind_mousewheel_to_scroll(scroll_frame: ctk.CTkScrollableFrame) -> None:
    """
    Register a CTkScrollableFrame for trackpad + mouse wheel scrolling.

    Call once after creating each CTkScrollableFrame. Binds the correct
    events globally so trackpad and mouse wheel work over content.
    """
    global _bound
    _registered.add(scroll_frame)

    if _bound:
        return

    root = scroll_frame.winfo_toplevel()

    # Primary: <TouchpadScroll> for Tk 9.0+ macOS trackpad
    try:
        root.bind_all("<TouchpadScroll>", _on_touchpad_scroll)
    except tk.TclError:
        pass

    # Fallback: <MouseWheel> for external mice and older Tk
    if platform.system() in ("Darwin", "Windows"):
        root.bind_all("<MouseWheel>", _on_mousewheel)
    else:
        root.bind_all("<Button-4>", _on_mousewheel)
        root.bind_all("<Button-5>", _on_mousewheel)

    _bound = True


# Alias for drop-in replacement in views
FixedScrollableFrame = ctk.CTkScrollableFrame
