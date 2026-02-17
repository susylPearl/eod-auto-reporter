"""
Activity View — today's GitHub, ClickUp & Slack activity.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk

from desktop.utils import FixedScrollableFrame, bind_mousewheel_to_scroll

from app.models.activity_models import (
    ClickUpActivity,
    ClickUpTask,
    GitHubActivity,
    GitHubCommit,
    GitHubPR,
    SlackChannelActivity,
    SlackMessage,
)

_CARD_BG = ("#ffffff", "#1e1f2e")
_CARD_BORDER = ("#e5e7eb", "#2d2f3d")
_MUTED = ("#6b7280", "#8b8d97")
_ACCENT = ("#6366f1", "#818cf8")
_GREEN = ("#15803d", "#4ade80")
_AMBER = ("#b45309", "#fbbf24")
_BLUE = ("#1e40af", "#60a5fa")
_SLACK_BG = ("#eff6ff", "#1e2a3d")
_SLACK_BORDER = ("#93c5fd", "#3b6fa8")
_BAR_TEXT = ("#111827", "#111827")


class ActivityView(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, config: Dict[str, Any], on_config_change: Optional[Any] = None) -> None:
        super().__init__(parent, fg_color="transparent")
        self._config = dict(config)
        self._on_config_change = on_config_change
        self._is_fetching = False
        self._is_sending = False
        self._manual_updates: List[str] = [
            str(x).strip() for x in self._config.get("manual_updates", []) if str(x).strip()
        ]

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build_ui()
        # Auto-fetch once on startup so Activity has fresh data without manual refresh.
        self.after(250, self._refresh)

    def update_config(self, config: Dict[str, Any]) -> None:
        self._config = dict(config)
        self._show_github_var.set(bool(config.get("show_github", True)))
        self._show_clickup_var.set(bool(config.get("show_clickup", True)))
        self._show_slack_var.set(bool(config.get("show_slack", True)))
        self._show_manual_var.set(bool(config.get("show_manual", True)))
        order = str(config.get("activity_section_order", "github_first"))
        mapping = {
            "github_first": "GitHub first",
            "clickup_first": "ClickUp first",
            "slack_first": "Slack first",
            "manual_first": "Manual first",
        }
        self._order_var.set(mapping.get(order, "GitHub first"))
        self._max_entry.delete(0, "end")
        self._max_entry.insert(0, str(config.get("max_commits_per_repo", 10)))
        self._manual_updates = [str(x).strip() for x in config.get("manual_updates", []) if str(x).strip()]
        self._render_manual_chips()

    def _build_ui(self) -> None:
        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        hdr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(hdr, text="Today's Activity", font=ctk.CTkFont(size=28, weight="bold"), anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(hdr, text="GitHub, ClickUp, Slack and manual updates", font=ctk.CTkFont(size=13), text_color=_MUTED, anchor="w").grid(row=1, column=0, sticky="w", pady=(2, 0))
        action_box = ctk.CTkFrame(hdr, fg_color="transparent")
        action_box.grid(row=0, column=1, rowspan=2, sticky="e")

        self._refresh_btn = ctk.CTkButton(
            action_box,
            text="\u21BB  Refresh",
            width=104,
            height=36,
            font=ctk.CTkFont(size=13),
            corner_radius=10,
            fg_color=_ACCENT,
            hover_color=("#4f46e5", "#6366f1"),
            command=self._refresh,
        )
        self._refresh_btn.pack(side="left", padx=(0, 8))

        self._send_btn = ctk.CTkButton(
            action_box,
            text="\u25B6  Send EOD Now",
            width=138,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=10,
            fg_color=_ACCENT,
            hover_color=("#4f46e5", "#6366f1"),
            command=self._send_now,
        )
        self._send_btn.pack(side="left")

        # Filters + manual updates editor
        opts_card = ctk.CTkFrame(
            self,
            corner_radius=14,
            fg_color=("#ffffff", "#1f2233"),
            border_color=("#c4b5fd", "#4c3f88"),
            border_width=1,
        )
        opts_card.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        opts = ctk.CTkFrame(opts_card, fg_color="transparent")
        opts.pack(fill="x", padx=12, pady=(11, 9))

        self._show_github_var = tk.BooleanVar(value=bool(self._config.get("show_github", True)))
        self._show_clickup_var = tk.BooleanVar(value=bool(self._config.get("show_clickup", True)))
        self._show_slack_var = tk.BooleanVar(value=bool(self._config.get("show_slack", True)))
        self._show_manual_var = tk.BooleanVar(value=bool(self._config.get("show_manual", True)))

        ctk.CTkLabel(opts, text="Tune feed", font=ctk.CTkFont(size=12, weight="bold"), text_color=_BAR_TEXT).pack(side="left", padx=(0, 6))

        source_items = [
            ("GitHub", self._show_github_var),
            ("ClickUp", self._show_clickup_var),
            ("Slack", self._show_slack_var),
            ("Manual", self._show_manual_var),
        ]
        for text, var in source_items:
            chk = ttk.Checkbutton(opts, text=text, variable=var, command=self._save_prefs)
            chk.pack(side="left", padx=(0, 6))

        order = str(self._config.get("activity_section_order", "github_first"))
        self._order_var = tk.StringVar()
        self._order_menu = ttk.Combobox(
            opts,
            textvariable=self._order_var,
            values=["ClickUp first", "GitHub first", "Slack first", "Manual first"],
            state="readonly",
            width=14,
        )
        order_label = {
            "clickup_first": "ClickUp first",
            "github_first": "GitHub first",
            "slack_first": "Slack first",
            "manual_first": "Manual first",
        }.get(order, "GitHub first")
        self._order_var.set(order_label)
        self._order_menu.bind("<<ComboboxSelected>>", lambda _e: self._save_prefs())
        self._order_menu.pack(side="left", padx=(4, 6))

        ctk.CTkLabel(opts, text="Max/repo:", font=ctk.CTkFont(size=11), text_color=_BAR_TEXT).pack(side="left", padx=(0, 3))
        self._max_entry = ctk.CTkEntry(
            opts,
            width=48,
            height=30,
            corner_radius=8,
            font=ctk.CTkFont(size=11),
            text_color=_BAR_TEXT,
            fg_color=("#ffffff", "#ffffff"),
        )
        self._max_entry.insert(0, str(self._config.get("max_commits_per_repo", 10)))
        self._max_entry.pack(side="left")
        self._max_entry.bind("<FocusOut>", lambda _e: self._save_prefs())

        manual_row = ctk.CTkFrame(opts_card, fg_color="transparent")
        manual_row.pack(fill="x", padx=12, pady=(3, 10))
        ctk.CTkLabel(
            manual_row,
            text="\U0001F4DD  Add manual update",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=_BAR_TEXT,
        ).pack(side="left", padx=(0, 6))

        self._manual_entry = ctk.CTkEntry(
            manual_row,
            height=32,
            corner_radius=8,
            font=ctk.CTkFont(size=12),
            placeholder_text="Add extra update (e.g. Design sync done, blocked by API review)",
            text_color=_BAR_TEXT,
            fg_color=("#ffffff", "#ffffff"),
        )
        self._manual_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._manual_entry.bind("<Return>", lambda _e: self._add_manual_update())

        ctk.CTkButton(
            manual_row,
            text="+ Add",
            width=72,
            height=32,
            corner_radius=8,
            fg_color=_ACCENT,
            hover_color=("#4f46e5", "#6366f1"),
            command=self._add_manual_update,
        ).pack(side="left")

        self._manual_chips = ctk.CTkFrame(opts_card, fg_color="transparent")
        self._manual_chips.pack(fill="x", padx=12, pady=(0, 10))
        self._render_manual_chips()

        # Scroll area
        self._scroll = FixedScrollableFrame(self, corner_radius=14, fg_color=_CARD_BG, border_color=_CARD_BORDER, border_width=1)
        self._scroll.grid(row=2, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)
        bind_mousewheel_to_scroll(self._scroll)

        ctk.CTkLabel(self._scroll, text="Click Refresh to load today's activity", font=ctk.CTkFont(size=14), text_color=_MUTED).grid(row=0, column=0, pady=50)

    # -- Refresh --

    def _refresh(self) -> None:
        if self._is_fetching:
            return
        self._is_fetching = True
        self._refresh_btn.configure(state="disabled", text="\u21BB  Loading...")
        threading.Thread(target=self._fetch_bg, daemon=True).start()

    def _send_now(self) -> None:
        if self._is_sending:
            return
        self._is_sending = True
        self._send_btn.configure(state="disabled", text="\u25B6  Sending...")
        threading.Thread(target=self._send_now_bg, daemon=True).start()

    def _send_now_bg(self) -> None:
        try:
            from app.scheduler import run_eod_pipeline
            run_eod_pipeline()
            self.after(0, self._on_send_done, True)
        except Exception:
            self.after(0, self._on_send_done, False)

    def _on_send_done(self, ok: bool) -> None:
        self._is_sending = False
        self._send_btn.configure(state="normal", text="\u25B6  Send EOD Now")
        if ok:
            # Refresh feed after successful send to keep UI current.
            self._refresh()

    def _fetch_bg(self) -> None:
        gh: Optional[GitHubActivity] = None
        cu: Optional[ClickUpActivity] = None
        slack: Optional[SlackChannelActivity] = None

        try:
            from app.services import github_service
            gh = github_service.fetch_github_activity()
        except Exception:
            pass
        try:
            from app.services import clickup_service
            cu = clickup_service.fetch_clickup_activity()
        except Exception:
            pass

        # Slack public channels
        channels = self._config.get("slack_monitor_channels", "")
        if channels:
            try:
                from app.services.slack_activity_service import fetch_slack_channel_activity
                slack = fetch_slack_channel_activity(channels)
            except Exception:
                pass

        self.after(0, self._render, gh, cu, slack)

    def _read_filters(self) -> Dict[str, Any]:
        try:
            mc = int(self._max_entry.get().strip() or "10")
        except ValueError:
            mc = 10
        order = {
            "ClickUp first": "clickup_first",
            "GitHub first": "github_first",
            "Slack first": "slack_first",
            "Manual first": "manual_first",
        }.get(self._order_menu.get(), "github_first")
        self._config["show_github"] = self._show_github_var.get()
        self._config["show_clickup"] = self._show_clickup_var.get()
        self._config["show_slack"] = self._show_slack_var.get()
        self._config["show_manual"] = self._show_manual_var.get()
        self._config["activity_section_order"] = order
        self._config["max_commits_per_repo"] = mc
        self._config["manual_updates"] = list(self._manual_updates)
        return self._config

    def _save_prefs(self) -> None:
        cfg = self._read_filters()
        if self._on_config_change:
            self._on_config_change(cfg)

    def _add_manual_update(self) -> None:
        text = self._manual_entry.get().strip()
        if not text:
            return
        if len(text) > 240:
            text = text[:239].rstrip() + "…"
        self._manual_updates.append(text)
        self._manual_entry.delete(0, "end")
        self._render_manual_chips()
        self._save_prefs()

    def _remove_manual_update(self, idx: int) -> None:
        if 0 <= idx < len(self._manual_updates):
            self._manual_updates.pop(idx)
            self._render_manual_chips()
            self._save_prefs()

    def _render_manual_chips(self) -> None:
        for w in self._manual_chips.winfo_children():
            w.destroy()

        if not self._manual_updates:
            ctk.CTkLabel(
                self._manual_chips,
                text="No manual updates added yet.",
                font=ctk.CTkFont(size=11),
                text_color=_MUTED,
                anchor="w",
            ).pack(side="left")
            return

        for idx, item in enumerate(self._manual_updates):
            chip = ctk.CTkFrame(self._manual_chips, corner_radius=10, fg_color=("#eef2ff", "#2a2d45"))
            chip.pack(fill="x", pady=3)
            ctk.CTkLabel(
                chip,
                text=f"• {item}",
                font=ctk.CTkFont(size=12),
                anchor="w",
                justify="left",
                wraplength=620,
            ).pack(side="left", fill="x", expand=True, padx=(10, 6), pady=6)
            ctk.CTkButton(
                chip,
                text="✕",
                width=24,
                height=24,
                corner_radius=8,
                fg_color="transparent",
                hover_color=("#e5e7eb", "#3a3d50"),
                command=lambda i=idx: self._remove_manual_update(i),
            ).pack(side="right", padx=(0, 6))

    def _render(self, gh: Optional[GitHubActivity], cu: Optional[ClickUpActivity], slack: Optional[SlackChannelActivity]) -> None:
        cfg = self._read_filters()
        if self._on_config_change:
            self._on_config_change(cfg)

        for w in self._scroll.winfo_children():
            w.destroy()

        row = 0

        # Build sections
        sections: list[tuple] = []
        if cfg.get("show_github", True) and gh:
            sections.append(("gh", gh))
        if cfg.get("show_clickup", True) and cu:
            sections.append(("cu", cu))
        if cfg.get("show_slack", True) and slack and slack.messages:
            sections.append(("slack", slack))
        elif cfg.get("show_slack", True) and not self._config.get("slack_monitor_channels"):
            sections.append(("slack_hint", None))
        if cfg.get("show_manual", True) and self._manual_updates:
            sections.append(("manual", list(self._manual_updates)))

        order_key = str(cfg.get("activity_section_order", "github_first"))
        order_map = {
            "clickup_first": ["cu", "gh", "slack", "manual", "slack_hint"],
            "github_first": ["gh", "cu", "slack", "manual", "slack_hint"],
            "slack_first": ["slack", "gh", "cu", "manual", "slack_hint"],
            "manual_first": ["manual", "cu", "gh", "slack", "slack_hint"],
        }
        rank = {k: i for i, k in enumerate(order_map.get(order_key, order_map["github_first"]))}
        sections.sort(key=lambda x: rank.get(x[0], 99))

        mc = int(cfg.get("max_commits_per_repo", 10))

        for i, (kind, data) in enumerate(sections):
            if i > 0:
                ctk.CTkFrame(self._scroll, height=1, fg_color=_CARD_BORDER).grid(row=row, column=0, sticky="ew", pady=14)
                row += 1
            if kind == "gh":
                row = self._render_github(data, row, mc)
            elif kind == "cu":
                row = self._render_clickup(data, row)
            elif kind == "slack":
                row = self._render_slack(data, row)
            elif kind == "manual":
                row = self._render_manual(data, row)
            elif kind == "slack_hint":
                row = self._render_hint(
                    "\U0001F4AC  Slack Discussions",
                    "Add Slack channel IDs in Settings \u2192 Slack \u2192 Monitor Channels to see discussions here.",
                    _SLACK_BG, _SLACK_BORDER, row,
                )

        if not sections:
            ctk.CTkLabel(self._scroll, text="No activity found for today", font=ctk.CTkFont(size=14), text_color=_MUTED).grid(row=row, column=0, pady=50)

        self._refresh_btn.configure(state="normal", text="\u21BB  Refresh")
        self._is_fetching = False
        bind_mousewheel_to_scroll(self._scroll)

    # -- Hints for unconfigured features --

    def _render_hint(self, title: str, msg: str, bg: Any, border: Any, row: int) -> int:
        card = ctk.CTkFrame(self._scroll, corner_radius=12, fg_color=bg, border_color=border, border_width=1)
        card.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=14, weight="bold"), text_color=_MUTED, anchor="w").pack(fill="x", padx=16, pady=(12, 2))
        ctk.CTkLabel(card, text=msg, font=ctk.CTkFont(size=12), text_color=_MUTED, anchor="w", justify="left", wraplength=600).pack(fill="x", padx=16, pady=(0, 12))
        return row + 1

    # -- GitHub --

    def _render_github(self, gh: GitHubActivity, row: int, mc: int) -> int:
        ctk.CTkLabel(self._scroll, text="\U0001F4BB  GitHub", font=ctk.CTkFont(size=20, weight="bold"), anchor="w").grid(row=row, column=0, sticky="w", pady=(0, 8))
        row += 1

        if not gh.commits and not gh.prs_opened and not gh.prs_merged:
            ctk.CTkLabel(self._scroll, text="  No GitHub activity today", font=ctk.CTkFont(size=13), text_color=_MUTED, anchor="w").grid(row=row, column=0, sticky="w", padx=8)
            return row + 1

        if gh.commits:
            ctk.CTkLabel(self._scroll, text=f"  Commits ({len(gh.commits)})", font=ctk.CTkFont(size=15, weight="bold"), anchor="w").grid(row=row, column=0, sticky="w", padx=8, pady=(6, 4))
            row += 1
            by_repo: Dict[str, List[GitHubCommit]] = {}
            for c in gh.commits:
                by_repo.setdefault(c.repo.split("/")[-1], []).append(c)
            for repo, commits in by_repo.items():
                ctk.CTkLabel(self._scroll, text=f"    {repo}", font=ctk.CTkFont(size=13, weight="bold"), text_color=_BLUE, anchor="w").grid(row=row, column=0, sticky="w", padx=12, pady=(4, 0))
                row += 1
                for c in commits[:mc]:
                    msg = c.message[:90] + ("..." if len(c.message) > 90 else "")
                    ctk.CTkLabel(self._scroll, text=f"      \u2022 {msg}", font=ctk.CTkFont(size=13), anchor="w", wraplength=600, justify="left").grid(row=row, column=0, sticky="w", padx=16, pady=1)
                    row += 1

        if gh.prs_opened:
            ctk.CTkLabel(self._scroll, text=f"  PRs Opened ({len(gh.prs_opened)})", font=ctk.CTkFont(size=15, weight="bold"), anchor="w").grid(row=row, column=0, sticky="w", padx=8, pady=(10, 4))
            row += 1
            for pr in gh.prs_opened:
                color = ("#2563eb", "#60a5fa")
                ctk.CTkLabel(self._scroll, text=f"      \u2022 [{pr.repo.split('/')[-1]}] {pr.title}", font=ctk.CTkFont(size=13), text_color=color, anchor="w", wraplength=600, justify="left").grid(row=row, column=0, sticky="w", padx=16, pady=1)
                row += 1

        if gh.prs_merged:
            ctk.CTkLabel(self._scroll, text=f"  PRs Merged ({len(gh.prs_merged)})", font=ctk.CTkFont(size=15, weight="bold"), anchor="w").grid(row=row, column=0, sticky="w", padx=8, pady=(10, 4))
            row += 1
            for pr in gh.prs_merged:
                ctk.CTkLabel(self._scroll, text=f"      \u2022 [{pr.repo.split('/')[-1]}] {pr.title}", font=ctk.CTkFont(size=13), text_color=_GREEN, anchor="w", wraplength=600, justify="left").grid(row=row, column=0, sticky="w", padx=16, pady=1)
                row += 1
        return row

    # -- ClickUp --

    def _render_clickup(self, cu: ClickUpActivity, row: int) -> int:
        ctk.CTkLabel(self._scroll, text="\u2611  ClickUp", font=ctk.CTkFont(size=20, weight="bold"), anchor="w").grid(row=row, column=0, sticky="w", pady=(0, 8))
        row += 1

        if not cu.tasks_completed and not cu.status_changes and not cu.comments:
            ctk.CTkLabel(self._scroll, text="  No ClickUp activity today", font=ctk.CTkFont(size=13), text_color=_MUTED, anchor="w").grid(row=row, column=0, sticky="w", padx=8)
            return row + 1

        if cu.tasks_completed:
            ctk.CTkLabel(self._scroll, text=f"  Completed ({len(cu.tasks_completed)})", font=ctk.CTkFont(size=15, weight="bold"), text_color=_GREEN, anchor="w").grid(row=row, column=0, sticky="w", padx=8, pady=(6, 4))
            row += 1
            row = self._tasks_hierarchy(cu.tasks_completed, cu.tasks_updated, row)

        if cu.status_changes:
            ctk.CTkLabel(self._scroll, text=f"  In Progress ({len(cu.status_changes)})", font=ctk.CTkFont(size=15, weight="bold"), text_color=_AMBER, anchor="w").grid(row=row, column=0, sticky="w", padx=8, pady=(10, 4))
            row += 1
            row = self._tasks_hierarchy(cu.status_changes, cu.tasks_updated, row)

        if cu.comments:
            ctk.CTkLabel(self._scroll, text=f"  Comments ({len(cu.comments)})", font=ctk.CTkFont(size=15, weight="bold"), anchor="w").grid(row=row, column=0, sticky="w", padx=8, pady=(10, 4))
            row += 1
            for c in cu.comments[:10]:
                snip = c.comment_text[:80] + ("..." if len(c.comment_text) > 80 else "")
                ctk.CTkLabel(self._scroll, text=f"      \u2022 {c.task_name}: {snip}", font=ctk.CTkFont(size=13), anchor="w", wraplength=600, justify="left").grid(row=row, column=0, sticky="w", padx=16, pady=1)
                row += 1
        return row

    def _tasks_hierarchy(self, tasks: List[ClickUpTask], all_tasks: List[ClickUpTask], row: int) -> int:
        task_map = {t.task_id: t for t in all_tasks}
        rendered: set[str] = set()
        children_map: Dict[str, List[ClickUpTask]] = {}
        top: List[ClickUpTask] = []
        for t in tasks:
            if t.parent_id and t.parent_id in task_map:
                children_map.setdefault(t.parent_id, []).append(t)
            else:
                top.append(t)
        for t in top:
            if t.task_id in rendered:
                continue
            badge = self._badge(t.status)
            ctk.CTkLabel(self._scroll, text=f"      \u2022 {t.name}  {badge}", font=ctk.CTkFont(size=13), anchor="w", wraplength=600, justify="left").grid(row=row, column=0, sticky="w", padx=16, pady=1)
            rendered.add(t.task_id)
            row += 1
            for ch in children_map.get(t.task_id, []):
                if ch.task_id in rendered:
                    continue
                ctk.CTkLabel(self._scroll, text=f"          \u25e6 {ch.name}  {self._badge(ch.status)}", font=ctk.CTkFont(size=12), text_color=("gray30", "gray70"), anchor="w", wraplength=580, justify="left").grid(row=row, column=0, sticky="w", padx=24, pady=1)
                rendered.add(ch.task_id)
                row += 1
        return row

    @staticmethod
    def _badge(status: str) -> str:
        s = status.lower()
        if s in ("complete", "closed", "done", "resolved"):
            return "[done]"
        if s in ("in progress", "in development"):
            return "[wip]"
        if s in ("in review", "review", "qa", "testing", "dev-test", "ready for review"):
            return "[review]"
        return ""

    # -- Manual --

    def _render_manual(self, updates: List[str], row: int) -> int:
        card = ctk.CTkFrame(self._scroll, corner_radius=12, fg_color=("#f8fafc", "#212534"), border_color=_CARD_BORDER, border_width=1)
        card.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="\U0001F4DD  Manual Updates",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(14, 6))

        for text in updates[:20]:
            clean = " ".join(str(text).split()).strip()
            if not clean:
                continue
            if len(clean) > 180:
                clean = clean[:179].rstrip() + "..."
            ctk.CTkLabel(
                card,
                text=f"  • {clean}",
                font=ctk.CTkFont(size=12),
                anchor="w",
                justify="left",
                wraplength=610,
            ).pack(fill="x", padx=16, pady=1)

        ctk.CTkFrame(card, height=10, fg_color="transparent").pack()
        return row + 1

    # -- Slack --

    def _render_slack(self, slack: SlackChannelActivity, row: int) -> int:
        card = ctk.CTkFrame(self._scroll, corner_radius=12, fg_color=_SLACK_BG, border_color=_SLACK_BORDER, border_width=1)
        card.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="\U0001F4AC  Slack Discussions", font=ctk.CTkFont(size=16, weight="bold"), anchor="w").pack(fill="x", padx=16, pady=(14, 6))

        # Group by channel
        by_ch: Dict[str, List[SlackMessage]] = {}
        for m in slack.messages:
            by_ch.setdefault(m.channel_name or m.channel_id, []).append(m)

        for ch_name, msgs in by_ch.items():
            ctk.CTkLabel(card, text=f"#{ch_name} ({len(msgs)} messages)", font=ctk.CTkFont(size=14, weight="bold"), text_color=_BLUE, anchor="w").pack(fill="x", padx=16, pady=(6, 2))

            for m in msgs[:15]:
                snip = m.text[:120] + ("..." if len(m.text) > 120 else "")
                ts = m.timestamp.strftime("%H:%M") if m.timestamp else ""
                ctk.CTkLabel(card, text=f"  {ts}  {m.user_name}: {snip}", font=ctk.CTkFont(size=12), anchor="w", wraplength=600, justify="left").pack(fill="x", padx=20, pady=1)

            if len(msgs) > 15:
                ctk.CTkLabel(card, text=f"  ... and {len(msgs) - 15} more messages", font=ctk.CTkFont(size=12), text_color=_MUTED, anchor="w").pack(fill="x", padx=20, pady=2)

        ctk.CTkFrame(card, height=10, fg_color="transparent").pack()
        return row + 1
