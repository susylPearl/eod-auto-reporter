"""
Dashboard View — scheduler status, quick stats, and trigger button.
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any, Dict

import customtkinter as ctk

from desktop.local_scheduler import LocalScheduler

_CARD_BG = ("#ffffff", "#1e1f2e")
_CARD_BORDER = ("#e5e7eb", "#2d2f3d")
_MUTED = ("#6b7280", "#8b8d97")
_ACCENT = ("#6366f1", "#818cf8")
_GREEN = "#22c55e"
_RED = "#ef4444"


def _card(parent: Any, **kw: Any) -> ctk.CTkFrame:
    return ctk.CTkFrame(parent, corner_radius=14, fg_color=_CARD_BG, border_color=_CARD_BORDER, border_width=1, **kw)


class DashboardView(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, scheduler: LocalScheduler, config: Dict[str, Any]) -> None:
        super().__init__(parent, fg_color="transparent")
        self._scheduler = scheduler
        self._config = config
        self._is_fetching = False
        self._dot_count = 0
        self._dot_job = None

        self.grid_columnconfigure(0, weight=1)
        self._build_ui()
        self._tick()
        # Auto-fetch dashboard stats on first load.
        self.after(300, self._refresh_stats)

    def update_config(self, config: Dict[str, Any]) -> None:
        self._config = config
        self._update_channel_label()

    def _build_ui(self) -> None:
        row = 0

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=row, column=0, sticky="ew", pady=(0, 20))
        ctk.CTkLabel(hdr, text="Dashboard", font=ctk.CTkFont(size=28, weight="bold"), anchor="w").pack(anchor="w")
        ctk.CTkLabel(hdr, text="Overview of your EOD automation", font=ctk.CTkFont(size=13), text_color=_MUTED, anchor="w").pack(anchor="w", pady=(2, 0))
        row += 1

        # Status
        sc = _card(self)
        sc.grid(row=row, column=0, sticky="ew", pady=(0, 16))
        sc.grid_columnconfigure(1, weight=1)
        self._status_dot = ctk.CTkLabel(sc, text="\u25cf", font=ctk.CTkFont(size=20), text_color=_GREEN, width=30)
        self._status_dot.grid(row=0, column=0, padx=(20, 6), pady=18)
        self._status_label = ctk.CTkLabel(sc, text="Scheduler Running", font=ctk.CTkFont(size=16, weight="bold"), anchor="w")
        self._status_label.grid(row=0, column=1, sticky="w", pady=18)
        self._toggle_btn = ctk.CTkButton(sc, text="Pause", width=90, height=34, font=ctk.CTkFont(size=13), corner_radius=8, fg_color=("gray80", "gray30"), hover_color=("gray70", "gray38"), text_color=("gray10", "gray90"), command=self._toggle_scheduler)
        self._toggle_btn.grid(row=0, column=2, padx=18, pady=18)
        row += 1

        # Schedule
        sch = _card(self)
        sch.grid(row=row, column=0, sticky="ew", pady=(0, 16))
        sch.grid_columnconfigure(1, weight=1)
        self._next_run_label = ctk.CTkLabel(sch, text="Next report:  \u2014", font=ctk.CTkFont(size=14), anchor="w")
        self._next_run_label.grid(row=0, column=0, padx=20, pady=(16, 4), sticky="w")
        self._last_run_label = ctk.CTkLabel(sch, text="Last report:  \u2014", font=ctk.CTkFont(size=14), anchor="w")
        self._last_run_label.grid(row=1, column=0, padx=20, pady=(0, 16), sticky="w")
        self._channel_label = ctk.CTkLabel(sch, text="", font=ctk.CTkFont(size=12), text_color=_MUTED, anchor="e")
        self._channel_label.grid(row=0, column=1, padx=20, pady=(16, 4), sticky="e")
        self._update_channel_label()
        row += 1

        # Stats
        sf = ctk.CTkFrame(self, fg_color="transparent")
        sf.grid(row=row, column=0, sticky="ew", pady=(0, 16))
        for i in range(4):
            sf.grid_columnconfigure(i, weight=1)
        stat_defs = [("Commits", "0", "#3b82f6", "\U0001F4DD"), ("PRs", "0", "#8b5cf6", "\U0001F500"), ("Completed", "0", _GREEN, "\u2705"), ("In Progress", "0", "#f59e0b", "\u23F3")]
        self._stat_values: list[ctk.CTkLabel] = []
        for col, (title, val, color, icon) in enumerate(stat_defs):
            card = _card(sf)
            card.grid(row=0, column=col, padx=5, sticky="ew")
            card.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=18)).grid(row=0, column=0, padx=16, pady=(16, 0))
            vl = ctk.CTkLabel(card, text=val, font=ctk.CTkFont(size=30, weight="bold"), text_color=color)
            vl.grid(row=1, column=0, padx=16, pady=(4, 2))
            self._stat_values.append(vl)
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12), text_color=_MUTED).grid(row=2, column=0, padx=16, pady=(0, 14))
        row += 1

        # Actions
        ac = _card(self)
        ac.grid(row=row, column=0, sticky="ew")
        ac.grid_columnconfigure(2, weight=1)

        self._send_btn = ctk.CTkButton(ac, text="\u25B6  Send EOD Now", font=ctk.CTkFont(size=14, weight="bold"), height=42, corner_radius=10, fg_color=_ACCENT, hover_color=("#4f46e5", "#6366f1"), command=self._trigger_now)
        self._send_btn.grid(row=0, column=0, padx=(18, 10), pady=(18, 4), sticky="w")

        self._refresh_btn = ctk.CTkButton(ac, text="\u21BB  Refresh Stats", font=ctk.CTkFont(size=13), height=42, corner_radius=10, fg_color=_ACCENT, hover_color=("#4f46e5", "#6366f1"), command=self._refresh_stats)
        self._refresh_btn.grid(row=0, column=1, pady=(18, 4), sticky="w")

        self._action_status = ctk.CTkLabel(ac, text="", font=ctk.CTkFont(size=12), text_color=_MUTED, anchor="w")
        self._action_status.grid(row=1, column=0, columnspan=3, padx=20, pady=(2, 16), sticky="w")

    # -- Scheduler events --

    def on_scheduler_event(self, event: str, detail: Dict[str, Any]) -> None:
        if event == "scheduler_started":
            self._set_status(True)
        elif event == "scheduler_stopped":
            self._set_status(False)
        elif event == "pipeline_started":
            self._action_status.configure(text="Sending EOD report...")
            self._send_btn.configure(state="disabled", text="\u25B6  Sending...")
        elif event == "pipeline_completed":
            ts = detail.get("timestamp", "")
            self._last_run_label.configure(text=f"Last report:  {self._fmt(ts)}")
            self._action_status.configure(text="\u2705  EOD report sent successfully!")
            self._send_btn.configure(state="normal", text="\u25B6  Send EOD Now")
        elif event == "pipeline_error":
            err = detail.get("error", "Unknown error")
            self._action_status.configure(text=f"\u274C  Error: {err[:80]}")
            self._send_btn.configure(state="normal", text="\u25B6  Send EOD Now")

    # -- Actions --

    def _toggle_scheduler(self) -> None:
        if self._scheduler.is_running:
            self._scheduler.stop()
            self._set_status(False)
        else:
            h = int(self._config.get("report_hour", 18))
            m = int(self._config.get("report_minute", 0))
            tz = str(self._config.get("timezone", "Asia/Kathmandu"))
            self._scheduler.start(h, m, tz)
            self._set_status(True)

    def _trigger_now(self) -> None:
        self._action_status.configure(text="Triggering EOD pipeline...")
        self._send_btn.configure(state="disabled", text="\u25B6  Sending...")
        self._scheduler.trigger_now()

    def _refresh_stats(self) -> None:
        if self._is_fetching:
            return
        self._is_fetching = True
        self._refresh_btn.configure(state="disabled")
        self._dot_count = 0
        self._animate_dots()
        threading.Thread(target=self._fetch_stats_bg, daemon=True).start()

    def _animate_dots(self) -> None:
        """Cycle dots inside the button text as a loading indicator."""
        if not self._is_fetching:
            return
        self._dot_count = (self._dot_count % 3) + 1
        dots = "." * self._dot_count
        self._refresh_btn.configure(text=f"\u21BB  Refreshing{dots}")
        self._dot_job = self.after(350, self._animate_dots)

    def _fetch_stats_bg(self) -> None:
        commits = prs = completed = in_progress = 0
        try:
            from app.services import github_service
            gh = github_service.fetch_github_activity()
            commits = len(gh.commits)
            prs = len(gh.prs_opened) + len(gh.prs_merged)
        except Exception:
            pass
        try:
            from app.services import clickup_service
            cu = clickup_service.fetch_clickup_activity()
            completed = len(cu.tasks_completed)
            in_progress = len(cu.status_changes)
        except Exception:
            pass
        self.after(0, self._update_stats, commits, prs, completed, in_progress)

    def _update_stats(self, commits: int, prs: int, completed: int, in_progress: int) -> None:
        self._stat_values[0].configure(text=str(commits))
        self._stat_values[1].configure(text=str(prs))
        self._stat_values[2].configure(text=str(completed))
        self._stat_values[3].configure(text=str(in_progress))
        self._is_fetching = False
        if self._dot_job:
            self.after_cancel(self._dot_job)
            self._dot_job = None
        self._refresh_btn.configure(state="normal", text="\u21BB  Refresh Stats")
        self._action_status.configure(text="\u2705  Stats refreshed")

    # -- Helpers --

    def _set_status(self, running: bool) -> None:
        if running:
            self._status_dot.configure(text_color=_GREEN)
            self._status_label.configure(text="Scheduler Running")
            self._toggle_btn.configure(text="Pause")
        else:
            self._status_dot.configure(text_color=_RED)
            self._status_label.configure(text="Scheduler Paused")
            self._toggle_btn.configure(text="Resume")

    def _update_channel_label(self) -> None:
        ch = self._config.get("slack_channel", "")
        if ch:
            self._channel_label.configure(text=f"Channel: {ch}")

    def _tick(self) -> None:
        nrt = self._scheduler.get_next_run_time()
        if nrt:
            self._next_run_label.configure(text=f"Next report:  {nrt.strftime('%a %b %d, %I:%M %p %Z')}")
        self.after(30_000, self._tick)

    @staticmethod
    def _fmt(iso: str) -> str:
        try:
            return datetime.fromisoformat(iso).strftime("%I:%M %p")
        except Exception:
            return iso or "\u2014"
