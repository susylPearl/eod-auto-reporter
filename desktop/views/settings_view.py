"""
Settings View — tokens, config, connection testing, and file import.
"""

from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog
from typing import Any, Callable, Dict, Optional

import customtkinter as ctk

from desktop.config_store import import_from_dotenv
from desktop.utils import FixedScrollableFrame, bind_mousewheel_to_scroll

_CARD_BG = ("#ffffff", "#1e1f2e")
_CARD_BORDER = ("#e5e7eb", "#2d2f3d")
_MUTED = ("#6b7280", "#8b8d97")
_ACCENT = ("#6366f1", "#818cf8")
_GREEN = "#22c55e"
_RED = "#ef4444"
_AMBER = "#f59e0b"

_TIMEZONES = [
    "Asia/Kathmandu", "Asia/Kolkata", "Asia/Dubai", "Asia/Singapore",
    "Asia/Tokyo", "US/Eastern", "US/Central", "US/Pacific",
    "Europe/London", "Europe/Berlin", "Australia/Sydney", "UTC",
]

# AI provider presets: (display name) -> (base_url, default_model)
_AI_PROVIDERS: Dict[str, tuple[str, str]] = {
    "Google Gemini (Free)": ("https://generativelanguage.googleapis.com/v1beta/openai/", "gemini-2.0-flash"),
    "Groq (Free)": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    "OpenAI": ("", "gpt-4o-mini"),
    "Ollama (Local)": ("http://localhost:11434/v1", "llama3.2"),
    "Custom": ("", ""),
}


