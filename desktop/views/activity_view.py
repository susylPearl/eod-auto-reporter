"""
Activity View — today's GitHub, ClickUp & Slack activity with Material Design 3.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

import customtkinter as ctk
import tkinter as tk

from desktop.utils import FixedScrollableFrame, bind_mousewheel_to_scroll
from desktop import theme as T

from app.models.activity_models import (
    ClickUpActivity,
    ClickUpTask,
    GitHubActivity,
    GitHubCommit,
    GitHubPR,
    SlackChannelActivity,
    SlackMessage,
)

logger = logging.getLogger(__name__)


class ActivityView(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, config: Dict[str, Any],
                 on_config_change: Optional[Any] = None) -> None:
        super().__init__(parent, fg_color="transparent")
        self._config = dict(config)
        self._on_config_change = on_config_change
        self._is_fetching = False
        self._is_sending = False
        self._manual_updates: List[str] = [
            str(x).strip() for x in self._config.get("manual_updates", []) if str(x).strip()
        ]
        self._last_gh: Optional[GitHubActivity] = None
        self._last_cu: Optional[ClickUpActivity] = None
        self._last_slack: Optional[SlackChannelActivity] = None
        self._last_slack_summaries: Dict[str, str] = {}
        self._last_slack_error: str = ""

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build_ui()
        self.after(250, self._refresh)

    # ── External config update ────────────────────────────────────────

    def update_config(self, config: Dict[str, Any]) -> None:
        self._config = dict(config)
        for key, var in self._filter_vars.items():
            var.set(bool(config.get(f"show_{key}", True)))
            btn = self._filter_chip_btns.get(key)
            if btn:
                on = var.get()
                btn.configure(
                    fg_color=T.PRIMARY if on else "transparent",
                    text_color=T.ON_PRIMARY if on else T.ON_SURFACE_VARIANT,
                    border_color=T.PRIMARY if on else T.OUTLINE,
                )
        order = str(config.get("activity_section_order", "github_first"))
        order_label = _ORDER_MAP_REV.get(order, "GitHub first")
        self._order_menu.set(order_label)
        self._max_entry.delete(0, "end")
        self._max_entry.insert(0, str(config.get("max_commits_per_repo", 10)))
        self._manual_updates = [str(x).strip() for x in config.get("manual_updates", []) if str(x).strip()]
        self._render_manual_chips()

    # ── Build UI ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # ── Row 0: Header bar with title + action buttons ─────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(hdr, text="Today's Activity", font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=T.ON_SURFACE, anchor="w").grid(row=0, column=0, sticky="w")

        btn_box = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_box.grid(row=0, column=1, sticky="e")

        self._refresh_btn = T.m3_tonal_button(btn_box, text="\u21BB  Refresh   ",
                                              command=self._refresh, width=130)
        self._refresh_btn.pack(side="left", padx=(0, 6))

        self._send_btn = T.m3_filled_button(btn_box, text="\u25B6  Send EOD  ",
                                            command=self._send_now, width=130)
        self._send_btn.pack(side="left")

        # ── Row 1: Toolbar — filters + sort ───────────────────────────
        toolbar = T.m3_filled_card(self)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 4))

        tb_row1 = ctk.CTkFrame(toolbar, fg_color="transparent")
        tb_row1.pack(fill="x", padx=10, pady=(8, 4))

        # Filter chips
        self._filter_vars: Dict[str, tk.BooleanVar] = {}
        self._filter_chip_btns: Dict[str, ctk.CTkButton] = {}
        chip_items = [
            ("GitHub", "github"),
            ("ClickUp", "clickup"),
            ("Slack", "slack"),
            ("Manual", "manual"),
        ]
        for label, key in chip_items:
            var = tk.BooleanVar(value=bool(self._config.get(f"show_{key}", True)))
            self._filter_vars[key] = var
            on = var.get()
            btn = ctk.CTkButton(
                tb_row1, text=label, height=30, corner_radius=15,
                font=ctk.CTkFont(size=12),
                fg_color=T.PRIMARY if on else "transparent",
                text_color=T.ON_PRIMARY if on else T.ON_SURFACE_VARIANT,
                hover_color=T.PRIMARY_CONTAINER,
                border_width=1,
                border_color=T.PRIMARY if on else T.OUTLINE,
                command=lambda k=key: self._toggle_chip(k),
            )
            btn.pack(side="left", padx=(0, 4))
            self._filter_chip_btns[key] = btn

        _vsep(tb_row1)

        # Sort
        ctk.CTkLabel(tb_row1, text="Sort", font=ctk.CTkFont(size=11),
                     text_color=T.MUTED).pack(side="left", padx=(0, 4))
        order = str(self._config.get("activity_section_order", "github_first"))
        self._order_menu = ctk.CTkOptionMenu(
            tb_row1, values=list(_ORDER_MAP.keys()),
            font=ctk.CTkFont(size=11), height=30, width=125, corner_radius=8,
            fg_color=T.SURFACE_CONTAINER_HIGH, button_color=T.OUTLINE_VARIANT,
            button_hover_color=T.SURFACE_CONTAINER_HIGHEST,
            text_color=T.ON_SURFACE, dropdown_fg_color=T.SURFACE_CONTAINER,
            dropdown_text_color=T.ON_SURFACE,
            dropdown_hover_color=T.SURFACE_CONTAINER_HIGH,
            command=lambda _v: self._on_filter_change(),
        )
        self._order_menu.set(_ORDER_MAP_REV.get(order, "GitHub first"))
        self._order_menu.pack(side="left", padx=(0, 4))

        self._max_entry = ctk.CTkEntry(
            tb_row1, width=38, height=30, corner_radius=8,
            font=ctk.CTkFont(size=11), justify="center",
            text_color=T.ON_SURFACE, fg_color=T.SURFACE_CONTAINER_HIGH,
            border_color=T.OUTLINE_VARIANT, border_width=1, placeholder_text="10",
        )
        self._max_entry.insert(0, str(self._config.get("max_commits_per_repo", 10)))
        self._max_entry.pack(side="left")
        self._max_entry.bind("<FocusOut>", lambda _e: self._on_filter_change())
        self._max_entry.bind("<Return>", lambda _e: self._on_filter_change())

        # ── Row 2 inside toolbar: Manual update input ─────────────────
        tb_row2 = ctk.CTkFrame(toolbar, fg_color="transparent")
        tb_row2.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkLabel(tb_row2, text="Manual:", font=ctk.CTkFont(size=11),
                     text_color=T.MUTED).pack(side="left", padx=(0, 4))

        self._manual_entry = T.m3_text_field(
            tb_row2, height=30, corner_radius=8,
            placeholder_text="Add manual update...",
        )
        self._manual_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._manual_entry.bind("<Return>", lambda _e: self._add_manual_update())

        self._add_btn = T.m3_filled_button(tb_row2, text="+ Add", width=70,
                                           height=30, corner_radius=8,
                                           command=self._add_manual_update)
        self._add_btn.pack(side="left")

        # ── Row 3 inside toolbar: Manual chips (shown only when non-empty)
        self._manual_chips_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        self._render_manual_chips()

        # ── Row 2: Scrollable activity feed ───────────────────────────
        self._scroll = FixedScrollableFrame(
            self, corner_radius=12, fg_color=T.CARD_BG,
            border_color=T.CARD_BORDER, border_width=1,
        )
        self._scroll.grid(row=2, column=0, sticky="nsew", pady=(2, 0))
        self._scroll.grid_columnconfigure(0, weight=1)
        bind_mousewheel_to_scroll(self._scroll)

        ctk.CTkLabel(self._scroll, text="Loading activity...",
                     font=ctk.CTkFont(size=14), text_color=T.MUTED
                     ).grid(row=0, column=0, pady=40)

    # ── Refresh / Send ────────────────────────────────────────────────

    def _refresh(self) -> None:
        if self._is_fetching:
            return
        self._is_fetching = True
        self._refresh_btn.configure(state="disabled")
        self._send_btn.configure(state="disabled")
        self._refresh_dot_count = 0
        self._animate_refresh_dots()
        threading.Thread(target=self._fetch_bg, daemon=True).start()

    def _animate_refresh_dots(self) -> None:
        if not self._is_fetching:
            return
        self._refresh_dot_count = (self._refresh_dot_count % 3) + 1
        dots = ("." * self._refresh_dot_count).ljust(3)
        self._refresh_btn.configure(text=f"\u21BB  Loading{dots} ")
        self._refresh_dot_job = self.after(350, self._animate_refresh_dots)

    def _send_now(self) -> None:
        if self._is_sending:
            return
        self._is_sending = True
        self._refresh_btn.configure(state="disabled")
        self._send_btn.configure(state="disabled")
        self._send_dot_count = 0
        self._animate_send_dots()
        threading.Thread(target=self._send_now_bg, daemon=True).start()

    def _animate_send_dots(self) -> None:
        if not self._is_sending:
            return
        self._send_dot_count = (self._send_dot_count % 3) + 1
        dots = ("." * self._send_dot_count).ljust(3)
        self._send_btn.configure(text=f"\u25B6  Sending{dots} ")
        self._send_dot_job = self.after(350, self._animate_send_dots)

    def _send_now_bg(self) -> None:
        try:
            from app.scheduler import run_eod_pipeline
            run_eod_pipeline()
            self.after(0, self._on_send_done, True)
        except Exception:
            self.after(0, self._on_send_done, False)

    def _on_send_done(self, ok: bool) -> None:
        self._is_sending = False
        if getattr(self, "_send_dot_job", None):
            self.after_cancel(self._send_dot_job)
            self._send_dot_job = None
        self._refresh_btn.configure(state="normal")
        self._send_btn.configure(state="normal", text="\u25B6  Send EOD  ")
        if ok:
            self._refresh()

    # ── Fetch ─────────────────────────────────────────────────────────

    def _fetch_bg(self) -> None:
        gh: Optional[GitHubActivity] = None
        cu: Optional[ClickUpActivity] = None
        slack: Optional[SlackChannelActivity] = None
        slack_summaries: Dict[str, str] = {}

        try:
            from app.services import github_service
            gh = github_service.fetch_github_activity()
            logger.info("Activity: GitHub — %d commits, %d PRs",
                        len(gh.commits) if gh else 0, len(gh.prs_opened) if gh else 0)
        except Exception as exc:
            logger.exception("Activity: GitHub fetch failed: %s", exc)
        try:
            from app.services import clickup_service
            cu = clickup_service.fetch_clickup_activity()
            logger.info("Activity: ClickUp — %d tasks", len(cu.tasks_updated) if cu else 0)
        except Exception as exc:
            logger.exception("Activity: ClickUp fetch failed: %s", exc)

        channels = self._config.get("slack_monitor_channels", "")
        slack_error = ""
        if channels:
            try:
                from app.services.slack_activity_service import fetch_slack_channel_activity
                slack = fetch_slack_channel_activity(channels)
                msg_count = len(slack.messages) if slack else 0
                logger.info("Activity: Slack — %d messages from channels: %s", msg_count, channels)
                if msg_count == 0:
                    slack_error = "No messages found. Channels may be invalid, bot may not be a member, or no messages today."
            except Exception as exc:
                logger.exception("Activity: Slack fetch failed: %s", exc)
                slack_error = f"Fetch error: {str(exc)[:100]}"

            api_key = str(self._config.get("openai_api_key", ""))
            base_url = str(self._config.get("ai_base_url", "")).strip()
            if not base_url and "gemini" in str(self._config.get("ai_model", "")).lower():
                base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
            if slack and slack.messages and api_key:
                try:
                    from app.services.ai_summary_service import summarize_slack_channels
                    slack_summaries = summarize_slack_channels(
                        slack,
                        api_key=api_key,
                        model=str(self._config.get("ai_model", "gemini-2.0-flash")),
                        base_url=base_url,
                    )
                    logger.info("Activity: AI summaries generated for %d channels", len(slack_summaries))
                except Exception as exc:
                    logger.exception("Activity: AI summary failed: %s", exc)
            elif slack and slack.messages and not api_key:
                logger.info("Activity: No AI API key — skipping Slack summarization")

        self.after(0, self._render, gh, cu, slack, slack_summaries, slack_error)

    # ── Filters ───────────────────────────────────────────────────────

    def _read_filters(self) -> Dict[str, Any]:
        try:
            mc = int(self._max_entry.get().strip() or "10")
        except ValueError:
            mc = 10
        current_order = self._order_menu.get()
        order = _ORDER_MAP.get(current_order, "github_first")
        for key, var in self._filter_vars.items():
            self._config[f"show_{key}"] = var.get()
        self._config["activity_section_order"] = order
        self._config["max_commits_per_repo"] = mc
        self._config["manual_updates"] = list(self._manual_updates)
        return self._config

    def _toggle_chip(self, key: str) -> None:
        var = self._filter_vars[key]
        var.set(not var.get())
        btn = self._filter_chip_btns.get(key)
        if btn:
            on = var.get()
            btn.configure(
                fg_color=T.PRIMARY if on else "transparent",
                text_color=T.ON_PRIMARY if on else T.ON_SURFACE_VARIANT,
                border_color=T.PRIMARY if on else T.OUTLINE,
            )
        self._on_filter_change()

    def _on_filter_change(self) -> None:
        self._save_prefs()
        if any(v is not None for v in (self._last_gh, self._last_cu, self._last_slack)):
            self._render(self._last_gh, self._last_cu, self._last_slack,
                         self._last_slack_summaries)

    def _save_prefs(self) -> None:
        cfg = self._read_filters()
        if self._on_config_change:
            self._on_config_change(cfg)

    # ── Manual updates ────────────────────────────────────────────────

    def _add_manual_update(self) -> None:
        text = self._manual_entry.get().strip()
        if not text:
            return
        if len(text) > 240:
            text = text[:239].rstrip() + "\u2026"
        self._manual_updates.append(text)
        self._manual_entry.delete(0, "end")
        self._render_manual_chips()
        self._save_prefs()
        self._on_filter_change()

    def _remove_manual_update(self, idx: int) -> None:
        if 0 <= idx < len(self._manual_updates):
            self._manual_updates.pop(idx)
            self._render_manual_chips()
            self._save_prefs()
            self._on_filter_change()

    def _render_manual_chips(self) -> None:
        for w in self._manual_chips_frame.winfo_children():
            w.destroy()
        if not self._manual_updates:
            self._manual_chips_frame.pack_forget()
            return
        self._manual_chips_frame.pack(fill="x", padx=10, pady=(0, 6))
        for idx, item in enumerate(self._manual_updates):
            short = item if len(item) <= 50 else item[:49] + "\u2026"
            chip = ctk.CTkFrame(self._manual_chips_frame, corner_radius=8,
                                fg_color=T.SECONDARY_CONTAINER, border_width=0)
            chip.pack(side="left", padx=(0, 4), pady=1)
            ctk.CTkLabel(chip, text=short, font=ctk.CTkFont(size=11),
                         text_color=T.ON_SECONDARY_CONTAINER).pack(side="left", padx=(8, 2), pady=3)
            ctk.CTkButton(
                chip, text="\u2715", width=20, height=20, corner_radius=10,
                font=ctk.CTkFont(size=10), fg_color="transparent",
                text_color=T.ON_SURFACE_VARIANT, hover_color=T.ERROR_CONTAINER,
                command=lambda i=idx: self._remove_manual_update(i),
            ).pack(side="left", padx=(0, 4), pady=3)

    # ── Render ────────────────────────────────────────────────────────

    def _render(
        self,
        gh: Optional[GitHubActivity],
        cu: Optional[ClickUpActivity],
        slack: Optional[SlackChannelActivity],
        slack_summaries: Optional[Dict[str, str]] = None,
        slack_error: str = "",
    ) -> None:
        if gh is not None:
            self._last_gh = gh
        if cu is not None:
            self._last_cu = cu
        if slack is not None:
            self._last_slack = slack
        if slack_summaries:
            self._last_slack_summaries = slack_summaries
        if slack_error:
            self._last_slack_error = slack_error

        gh = self._last_gh
        cu = self._last_cu
        slack = self._last_slack
        self._slack_summaries = self._last_slack_summaries
        cfg = self._read_filters()

        for w in self._scroll.winfo_children():
            w.destroy()

        row = 0
        sections: list[tuple] = []
        if cfg.get("show_github", True) and gh:
            sections.append(("gh", gh))
        if cfg.get("show_clickup", True) and cu:
            sections.append(("cu", cu))
        if cfg.get("show_slack", True) and slack and slack.messages:
            sections.append(("slack", slack))
        elif cfg.get("show_slack", True) and self._config.get("slack_monitor_channels"):
            err = getattr(self, "_last_slack_error", "")
            sections.append(("slack_warn", err))
        elif cfg.get("show_slack", True) and not self._config.get("slack_monitor_channels"):
            sections.append(("slack_hint", None))
        if cfg.get("show_manual", True) and self._manual_updates:
            sections.append(("manual", list(self._manual_updates)))

        order_key = str(cfg.get("activity_section_order", "github_first"))
        order_map = {
            "clickup_first": ["cu", "gh", "slack", "slack_warn", "manual", "slack_hint"],
            "github_first": ["gh", "cu", "slack", "slack_warn", "manual", "slack_hint"],
            "slack_first": ["slack", "slack_warn", "gh", "cu", "manual", "slack_hint"],
            "manual_first": ["manual", "cu", "gh", "slack", "slack_warn", "slack_hint"],
        }
        rank = {k: i for i, k in enumerate(order_map.get(order_key, order_map["github_first"]))}
        sections.sort(key=lambda x: rank.get(x[0], 99))
        mc = int(cfg.get("max_commits_per_repo", 10))

        for i, (kind, data) in enumerate(sections):
            if kind == "gh":
                row = self._render_github(data, row, mc)
            elif kind == "cu":
                row = self._render_clickup(data, row)
            elif kind == "slack":
                row = self._render_slack(data, row)
            elif kind == "manual":
                row = self._render_manual(data, row)
            elif kind == "slack_warn":
                channels = self._config.get("slack_monitor_channels", "")
                hint = data or "0 messages fetched."
                if not self._config.get("openai_api_key"):
                    hint += "\nNo AI API key configured \u2014 add one in Settings \u2192 AI Summary."
                row = self._render_hint(
                    "Slack Activity",
                    f"Channels: {channels}\n{hint}\n\nTip: Verify channel IDs and ensure the bot is invited to each channel.",
                    T.WARNING_CONTAINER, T.WARNING, row,
                )
            elif kind == "slack_hint":
                row = self._render_hint(
                    "Slack Discussions",
                    "Add Slack channel IDs in Settings \u2192 Slack \u2192 Monitor Channels.",
                    T.INFO_CONTAINER, T.INFO, row,
                )

        if not sections:
            ctk.CTkLabel(self._scroll, text="No activity found for today",
                         font=ctk.CTkFont(size=14), text_color=T.MUTED
                         ).grid(row=row, column=0, pady=40)

        self._is_fetching = False
        if getattr(self, "_refresh_dot_job", None):
            self.after_cancel(self._refresh_dot_job)
            self._refresh_dot_job = None
        self._refresh_btn.configure(state="normal", text="\u21BB  Refresh   ")
        self._send_btn.configure(state="normal")
        bind_mousewheel_to_scroll(self._scroll)

    # ── Section renderers ─────────────────────────────────────────────

    def _render_hint(self, title: str, msg: str, bg: Any, border: Any, row: int) -> int:
        card = ctk.CTkFrame(self._scroll, corner_radius=12, fg_color=bg,
                            border_color=border, border_width=1)
        card.grid(row=row, column=0, sticky="ew", padx=2, pady=(4, 3))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=T.ON_SURFACE, anchor="w").pack(fill="x", padx=12, pady=(8, 2))
        ctk.CTkLabel(card, text=msg, font=ctk.CTkFont(size=12), text_color=T.MUTED,
                     anchor="w", justify="left", wraplength=600
                     ).pack(fill="x", padx=12, pady=(0, 8))
        return row + 1

    def _render_github(self, gh: GitHubActivity, row: int, mc: int) -> int:
        card = T.m3_filled_card(self._scroll, corner_radius=12)
        card.grid(row=row, column=0, sticky="ew", padx=2, pady=(4, 3))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="GitHub", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=T.ON_SURFACE, anchor="w").pack(fill="x", padx=12, pady=(10, 2))

        if not gh.commits and not gh.prs_opened and not gh.prs_merged:
            ctk.CTkLabel(card, text="No GitHub activity today", font=ctk.CTkFont(size=12),
                         text_color=T.MUTED, anchor="w").pack(fill="x", padx=12, pady=(0, 8))
            return row + 1

        if gh.prs_opened:
            ctk.CTkLabel(card, text=f"PRs Opened ({len(gh.prs_opened)})",
                         font=ctk.CTkFont(size=12, weight="bold"), text_color=T.INFO,
                         anchor="w").pack(fill="x", padx=12, pady=(2, 1))
            for pr in gh.prs_opened:
                repo = pr.repo.split("/")[-1]
                ctk.CTkLabel(card, text=f"  \u2022 [{repo}] {pr.title}",
                             font=ctk.CTkFont(size=12), text_color=T.INFO,
                             anchor="w", wraplength=600, justify="left"
                             ).pack(fill="x", padx=16, pady=1)

        if gh.prs_merged:
            ctk.CTkLabel(card, text=f"PRs Merged ({len(gh.prs_merged)})",
                         font=ctk.CTkFont(size=12, weight="bold"), text_color=T.SUCCESS,
                         anchor="w").pack(fill="x", padx=12, pady=(4, 1))
            for pr in gh.prs_merged:
                repo = pr.repo.split("/")[-1]
                ctk.CTkLabel(card, text=f"  \u2022 [{repo}] {pr.title}",
                             font=ctk.CTkFont(size=12), text_color=T.SUCCESS,
                             anchor="w", wraplength=600, justify="left"
                             ).pack(fill="x", padx=16, pady=1)

        if gh.commits:
            ctk.CTkLabel(card, text=f"Commits ({len(gh.commits)})",
                         font=ctk.CTkFont(size=12, weight="bold"), text_color=T.ON_SURFACE,
                         anchor="w").pack(fill="x", padx=12, pady=(4, 1))
            by_repo: Dict[str, List[GitHubCommit]] = {}
            for c in gh.commits:
                by_repo.setdefault(c.repo.split("/")[-1], []).append(c)
            for repo, commits in by_repo.items():
                ctk.CTkLabel(card, text=repo, font=ctk.CTkFont(size=12, weight="bold"),
                             text_color=T.PRIMARY, anchor="w"
                             ).pack(fill="x", padx=16, pady=(2, 0))
                for c in commits[:mc]:
                    msg = c.message[:90] + ("..." if len(c.message) > 90 else "")
                    ctk.CTkLabel(card, text=f"  \u2022 {msg}", font=ctk.CTkFont(size=12),
                                 text_color=T.ON_SURFACE, anchor="w", wraplength=580,
                                 justify="left").pack(fill="x", padx=20, pady=1)

        ctk.CTkFrame(card, height=6, fg_color="transparent").pack()
        return row + 1

    def _render_clickup(self, cu: ClickUpActivity, row: int) -> int:
        card = T.m3_filled_card(self._scroll, corner_radius=12)
        card.grid(row=row, column=0, sticky="ew", padx=2, pady=(4, 3))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="ClickUp", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=T.ON_SURFACE, anchor="w").pack(fill="x", padx=12, pady=(10, 2))

        if not cu.tasks_completed and not cu.status_changes and not cu.comments:
            ctk.CTkLabel(card, text="No ClickUp activity today", font=ctk.CTkFont(size=12),
                         text_color=T.MUTED, anchor="w").pack(fill="x", padx=12, pady=(0, 8))
            return row + 1

        if cu.tasks_completed:
            ctk.CTkLabel(card, text=f"Completed ({len(cu.tasks_completed)})",
                         font=ctk.CTkFont(size=12, weight="bold"), text_color=T.SUCCESS,
                         anchor="w").pack(fill="x", padx=12, pady=(2, 1))
            self._tasks_into_card(card, cu.tasks_completed, cu.tasks_updated)

        if cu.status_changes:
            ctk.CTkLabel(card, text=f"In Progress ({len(cu.status_changes)})",
                         font=ctk.CTkFont(size=12, weight="bold"), text_color=T.WARNING,
                         anchor="w").pack(fill="x", padx=12, pady=(4, 1))
            self._tasks_into_card(card, cu.status_changes, cu.tasks_updated)

        if cu.comments:
            ctk.CTkLabel(card, text=f"Comments ({len(cu.comments)})",
                         font=ctk.CTkFont(size=12, weight="bold"), text_color=T.ON_SURFACE,
                         anchor="w").pack(fill="x", padx=12, pady=(4, 1))
            for c in cu.comments[:10]:
                snip = c.comment_text[:80] + ("..." if len(c.comment_text) > 80 else "")
                ctk.CTkLabel(card, text=f"  \u2022 {c.task_name}: {snip}",
                             font=ctk.CTkFont(size=12), text_color=T.ON_SURFACE,
                             anchor="w", wraplength=600, justify="left"
                             ).pack(fill="x", padx=16, pady=1)

        ctk.CTkFrame(card, height=6, fg_color="transparent").pack()
        return row + 1

    def _tasks_into_card(self, card: ctk.CTkFrame, tasks: List[ClickUpTask],
                         all_tasks: List[ClickUpTask]) -> None:
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
            ctk.CTkLabel(card, text=f"  \u2022 {t.name}  {badge}",
                         font=ctk.CTkFont(size=12), text_color=T.ON_SURFACE,
                         anchor="w", wraplength=580, justify="left"
                         ).pack(fill="x", padx=16, pady=1)
            rendered.add(t.task_id)
            for ch in children_map.get(t.task_id, []):
                if ch.task_id in rendered:
                    continue
                ctk.CTkLabel(card, text=f"    \u25e6 {ch.name}  {self._badge(ch.status)}",
                             font=ctk.CTkFont(size=11), text_color=T.MUTED,
                             anchor="w", wraplength=560, justify="left"
                             ).pack(fill="x", padx=24, pady=1)
                rendered.add(ch.task_id)

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

    def _render_manual(self, updates: List[str], row: int) -> int:
        card = T.m3_filled_card(self._scroll, corner_radius=12)
        card.grid(row=row, column=0, sticky="ew", padx=2, pady=(4, 3))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="Manual Updates",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=T.ON_SURFACE, anchor="w").pack(fill="x", padx=12, pady=(10, 2))

        for text in updates[:20]:
            clean = " ".join(str(text).split()).strip()
            if not clean:
                continue
            if len(clean) > 180:
                clean = clean[:179] + "..."
            ctk.CTkLabel(card, text=f"  \u2022 {clean}", font=ctk.CTkFont(size=12),
                         text_color=T.ON_SURFACE, anchor="w", wraplength=600,
                         justify="left").pack(fill="x", padx=12, pady=1)

        ctk.CTkFrame(card, height=6, fg_color="transparent").pack()
        return row + 1

    def _render_slack(self, slack: SlackChannelActivity, row: int) -> int:
        card = ctk.CTkFrame(self._scroll, corner_radius=12, fg_color=T.INFO_CONTAINER,
                            border_color=T.INFO, border_width=1)
        card.grid(row=row, column=0, sticky="ew", padx=2, pady=(4, 3))
        card.grid_columnconfigure(0, weight=1)

        total = len(slack.messages)
        ctk.CTkLabel(card, text=f"Slack Activity  ({total} messages)",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=T.ON_SURFACE, anchor="w").pack(fill="x", padx=12, pady=(10, 2))

        by_ch: Dict[str, List[SlackMessage]] = {}
        for m in slack.messages:
            by_ch.setdefault(m.channel_name or m.channel_id, []).append(m)

        summaries = getattr(self, "_slack_summaries", {})

        for ch_name, msgs in by_ch.items():
            ctk.CTkLabel(card, text=f"#{ch_name}  ({len(msgs)} messages)",
                         font=ctk.CTkFont(size=12, weight="bold"), text_color=T.PRIMARY,
                         anchor="w").pack(fill="x", padx=12, pady=(4, 1))

            summary_text = summaries.get(ch_name, "")
            if summary_text:
                sf = ctk.CTkFrame(card, corner_radius=8, fg_color=T.SURFACE_CONTAINER)
                sf.pack(fill="x", padx=16, pady=(2, 4))
                ctk.CTkLabel(sf, text="AI Summary", font=ctk.CTkFont(size=11, weight="bold"),
                             text_color=T.PRIMARY, anchor="w").pack(fill="x", padx=10, pady=(6, 1))
                ctk.CTkLabel(sf, text=summary_text, font=ctk.CTkFont(size=12),
                             text_color=T.ON_SURFACE, anchor="w", justify="left",
                             wraplength=560).pack(fill="x", padx=10, pady=(0, 6))
            else:
                for m in msgs[:8]:
                    snip = m.text[:120] + ("..." if len(m.text) > 120 else "")
                    ts = m.timestamp.strftime("%H:%M") if m.timestamp else ""
                    ctk.CTkLabel(card, text=f"  {ts}  {m.user_name}: {snip}",
                                 font=ctk.CTkFont(size=12), text_color=T.ON_SURFACE,
                                 anchor="w", wraplength=580, justify="left"
                                 ).pack(fill="x", padx=16, pady=1)
                if len(msgs) > 8:
                    ctk.CTkLabel(card, text=f"  ... and {len(msgs) - 8} more",
                                 font=ctk.CTkFont(size=12), text_color=T.MUTED,
                                 anchor="w").pack(fill="x", padx=16, pady=2)

        ctk.CTkFrame(card, height=6, fg_color="transparent").pack()
        return row + 1


# ── Helpers ───────────────────────────────────────────────────────────────────

_ORDER_MAP = {
    "GitHub first": "github_first",
    "ClickUp first": "clickup_first",
    "Slack first": "slack_first",
    "Manual first": "manual_first",
}
_ORDER_MAP_REV = {v: k for k, v in _ORDER_MAP.items()}


def _vsep(parent: ctk.CTkFrame) -> None:
    ctk.CTkFrame(parent, width=1, fg_color=T.OUTLINE_VARIANT, height=20).pack(
        side="left", padx=8, pady=6)
