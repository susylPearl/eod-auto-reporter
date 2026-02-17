"""
Main application window with sidebar navigation and view switching.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import customtkinter as ctk

from desktop.config_store import load_config, save_config
from desktop.local_scheduler import LocalScheduler
from desktop.views.activity_view import ActivityView
from desktop.views.dashboard_view import DashboardView
from desktop.views.settings_view import SettingsView
from desktop.views.support_view import SupportView

# Color constants
_SIDEBAR_BG = ("#e8eaed", "#1a1b26")
_SIDEBAR_ACTIVE = ("#d1d5db", "#2d2f3d")
_SIDEBAR_HOVER = ("#d5d8dc", "#252736")
_SIDEBAR_TEXT = ("#1f2937", "#c8cad0")
_SIDEBAR_MUTED = ("#6b7280", "#7a7d88")
_ACCENT = ("#6366f1", "#818cf8")


class AppWindow(ctk.CTk):
    """Root window for the EOD Reporter desktop app."""

    WIDTH = 1020
    HEIGHT = 680

    def __init__(self) -> None:
        super().__init__()

        self.title("EOD Auto Reporter")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.minsize(860, 580)

        self._config = load_config()
        self._scheduler = LocalScheduler(on_status=self._on_scheduler_status)
        self._current_view: Optional[str] = None
        self._views: Dict[str, ctk.CTkFrame] = {}

        self._build_layout()
        self._show_view("dashboard")

        if self._has_required_config():
            self._start_scheduler()

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        self._sidebar = ctk.CTkFrame(
            self, width=220, corner_radius=0,
            fg_color=_SIDEBAR_BG,
        )
        self._sidebar.grid(row=0, column=0, sticky="nswe")
        self._sidebar.grid_propagate(False)
        self._sidebar.grid_columnconfigure(0, weight=1)
        self._sidebar.grid_rowconfigure(7, weight=1)

        # Logo / App title
        logo_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=(28, 2), sticky="w")

        ctk.CTkLabel(
            logo_frame, text="EOD",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=_ACCENT,
        ).pack(side="left")
        ctk.CTkLabel(
            logo_frame, text=" Reporter",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=_SIDEBAR_TEXT,
        ).pack(side="left")

        ctk.CTkLabel(
            self._sidebar,
            text="Automated daily updates",
            font=ctk.CTkFont(size=11),
            text_color=_SIDEBAR_MUTED,
        ).grid(row=1, column=0, padx=22, pady=(0, 28), sticky="w")

        # Nav section label
        ctk.CTkLabel(
            self._sidebar, text="MENU",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=_SIDEBAR_MUTED,
        ).grid(row=2, column=0, padx=22, pady=(0, 6), sticky="w")

        # Nav buttons with icons
        self._nav_buttons: Dict[str, ctk.CTkButton] = {}
        nav_items = [
            ("dashboard", "\u2302  Dashboard"),
            ("activity", "\u2261  Activity"),
            ("settings", "\u2699  Settings"),
            ("support", "\u2753  Support"),
        ]

        for idx, (key, label) in enumerate(nav_items):
            btn = ctk.CTkButton(
                self._sidebar,
                text=label,
                font=ctk.CTkFont(size=14),
                height=42,
                anchor="w",
                corner_radius=10,
                fg_color="transparent",
                text_color=_SIDEBAR_TEXT,
                hover_color=_SIDEBAR_HOVER,
                command=lambda k=key: self._show_view(k),
            )
            btn.grid(row=idx + 3, column=0, padx=12, pady=2, sticky="ew")
            self._nav_buttons[key] = btn

        # Appearance at bottom
        ctk.CTkLabel(
            self._sidebar, text="THEME",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=_SIDEBAR_MUTED,
        ).grid(row=8, column=0, padx=22, pady=(0, 4), sticky="w")

        self._appearance_menu = ctk.CTkOptionMenu(
            self._sidebar,
            values=["System", "Dark", "Light"],
            font=ctk.CTkFont(size=12),
            command=self._change_appearance,
            width=160,
            height=32,
            corner_radius=8,
            fg_color=_SIDEBAR_ACTIVE,
            button_color=_SIDEBAR_ACTIVE,
            button_hover_color=_SIDEBAR_HOVER,
            text_color=("gray10", "gray90"),
            dropdown_text_color=("gray10", "gray90"),
        )
        self._appearance_menu.grid(row=9, column=0, padx=16, pady=(0, 20))
        self._appearance_menu.set("System")

        # --- Content area ---
        self._content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self._content.grid(row=0, column=1, sticky="nswe", padx=0, pady=0)
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        # Create all views
        self._views["dashboard"] = DashboardView(
            self._content, scheduler=self._scheduler, config=self._config,
        )
        self._views["activity"] = ActivityView(
            self._content, config=self._config, on_config_change=self._on_activity_config,
        )
        self._views["settings"] = SettingsView(
            self._content, config=self._config, on_save=self._on_settings_saved,
        )
        self._views["support"] = SupportView(
            self._content, config=self._config,
        )

    # ------------------------------------------------------------------ #
    # View switching
    # ------------------------------------------------------------------ #

    def _show_view(self, name: str) -> None:
        if self._current_view == name:
            return

        if self._current_view and self._current_view in self._views:
            self._views[self._current_view].grid_forget()

        self._views[name].grid(row=0, column=0, sticky="nswe", padx=24, pady=20)
        self._current_view = name

        for key, btn in self._nav_buttons.items():
            if key == name:
                btn.configure(fg_color=_SIDEBAR_ACTIVE, text_color=_ACCENT)
            else:
                btn.configure(fg_color="transparent", text_color=_SIDEBAR_TEXT)

    # ------------------------------------------------------------------ #
    # Callbacks
    # ------------------------------------------------------------------ #

    def _on_activity_config(self, new_config: Dict[str, Any]) -> None:
        self._config = new_config
        save_config(new_config)

    def _on_settings_saved(self, new_config: Dict[str, Any]) -> None:
        self._config = new_config
        save_config(new_config)

        # Run reload in background to avoid UI hang (importlib.reload can block)
        def _reload_bg() -> None:
            from desktop.service_bridge import apply_config_and_reload
            apply_config_and_reload(new_config)
            self.after(0, self._after_reload, new_config)

        import threading
        threading.Thread(target=_reload_bg, daemon=True).start()

    def _after_reload(self, new_config: Dict[str, Any]) -> None:
        """Called on main thread after background reload completes."""
        for key in ("dashboard", "activity", "settings", "support"):
            view = self._views[key]
            if hasattr(view, "update_config"):
                view.update_config(new_config)  # type: ignore[union-attr]

        if self._has_required_config():
            self._start_scheduler()

    def _on_scheduler_status(self, event: str, detail: Dict[str, Any]) -> None:
        try:
            dashboard: DashboardView = self._views["dashboard"]  # type: ignore[assignment]
            self.after(0, dashboard.on_scheduler_event, event, detail)
        except Exception:
            pass

    def _change_appearance(self, mode: str) -> None:
        ctk.set_appearance_mode(mode)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _has_required_config(self) -> bool:
        return bool(
            self._config.get("github_token") and self._config.get("slack_bot_token")
        )

    def _start_scheduler(self) -> None:
        hour = int(self._config.get("report_hour", 18))
        minute = int(self._config.get("report_minute", 0))
        tz = str(self._config.get("timezone", "Asia/Kathmandu"))
        self._scheduler.start(hour, minute, tz)

    def on_closing(self) -> None:
        self._scheduler.stop()
        self.destroy()
