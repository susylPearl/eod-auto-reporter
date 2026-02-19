"""
Main application window with Material Design 3 navigation rail and view switching.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import customtkinter as ctk
from PIL import Image

from desktop.config_store import load_config, save_config
from desktop.local_scheduler import LocalScheduler
from desktop import theme as T
from desktop.views.activity_view import ActivityView
from desktop.views.dashboard_view import DashboardView
from desktop.views.settings_view import SettingsView
from desktop.views.support_view import SupportView


class AppWindow(ctk.CTk):

    WIDTH = 1060
    HEIGHT = 720

    def __init__(self) -> None:
        super().__init__()

        self.title("EOD Auto Reporter")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.minsize(900, 600)

        self._config = load_config()
        self._scheduler = LocalScheduler(on_status=self._on_scheduler_status)
        self._current_view: Optional[str] = None
        self._views: Dict[str, ctk.CTkFrame] = {}

        self._build_layout()
        self._show_view("dashboard")

        if self._has_required_config():
            self._start_scheduler()

        self._health_check()

    # ── Layout ────────────────────────────────────────────────────────────

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.configure(fg_color=T.SURFACE)

        # ── Nav rail ──────────────────────────────────────────────────────
        rail = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=T.NAV_BG)
        rail.grid(row=0, column=0, sticky="nswe")
        rail.grid_propagate(False)
        rail.grid_columnconfigure(0, weight=1)
        rail.grid_rowconfigure(6, weight=1)

        # Logo
        logo_dir = Path(__file__).resolve().parent / "assets"
        icon_path = logo_dir / "icon.png"
        logo = ctk.CTkFrame(rail, fg_color="transparent")
        logo.grid(row=0, column=0, padx=16, pady=(24, 4), sticky="w")
        try:
            if icon_path.exists():
                pil_img = Image.open(icon_path).convert("RGBA")
                self._logo_img = ctk.CTkImage(
                    light_image=pil_img,
                    dark_image=pil_img,
                    size=(32, 32),
                )
                ctk.CTkLabel(logo, image=self._logo_img, text="").pack(side="left", padx=(0, 6))
        except Exception:
            pass
        ctk.CTkLabel(logo, text="EOD", font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=T.PRIMARY).pack(side="left")
        ctk.CTkLabel(logo, text=" Reporter", font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=T.ON_SURFACE).pack(side="left")

        ctk.CTkLabel(rail, text="Automated daily updates", font=ctk.CTkFont(size=10),
                     text_color=T.MUTED).grid(row=1, column=0, padx=18, pady=(0, 20), sticky="w")

        # Nav items — icon at 18pt, label at 13pt for visual balance
        self._nav_buttons: Dict[str, ctk.CTkButton] = {}
        self._nav_icon_labels: Dict[str, ctk.CTkLabel] = {}
        self._nav_text_labels: Dict[str, ctk.CTkLabel] = {}
        nav_items = [
            ("dashboard", "\u2302", "Dashboard"),
            ("activity",  "\u2261", "Activity"),
            ("settings",  "\u2699", "Settings"),
            ("support",   "?",      "Support"),
        ]
        for idx, (key, icon, label) in enumerate(nav_items):
            btn = ctk.CTkFrame(rail, height=40, corner_radius=20,
                               fg_color="transparent", cursor="arrow")
            btn.grid(row=idx + 2, column=0, padx=10, pady=2, sticky="ew")
            btn.grid_propagate(False)
            btn.grid_columnconfigure(1, weight=1)
            btn.grid_rowconfigure(0, weight=1)

            icon_lbl = ctk.CTkLabel(btn, text=icon,
                                    font=ctk.CTkFont(size=18),
                                    text_color=T.NAV_TEXT, width=28, anchor="center")
            icon_lbl.grid(row=0, column=0, padx=(12, 2))

            text_lbl = ctk.CTkLabel(btn, text=label,
                                    font=ctk.CTkFont(size=13),
                                    text_color=T.NAV_TEXT, anchor="w")
            text_lbl.grid(row=0, column=1, sticky="w")

            for widget in (btn, icon_lbl, text_lbl):
                widget.bind("<Button-1>", lambda _e, k=key: self._show_view(k))
                widget.bind("<Enter>", lambda _e, b=btn: b.configure(
                    fg_color=T.SURFACE_CONTAINER_HIGH))
                widget.bind("<Leave>", lambda _e, b=btn, k=key: b.configure(
                    fg_color=T.NAV_INDICATOR if self._current_view == k else "transparent"))

            self._nav_buttons[key] = btn
            self._nav_icon_labels[key] = icon_lbl
            self._nav_text_labels[key] = text_lbl

        # Theme at bottom — label and dropdown left-aligned together
        theme_frame = ctk.CTkFrame(rail, fg_color="transparent")
        theme_frame.grid(row=7, column=0, padx=14, pady=(0, 16), sticky="sw")

        ctk.CTkLabel(theme_frame, text="THEME", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=T.MUTED, anchor="w").pack(anchor="w", pady=(0, 4))

        self._appearance_menu = ctk.CTkOptionMenu(
            theme_frame, values=["System", "Dark", "Light"],
            font=ctk.CTkFont(size=11), command=self._change_appearance,
            width=170, height=32, corner_radius=12,
            fg_color=T.SURFACE_CONTAINER_HIGH,
            button_color=T.SURFACE_CONTAINER_HIGH,
            button_hover_color=T.SURFACE_CONTAINER_HIGHEST,
            text_color=T.ON_SURFACE, dropdown_text_color=T.ON_SURFACE,
            dropdown_fg_color=T.SURFACE_CONTAINER,
            dropdown_hover_color=T.SURFACE_CONTAINER_HIGH,
        )
        self._appearance_menu.pack(anchor="w")
        self._appearance_menu.set("System")

        # ── Content ───────────────────────────────────────────────────────
        self._content = ctk.CTkFrame(self, corner_radius=0, fg_color=T.SURFACE)
        self._content.grid(row=0, column=1, sticky="nswe", padx=0, pady=0)
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

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

    # ── View switching ────────────────────────────────────────────────────

    def _show_view(self, name: str) -> None:
        if self._current_view == name:
            return
        if self._current_view and self._current_view in self._views:
            self._views[self._current_view].grid_forget()

        self._views[name].grid(row=0, column=0, sticky="nswe", padx=(12, 12), pady=12)
        self._current_view = name

        for key, btn in self._nav_buttons.items():
            active = key == name
            btn.configure(fg_color=T.NAV_INDICATOR if active else "transparent")
            self._nav_icon_labels[key].configure(
                text_color=T.NAV_TEXT_ACTIVE if active else T.NAV_TEXT)
            self._nav_text_labels[key].configure(
                text_color=T.NAV_TEXT_ACTIVE if active else T.NAV_TEXT)

    # ── Callbacks ─────────────────────────────────────────────────────────

    def _on_activity_config(self, new_config: Dict[str, Any]) -> None:
        self._config = new_config
        save_config(new_config)

    def _on_settings_saved(self, new_config: Dict[str, Any]) -> None:
        self._config = new_config
        save_config(new_config)

        def _reload_bg() -> None:
            from desktop.service_bridge import apply_config_and_reload
            apply_config_and_reload(new_config)
            self.after(0, self._after_reload, new_config)

        import threading
        threading.Thread(target=_reload_bg, daemon=True).start()

    def _after_reload(self, new_config: Dict[str, Any]) -> None:
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

    def _health_check(self) -> None:
        if self._scheduler.is_running:
            self._scheduler.check_health()
        self.after(60_000, self._health_check)

    def _change_appearance(self, mode: str) -> None:
        ctk.set_appearance_mode(mode)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _has_required_config(self) -> bool:
        return bool(self._config.get("github_token") and self._config.get("slack_bot_token"))

    def _start_scheduler(self) -> None:
        hour = int(self._config.get("report_hour", 18))
        minute = int(self._config.get("report_minute", 0))
        tz = str(self._config.get("timezone", "Asia/Kathmandu"))
        self._scheduler.start(hour, minute, tz)

    def on_closing(self) -> None:
        self._scheduler.stop()
        self.destroy()
