"""
Settings View — Material Design 3 styled configuration.
"""

from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog
from typing import Any, Callable, Dict, Optional

import customtkinter as ctk

from desktop.config_store import import_from_file
from desktop.utils import FixedScrollableFrame, bind_mousewheel_to_scroll
from desktop import theme as T

_TIMEZONES = [
    "Asia/Kathmandu", "Asia/Kolkata", "Asia/Dubai", "Asia/Singapore",
    "Asia/Tokyo", "US/Eastern", "US/Central", "US/Pacific",
    "Europe/London", "Europe/Berlin", "Australia/Sydney", "UTC",
]

_AI_PROVIDERS: Dict[str, tuple[str, str]] = {
    "Google Gemini (Free)": ("https://generativelanguage.googleapis.com/v1beta/openai/", "gemini-2.0-flash"),
    "Groq (Free)": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    "OpenAI": ("", "gpt-4o-mini"),
    "Ollama (Local)": ("http://localhost:11434/v1", "llama3.2"),
    "Custom": ("", ""),
}


class SettingsView(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, config: Dict[str, Any],
                 on_save: Callable[[Dict[str, Any]], None]) -> None:
        super().__init__(parent, fg_color="transparent")
        self._config = dict(config)
        self._on_save = on_save
        self._entries: Dict[str, ctk.CTkEntry | ctk.CTkOptionMenu] = {}
        self._test_status_labels: Dict[str, ctk.CTkLabel] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_ui()

    def update_config(self, config: Dict[str, Any]) -> None:
        self._config = dict(config)

    def _build_ui(self) -> None:
        # ── Header ────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(hdr, text="Settings", font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=T.ON_SURFACE, anchor="w").grid(row=0, column=0, sticky="w")

        btn_box = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_box.grid(row=0, column=1, sticky="e")

        self._import_btn = T.m3_outlined_button(btn_box, text="\U0001F4C1  Import File",
                                                command=self._import_file, width=130, height=36)
        self._import_btn.pack(side="left", padx=(0, 6))

        self._save_btn = T.m3_filled_button(btn_box, text="Save Settings",
                                            command=self._save, width=130, height=36)
        self._save_btn.pack(side="left")

        # ── Scroll area ──────────────────────────────────────────────
        self._scroll = FixedScrollableFrame(
            self, corner_radius=16, fg_color=T.CARD_BG,
            border_color=T.CARD_BORDER, border_width=1,
        )
        self._scroll.grid(row=1, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(1, weight=1)
        bind_mousewheel_to_scroll(self._scroll)

        row = 0

        row = self._section("GitHub", "\U0001F4BB", row)
        row = self._field("github_token", "Token", row, show="*")
        row = self._field_test("github_username", "Username", row, test_fn=self._test_github)

        row = self._section("ClickUp", "\u2611", row)
        row = self._field("clickup_api_token", "API Token", row, show="*")
        row = self._field("clickup_team_id", "Team ID", row)
        row = self._field_test("clickup_user_id", "User ID", row, test_fn=self._test_clickup)

        row = self._section("Slack", "\U0001F4AC", row)
        row = self._field("slack_bot_token", "Bot Token", row, show="*")
        row = self._field_test("slack_channel", "EOD Channel", row, test_fn=self._test_slack)
        row = self._field("slack_user_id", "User ID", row)
        row = self._field("slack_display_name", "Display Name", row)
        row = self._field("slack_icon_url", "Icon URL", row)
        row = self._field("slack_monitor_channels", "Monitor Channels", row,
                          placeholder="C01ABC,C02DEF (comma-separated)")

        row = self._section("AI Summary", "\u2728", row)
        row = self._provider_field(row)
        row = self._field("openai_api_key", "API Key", row, show="*")
        row = self._field("ai_model", "Model", row)
        row = self._field("ai_base_url", "Base URL", row, placeholder="Leave empty for OpenAI default")

        row = self._section("Schedule", "\u23F0", row)
        row = self._field("report_hour", "Hour (0-23)", row)
        row = self._field("report_minute", "Minute (0-59)", row)
        row = self._tz_field("timezone", "Timezone", row)

        # Status bar at bottom
        self._status_label = ctk.CTkLabel(
            self._scroll, text="", font=ctk.CTkFont(size=12), text_color=T.SUCCESS, anchor="w",
        )
        self._status_label.grid(row=row, column=0, columnspan=3, sticky="w",
                                padx=14, pady=(12, 16))

    # ── Field builders ────────────────────────────────────────────────

    def _section(self, title: str, icon: str, row: int) -> int:
        ctk.CTkLabel(
            self._scroll, text=f"{icon}  {title}",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=T.PRIMARY, anchor="w",
        ).grid(row=row, column=0, columnspan=3, sticky="w", padx=14, pady=(18, 2))
        ctk.CTkFrame(self._scroll, height=1, fg_color=T.OUTLINE_VARIANT).grid(
            row=row + 1, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 6))
        return row + 2

    def _field(self, key: str, label: str, row: int, show: Optional[str] = None,
               placeholder: str = "") -> int:
        ctk.CTkLabel(self._scroll, text=label, font=ctk.CTkFont(size=13),
                     text_color=T.ON_SURFACE, anchor="w", width=150
                     ).grid(row=row, column=0, sticky="w", padx=(14, 8), pady=3)
        entry = T.m3_text_field(self._scroll, placeholder_text=placeholder)
        if show:
            entry.configure(show=show)
        entry.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(0, 14), pady=3)
        val = self._config.get(key, "")
        if val:
            entry.insert(0, str(val))
        if show:
            vis = [False]
            def toggle(_e: Any = None, _en: ctk.CTkEntry = entry, _s: str = show, _v: list = vis) -> None:
                _v[0] = not _v[0]
                _en.configure(show="" if _v[0] else _s)
            entry.bind("<Double-Button-1>", toggle)
        self._entries[key] = entry
        return row + 1

    def _field_test(self, key: str, label: str, row: int,
                    test_fn: Callable = lambda: None, show: Optional[str] = None) -> int:
        ctk.CTkLabel(self._scroll, text=label, font=ctk.CTkFont(size=13),
                     text_color=T.ON_SURFACE, anchor="w", width=150
                     ).grid(row=row, column=0, sticky="w", padx=(14, 8), pady=3)
        entry = T.m3_text_field(self._scroll)
        if show:
            entry.configure(show=show)
        entry.grid(row=row, column=1, sticky="ew", padx=(0, 6), pady=3)
        val = self._config.get(key, "")
        if val:
            entry.insert(0, str(val))
        cell = ctk.CTkFrame(self._scroll, fg_color="transparent")
        cell.grid(row=row, column=2, padx=(0, 14), pady=3)
        T.m3_tonal_button(cell, text="Test", width=64, height=40, corner_radius=12,
                         command=test_fn).pack(side="left")
        status_lbl = ctk.CTkLabel(cell, text="", font=ctk.CTkFont(size=11),
                                  text_color=T.MUTED, anchor="w")
        status_lbl.pack(side="left", padx=(6, 0))
        self._test_status_labels[key] = status_lbl
        self._entries[key] = entry
        return row + 1

    def _provider_field(self, row: int) -> int:
        ctk.CTkLabel(self._scroll, text="Provider", font=ctk.CTkFont(size=13),
                     text_color=T.ON_SURFACE, anchor="w", width=150
                     ).grid(row=row, column=0, sticky="w", padx=(14, 8), pady=3)
        cur = str(self._config.get("ai_provider", "Google Gemini (Free)"))
        names = list(_AI_PROVIDERS.keys())
        if cur not in names:
            cur = "Custom"
        self._provider_menu = ctk.CTkOptionMenu(
            self._scroll, values=names, font=ctk.CTkFont(size=13),
            height=40, corner_radius=12, command=self._on_provider_change,
            fg_color=T.SURFACE_CONTAINER, text_color=T.ON_SURFACE,
            button_color=T.OUTLINE_VARIANT, button_hover_color=T.SURFACE_CONTAINER_HIGH,
            dropdown_fg_color=T.SURFACE_CONTAINER,
            dropdown_text_color=T.ON_SURFACE,
            dropdown_hover_color=T.SURFACE_CONTAINER_HIGH,
        )
        self._provider_menu.set(cur)
        self._provider_menu.grid(row=row, column=1, columnspan=2, sticky="ew",
                                 padx=(0, 14), pady=3)
        self._entries["ai_provider"] = self._provider_menu
        return row + 1

    def _on_provider_change(self, choice: str) -> None:
        preset = _AI_PROVIDERS.get(choice)
        if not preset:
            return
        base_url, model = preset
        url_entry = self._entries.get("ai_base_url")
        model_entry = self._entries.get("ai_model")
        if isinstance(url_entry, ctk.CTkEntry):
            url_entry.delete(0, "end")
            if base_url:
                url_entry.insert(0, base_url)
        if isinstance(model_entry, ctk.CTkEntry) and model:
            model_entry.delete(0, "end")
            model_entry.insert(0, model)

    def _tz_field(self, key: str, label: str, row: int) -> int:
        ctk.CTkLabel(self._scroll, text=label, font=ctk.CTkFont(size=13),
                     text_color=T.ON_SURFACE, anchor="w", width=150
                     ).grid(row=row, column=0, sticky="w", padx=(14, 8), pady=3)
        cur = str(self._config.get(key, "Asia/Kathmandu"))
        vals = list(_TIMEZONES)
        if cur not in vals:
            vals.insert(0, cur)
        menu = ctk.CTkOptionMenu(
            self._scroll, values=vals, font=ctk.CTkFont(size=13),
            height=40, corner_radius=12,
            fg_color=T.SURFACE_CONTAINER, text_color=T.ON_SURFACE,
            button_color=T.OUTLINE_VARIANT, button_hover_color=T.SURFACE_CONTAINER_HIGH,
            dropdown_fg_color=T.SURFACE_CONTAINER,
            dropdown_text_color=T.ON_SURFACE,
            dropdown_hover_color=T.SURFACE_CONTAINER_HIGH,
        )
        menu.set(cur)
        menu.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(0, 14), pady=3)
        self._entries[key] = menu
        return row + 1

    # ── Save ──────────────────────────────────────────────────────────

    def _save(self) -> None:
        nc: Dict[str, Any] = dict(self._config)
        for key, w in self._entries.items():
            if isinstance(w, ctk.CTkOptionMenu):
                nc[key] = w.get()
            elif isinstance(w, ctk.CTkEntry):
                val = w.get().strip()
                if key in ("report_hour", "report_minute"):
                    try:
                        val = int(val)
                    except ValueError:
                        val = 0
                nc[key] = val
        self._config = nc
        self._on_save(nc)
        self._status_label.configure(text="\u2705  Settings saved!", text_color=T.SUCCESS)
        self.after(3000, lambda: self._status_label.configure(text=""))

    # ── Import ────────────────────────────────────────────────────────

    def _import_file(self) -> None:
        fp = filedialog.askopenfilename(
            title="Select Config File",
            filetypes=[
                ("All supported", "*.env *.json *.txt *.md *.docx *.doc"),
                ("Environment files", "*.env"),
                ("JSON files", "*.json"),
                ("Text / Markdown", "*.txt *.md"),
                ("Word documents", "*.docx *.doc"),
                ("All files", "*.*"),
            ],
        )
        if not fp:
            return
        path = Path(fp)
        if not path.exists():
            self._status_label.configure(text="\u274C  File not found", text_color=T.ERROR)
            return
        self._status_label.configure(text=f"Parsing {path.name}...", text_color=T.MUTED)
        self._import_btn.configure(state="disabled")
        threading.Thread(target=self._import_bg, args=(path,), daemon=True).start()

    def _import_bg(self, path: Path) -> None:
        try:
            imported = import_from_file(path)
        except Exception as exc:
            self.after(0, self._import_done, path, None, str(exc))
            return
        self.after(0, self._import_done, path, imported, "")

    def _import_done(self, path: Path, imported: Optional[Dict[str, Any]], error: str) -> None:
        self._import_btn.configure(state="normal")
        if error:
            self._status_label.configure(text=f"\u274C  {error[:80]}", text_color=T.ERROR)
            return
        if not imported:
            suffix = path.suffix.lower()
            if suffix in (".docx", ".doc"):
                self._status_label.configure(
                    text="\u274C  Could not parse \u2014 ensure python-docx is installed",
                    text_color=T.ERROR)
            else:
                self._status_label.configure(text="\u274C  No settings found in file",
                                             text_color=T.ERROR)
            return

        populated = 0
        from desktop.config_store import DEFAULT_CONFIG
        for key, w in self._entries.items():
            val = imported.get(key, "")
            default_val = DEFAULT_CONFIG.get(key, "")
            if not val or str(val) == str(default_val):
                continue
            if isinstance(w, ctk.CTkEntry):
                w.delete(0, "end")
                w.insert(0, str(val))
                populated += 1
            elif isinstance(w, ctk.CTkOptionMenu) and val:
                w.set(str(val))
                populated += 1
        self._status_label.configure(
            text=f"\U0001F4C1  Imported {populated} fields from {path.name} \u2014 click Save",
            text_color=T.WARNING)

    # ── Tests ─────────────────────────────────────────────────────────

    def _test_github(self) -> None:
        lbl = self._test_status_labels.get("github_username")
        if lbl:
            lbl.configure(text="Testing...", text_color=T.MUTED)
        threading.Thread(target=self._test_github_bg, daemon=True).start()

    def _test_github_bg(self) -> None:
        lbl = self._test_status_labels.get("github_username")
        try:
            import requests
            tok = self._entries["github_token"].get().strip()
            usr = self._entries["github_username"].get().strip()
            r = requests.get(f"https://api.github.com/users/{usr}",
                             headers={"Authorization": f"Bearer {tok}",
                                      "Accept": "application/vnd.github+json"}, timeout=10)
            if r.status_code == 200:
                name = r.json().get("name", usr)
                self.after(0, lambda: lbl.configure(
                    text=f"\u2705 OK: {name}", text_color=T.SUCCESS) if lbl else None)
            else:
                self.after(0, lambda: lbl.configure(
                    text=f"\u274C Error {r.status_code}", text_color=T.ERROR) if lbl else None)
        except Exception as e:
            self.after(0, lambda: lbl.configure(
                text=f"\u274C {str(e)[:30]}", text_color=T.ERROR) if lbl else None)

    def _test_clickup(self) -> None:
        lbl = self._test_status_labels.get("clickup_user_id")
        if lbl:
            lbl.configure(text="Testing...", text_color=T.MUTED)
        threading.Thread(target=self._test_clickup_bg, daemon=True).start()

    def _test_clickup_bg(self) -> None:
        lbl = self._test_status_labels.get("clickup_user_id")
        try:
            import requests
            tok = self._entries["clickup_api_token"].get().strip()
            r = requests.get("https://api.clickup.com/api/v2/user",
                             headers={"Authorization": tok}, timeout=10)
            if r.status_code == 200:
                u = r.json().get("user", {}).get("username", "OK")
                self.after(0, lambda: lbl.configure(
                    text=f"\u2705 OK: {u}", text_color=T.SUCCESS) if lbl else None)
            else:
                self.after(0, lambda: lbl.configure(
                    text=f"\u274C Error {r.status_code}", text_color=T.ERROR) if lbl else None)
        except Exception as e:
            self.after(0, lambda: lbl.configure(
                text=f"\u274C {str(e)[:30]}", text_color=T.ERROR) if lbl else None)

    def _test_slack(self) -> None:
        lbl = self._test_status_labels.get("slack_channel")
        if lbl:
            lbl.configure(text="Testing...", text_color=T.MUTED)
        threading.Thread(target=self._test_slack_bg, daemon=True).start()

    def _test_slack_bg(self) -> None:
        lbl = self._test_status_labels.get("slack_channel")
        try:
            from slack_sdk import WebClient
            tok = self._entries["slack_bot_token"].get().strip()
            resp = WebClient(token=tok).auth_test()
            team = resp.get("team", "")
            self.after(0, lambda: lbl.configure(
                    text=f"\u2705 OK: {team}", text_color=T.SUCCESS) if lbl else None)
        except Exception as e:
            self.after(0, lambda: lbl.configure(
                    text=f"\u274C {str(e)[:30]}", text_color=T.ERROR) if lbl else None)