class SettingsView(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, config: Dict[str, Any], on_save: Callable[[Dict[str, Any]], None]) -> None:
        super().__init__(parent, fg_color="transparent")
        self._config = dict(config)
        self._on_save = on_save
        self._entries: Dict[str, ctk.CTkEntry | ctk.CTkOptionMenu] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_ui()

    def update_config(self, config: Dict[str, Any]) -> None:
        self._config = dict(config)

    def _build_ui(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        hdr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(hdr, text="\u2699  Settings", font=ctk.CTkFont(size=28, weight="bold"), anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(hdr, text="API tokens, schedule & preferences", font=ctk.CTkFont(size=13), text_color=_MUTED, anchor="w").grid(row=1, column=0, sticky="w", pady=(2, 0))

        self._import_btn = ctk.CTkButton(hdr, text="\U0001F4C1  Import Config File", width=170, height=34, font=ctk.CTkFont(size=12), corner_radius=10, fg_color=("gray80", "gray28"), hover_color=("gray70", "gray35"), text_color=("gray10", "gray90"), command=self._import_file)
        self._import_btn.grid(row=0, column=1, rowspan=2, sticky="e")

        self._scroll = FixedScrollableFrame(self, corner_radius=14, fg_color=_CARD_BG, border_color=_CARD_BORDER, border_width=1)
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
        row = self._field("slack_monitor_channels", "Monitor Channels", row, placeholder="C01ABC,C02DEF (comma-separated)")

        row = self._section("AI Summary", "\u2728", row)
        row = self._provider_field(row)
        row = self._field("openai_api_key", "API Key", row, show="*")
        row = self._field("ai_model", "Model", row)
        row = self._field("ai_base_url", "Base URL", row, placeholder="Leave empty for OpenAI default")

        row = self._section("Schedule", "\u23F0", row)
        row = self._field("report_hour", "Hour (0-23)", row)
        row = self._field("report_minute", "Minute (0-59)", row)
        row = self._tz_field("timezone", "Timezone", row)

        bf = ctk.CTkFrame(self._scroll, fg_color="transparent")
        bf.grid(row=row, column=0, columnspan=3, pady=(20, 12), sticky="ew")
        bf.grid_columnconfigure(1, weight=1)

        self._save_btn = ctk.CTkButton(bf, text="Save Settings", font=ctk.CTkFont(size=15, weight="bold"), height=44, corner_radius=10, fg_color=_ACCENT, hover_color=("#4f46e5", "#6366f1"), command=self._save)
        self._save_btn.grid(row=0, column=0, padx=(0, 12))

        self._status_label = ctk.CTkLabel(bf, text="", font=ctk.CTkFont(size=13), text_color=_GREEN)
        self._status_label.grid(row=0, column=1, sticky="w")

    # -- Field builders --

    def _section(self, title: str, icon: str, row: int) -> int:
        hf = ctk.CTkFrame(self._scroll, fg_color="transparent")
        hf.grid(row=row, column=0, columnspan=3, sticky="w", pady=(20, 8))
        ctk.CTkLabel(hf, text=f"{icon}  {title}", font=ctk.CTkFont(size=17, weight="bold"), anchor="w").pack(side="left")
        ctk.CTkFrame(self._scroll, height=1, fg_color=_CARD_BORDER).grid(row=row + 1, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        return row + 2

    def _field(self, key: str, label: str, row: int, show: Optional[str] = None, placeholder: str = "") -> int:
        ctk.CTkLabel(self._scroll, text=label, font=ctk.CTkFont(size=13), anchor="w", width=150).grid(row=row, column=0, sticky="w", padx=(12, 6), pady=4)
        entry = ctk.CTkEntry(self._scroll, font=ctk.CTkFont(size=13), height=36, corner_radius=8, border_color=_CARD_BORDER, placeholder_text=placeholder)
        if show:
            entry.configure(show=show)
        entry.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(0, 12), pady=4)
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

    def _field_test(self, key: str, label: str, row: int, test_fn: Callable = lambda: None, show: Optional[str] = None) -> int:
        ctk.CTkLabel(self._scroll, text=label, font=ctk.CTkFont(size=13), anchor="w", width=150).grid(row=row, column=0, sticky="w", padx=(12, 6), pady=4)
        entry = ctk.CTkEntry(self._scroll, font=ctk.CTkFont(size=13), height=36, corner_radius=8, border_color=_CARD_BORDER)
        if show:
            entry.configure(show=show)
        entry.grid(row=row, column=1, sticky="ew", padx=(0, 6), pady=4)
        val = self._config.get(key, "")
        if val:
            entry.insert(0, str(val))
        ctk.CTkButton(self._scroll, text="Test", width=64, height=36, font=ctk.CTkFont(size=12), corner_radius=8, fg_color=("gray80", "gray30"), hover_color=("gray70", "gray38"), text_color=("gray10", "gray90"), command=test_fn).grid(row=row, column=2, padx=(0, 12), pady=4)
        self._entries[key] = entry
        return row + 1

    def _provider_field(self, row: int) -> int:
        """AI provider preset dropdown that auto-fills base URL and model."""
        ctk.CTkLabel(self._scroll, text="Provider", font=ctk.CTkFont(size=13), anchor="w", width=150).grid(row=row, column=0, sticky="w", padx=(12, 6), pady=4)
        cur = str(self._config.get("ai_provider", "Google Gemini (Free)"))
        provider_names = list(_AI_PROVIDERS.keys())
        if cur not in provider_names:
            cur = "Custom"
        self._provider_menu = ctk.CTkOptionMenu(
            self._scroll, values=provider_names, font=ctk.CTkFont(size=13),
            height=36, corner_radius=8, command=self._on_provider_change,
        )
        self._provider_menu.set(cur)
        self._provider_menu.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(0, 12), pady=4)
        self._entries["ai_provider"] = self._provider_menu
        return row + 1

    def _on_provider_change(self, choice: str) -> None:
        """When provider changes, auto-fill base URL and model fields."""
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
        ctk.CTkLabel(self._scroll, text=label, font=ctk.CTkFont(size=13), anchor="w", width=150).grid(row=row, column=0, sticky="w", padx=(12, 6), pady=4)
        cur = str(self._config.get(key, "Asia/Kathmandu"))
        vals = list(_TIMEZONES)
        if cur not in vals:
            vals.insert(0, cur)
        menu = ctk.CTkOptionMenu(self._scroll, values=vals, font=ctk.CTkFont(size=13), height=36, corner_radius=8)
        menu.set(cur)
        menu.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(0, 12), pady=4)
        self._entries[key] = menu
        return row + 1

    # -- Save --

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
        self._status_label.configure(text="\u2705  Settings saved!", text_color=_GREEN)
        self.after(3000, lambda: self._status_label.configure(text=""))

    # -- Import --

    def _import_file(self) -> None:
        fp = filedialog.askopenfilename(title="Select Config File", filetypes=[("Environment files", "*.env"), ("Text files", "*.txt"), ("JSON files", "*.json"), ("All files", "*.*")])
        if not fp:
            return
        path = Path(fp)
        if not path.exists():
            self._status_label.configure(text="\u274C  File not found", text_color=_RED)
            return
        imported = None
        try:
            if path.suffix == ".json":
                imported = self._import_json(path)
            if not imported:
                imported = import_from_dotenv(path)
        except (UnicodeDecodeError, OSError) as e:
            self._status_label.configure(text=f"\u274C  Cannot read file: {type(e).__name__}", text_color=_RED)
            return
        if not imported:
            self._status_label.configure(text="\u274C  Could not parse file", text_color=_RED)
            return
        for key, w in self._entries.items():
            val = imported.get(key, "")
            if isinstance(w, ctk.CTkEntry):
                w.delete(0, "end")
                if val:
                    w.insert(0, str(val))
            elif isinstance(w, ctk.CTkOptionMenu) and val:
                w.set(str(val))
        self._status_label.configure(text=f"\U0001F4C1  Imported from {path.name} \u2014 click Save", text_color=_AMBER)

    @staticmethod
    def _import_json(path: Path) -> Optional[Dict[str, Any]]:
        import json
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, OSError):
            return None

    # -- Tests --

    def _test_github(self) -> None:
        self._status_label.configure(text="Testing GitHub...", text_color=_MUTED)
        threading.Thread(target=self._test_github_bg, daemon=True).start()

    def _test_github_bg(self) -> None:
        try:
            import requests
            tok = self._entries["github_token"].get().strip()
            usr = self._entries["github_username"].get().strip()
            r = requests.get(f"https://api.github.com/users/{usr}", headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}, timeout=10)
            if r.status_code == 200:
                name = r.json().get("name", usr)
                self.after(0, lambda: self._status_label.configure(text=f"\u2705  GitHub OK: {name}", text_color=_GREEN))
            else:
                self.after(0, lambda: self._status_label.configure(text=f"\u274C  GitHub error: {r.status_code}", text_color=_RED))
        except Exception as e:
            self.after(0, lambda: self._status_label.configure(text=f"\u274C  {e}", text_color=_RED))

    def _test_clickup(self) -> None:
        self._status_label.configure(text="Testing ClickUp...", text_color=_MUTED)
        threading.Thread(target=self._test_clickup_bg, daemon=True).start()

    def _test_clickup_bg(self) -> None:
        try:
            import requests
            tok = self._entries["clickup_api_token"].get().strip()
            r = requests.get("https://api.clickup.com/api/v2/user", headers={"Authorization": tok}, timeout=10)
            if r.status_code == 200:
                u = r.json().get("user", {}).get("username", "OK")
                self.after(0, lambda: self._status_label.configure(text=f"\u2705  ClickUp OK: {u}", text_color=_GREEN))
            else:
                self.after(0, lambda: self._status_label.configure(text=f"\u274C  ClickUp error: {r.status_code}", text_color=_RED))
        except Exception as e:
            self.after(0, lambda: self._status_label.configure(text=f"\u274C  {e}", text_color=_RED))

    def _test_slack(self) -> None:
        self._status_label.configure(text="Testing Slack...", text_color=_MUTED)
        threading.Thread(target=self._test_slack_bg, daemon=True).start()

    def _test_slack_bg(self) -> None:
        try:
            from slack_sdk import WebClient
            tok = self._entries["slack_bot_token"].get().strip()
            resp = WebClient(token=tok).auth_test()
            team = resp.get("team", "")
            self.after(0, lambda: self._status_label.configure(text=f"\u2705  Slack OK: {team}", text_color=_GREEN))
        except Exception as e:
            self.after(0, lambda: self._status_label.configure(text=f"\u274C  {e}", text_color=_RED))
