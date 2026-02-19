"""
Dashboard View — Material Design 3 styled scheduler status, stats, and actions.
"""

from __future__ import annotations

import threading
import tkinter as tk
from datetime import datetime
from typing import Any, Dict

import customtkinter as ctk

from desktop.local_scheduler import LocalScheduler
from desktop import theme as T


class DashboardView(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, scheduler: LocalScheduler, config: Dict[str, Any]) -> None:
        super().__init__(parent, fg_color="transparent")
        self._scheduler = scheduler
        self._config = config
        self._is_fetching = False
        self._dot_count = 0
        self._dot_job = None
        self._send_dot_count = 0
        self._send_dot_job = None

        self.grid_columnconfigure(0, weight=1)
        self._build_ui()
        self._tick()
        self.after(300, self._refresh_stats)

    def update_config(self, config: Dict[str, Any]) -> None:
        self._config = config
        self._update_channel_label()

    def _build_ui(self) -> None:
        # ── Header with action buttons ────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        hdr.grid_columnconfigure(0, weight=1)

        title_box = ctk.CTkFrame(hdr, fg_color="transparent")
        title_box.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(title_box, text="Dashboard", font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=T.ON_SURFACE, anchor="w").pack(anchor="w")
        ctk.CTkLabel(title_box, text="Overview of your EOD automation",
                     font=ctk.CTkFont(size=12), text_color=T.MUTED, anchor="w"
                     ).pack(anchor="w", pady=(1, 0))

        btn_box = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_box.grid(row=0, column=1, sticky="e")

        self._refresh_btn = T.m3_tonal_button(btn_box, text="\u21BB  Refresh   ",
                                              command=self._refresh_stats, width=130)
        self._refresh_btn.pack(side="left", padx=(0, 6))

        self._send_btn = T.m3_filled_button(btn_box, text="\u25B6  Send EOD  ",
                                            command=self._trigger_now, width=130)
        self._send_btn.pack(side="left")

        # ── Status label ──────────────────────────────────────────────
        self._action_status = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12),
                                           text_color=T.MUTED, anchor="w")
        self._action_status.grid(row=1, column=0, sticky="w", pady=(0, 8))

        # ── Scheduler status card ─────────────────────────────────────
        sc = T.m3_card(self)
        sc.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        sc_inner = ctk.CTkFrame(sc, fg_color="transparent")
        sc_inner.pack(fill="x", padx=16, pady=14)

        # Circular dot via a small canvas
        self._dot_canvas = tk.Canvas(sc_inner, width=14, height=14,
                                     highlightthickness=0, bd=0)
        self._dot_canvas.pack(side="left", padx=(0, 10))
        self._dot_id = self._dot_canvas.create_oval(1, 1, 13, 13, fill="#1B873B", outline="")
        self._apply_canvas_bg()

        self._status_label = ctk.CTkLabel(sc_inner, text="Scheduler Running",
                                          font=ctk.CTkFont(size=14, weight="bold"),
                                          text_color=T.ON_SURFACE, anchor="w")
        self._status_label.pack(side="left", fill="x", expand=True)
        self._toggle_btn = T.m3_tonal_button(sc_inner, text="Pause", width=90,
                                             command=self._toggle_scheduler)
        self._toggle_btn.pack(side="right")

        # ── Schedule info card ────────────────────────────────────────
        sch = T.m3_card(self)
        sch.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        sch_inner = ctk.CTkFrame(sch, fg_color="transparent")
        sch_inner.pack(fill="x", padx=16, pady=12)
        sch_inner.grid_columnconfigure(1, weight=1)

        self._next_run_label = ctk.CTkLabel(sch_inner, text="Next report:  \u2014",
                                            font=ctk.CTkFont(size=13),
                                            text_color=T.ON_SURFACE, anchor="w")
        self._next_run_label.grid(row=0, column=0, sticky="w")
        self._last_run_label = ctk.CTkLabel(sch_inner, text="Last report:  \u2014",
                                            font=ctk.CTkFont(size=13),
                                            text_color=T.MUTED, anchor="w")
        self._last_run_label.grid(row=1, column=0, sticky="w", pady=(2, 0))
        self._channel_label = ctk.CTkLabel(sch_inner, text="",
                                           font=ctk.CTkFont(size=12),
                                           text_color=T.MUTED, anchor="e")
        self._channel_label.grid(row=0, column=1, rowspan=2, sticky="e")
        self._update_channel_label()

        # ── Stats row ─────────────────────────────────────────────────
        sf = ctk.CTkFrame(self, fg_color="transparent")
        sf.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        for i in range(4):
            sf.grid_columnconfigure(i, weight=1)

        stat_defs = [
            ("Commits", "0", T.INFO, "\U0001F4DD"),
            ("PRs", "0", T.PRIMARY, "\U0001F500"),
            ("Completed", "0", T.SUCCESS, "\u2705"),
            ("In Progress", "0", T.WARNING, "\u23F3"),
        ]
        self._stat_values: list[ctk.CTkLabel] = []
        for col, (title, val, color, icon) in enumerate(stat_defs):
            card = T.m3_filled_card(sf)
            card.grid(row=0, column=col, padx=(0 if col == 0 else 4, 0), sticky="ew")

            ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=18),
                         text_color=T.MUTED).pack(pady=(12, 0))
            vl = ctk.CTkLabel(card, text=val, font=ctk.CTkFont(size=28, weight="bold"),
                              text_color=color)
            vl.pack(pady=(2, 0))
            self._stat_values.append(vl)
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11),
                         text_color=T.MUTED).pack(pady=(0, 12))

    # ── Canvas background sync ────────────────────────────────────────

    def _apply_canvas_bg(self) -> None:
        mode = ctk.get_appearance_mode()
        bg = "#FFFFFF" if mode == "Light" else "#211F26"
        try:
            self._dot_canvas.configure(bg=bg)
        except Exception:
            pass
        self.after(2000, self._apply_canvas_bg)

    # ── Scheduler events ──────────────────────────────────────────────

    def on_scheduler_event(self, event: str, detail: Dict[str, Any]) -> None:
        if event == "scheduler_started":
            self._set_status(True)
        elif event == "scheduler_stopped":
            self._set_status(False)
        elif event == "pipeline_started":
            self._action_status.configure(text="Sending EOD report...", text_color=T.MUTED)
            self._send_btn.configure(state="disabled")
            if not self._send_dot_job:
                self._send_dot_count = 0
                self._animate_send_dots()
        elif event == "pipeline_completed":
            ts = detail.get("timestamp", "")
            self._last_run_label.configure(text=f"Last report:  {self._fmt(ts)}")
            self._action_status.configure(text="EOD report sent successfully", text_color=T.SUCCESS)
            if self._send_dot_job:
                self.after_cancel(self._send_dot_job)
                self._send_dot_job = None
            self._send_btn.configure(state="normal", text="\u25B6  Send EOD  ")
        elif event == "pipeline_error":
            err = detail.get("error", "Unknown error")
            self._action_status.configure(text=f"Error: {err[:80]}", text_color=T.ERROR)
            if self._send_dot_job:
                self.after_cancel(self._send_dot_job)
                self._send_dot_job = None
            self._send_btn.configure(state="normal", text="\u25B6  Send EOD  ")
        elif event == "job_missed":
            scheduled = detail.get("scheduled_time", "")
            self._action_status.configure(
                text=f"Missed ({scheduled}) \u2014 system was likely asleep",
                text_color=T.WARNING,
            )

    # ── Actions ───────────────────────────────────────────────────────

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
        self._action_status.configure(text="Triggering EOD pipeline...", text_color=T.MUTED)
        self._send_btn.configure(state="disabled")
        self._send_dot_count = 0
        self._animate_send_dots()
        self._scheduler.trigger_now()

    def _animate_send_dots(self) -> None:
        if self._send_btn.cget("state") != "disabled":
            return
        self._send_dot_count = (self._send_dot_count % 3) + 1
        dots = ("." * self._send_dot_count).ljust(3)
        self._send_btn.configure(text=f"\u25B6  Sending{dots} ")
        self._send_dot_job = self.after(350, self._animate_send_dots)

    def _refresh_stats(self) -> None:
        if self._is_fetching:
            return
        self._is_fetching = True
        self._refresh_btn.configure(state="disabled")
        self._dot_count = 0
        self._animate_dots()
        threading.Thread(target=self._fetch_stats_bg, daemon=True).start()

    def _animate_dots(self) -> None:
        if not self._is_fetching:
            return
        self._dot_count = (self._dot_count % 3) + 1
        dots = ("." * self._dot_count).ljust(3)
        self._refresh_btn.configure(text=f"\u21BB  Loading{dots} ")
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
        self._refresh_btn.configure(state="normal", text="\u21BB  Refresh   ")
        self._action_status.configure(text="Stats refreshed", text_color=T.SUCCESS)

    # ── Helpers ───────────────────────────────────────────────────────

    def _set_status(self, running: bool) -> None:
        color = "#1B873B" if running else "#B3261E"
        self._dot_canvas.itemconfigure(self._dot_id, fill=color)
        self._status_label.configure(text="Scheduler Running" if running else "Scheduler Paused")
        self._toggle_btn.configure(text="Pause" if running else "Resume")

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
