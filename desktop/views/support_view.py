"""
Support View — Material Design 3 styled documentation and setup guide.
"""

from __future__ import annotations

from typing import Any, Dict

import customtkinter as ctk

from desktop.utils import FixedScrollableFrame, bind_mousewheel_to_scroll
from desktop import theme as T


class SupportView(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, config: Dict[str, Any], on_save: Any = None) -> None:
        super().__init__(parent, fg_color="transparent")
        self._config = dict(config)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_ui()

    def update_config(self, config: Dict[str, Any]) -> None:
        self._config = dict(config)

    def _build_ui(self) -> None:
        ctk.CTkLabel(self, text="Support & Documentation",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=T.ON_SURFACE, anchor="w"
                     ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        self._scroll = FixedScrollableFrame(
            self, corner_radius=12, fg_color=T.CARD_BG,
            border_color=T.CARD_BORDER, border_width=1,
        )
        self._scroll.grid(row=1, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)
        bind_mousewheel_to_scroll(self._scroll)

        cards: list[tuple] = [
            ("\U0001F680", "Getting Started",
             "Configure your tokens and schedule in the Settings tab. Use the Test buttons to verify each connection before saving.",
             None),
            ("\U0001F4BB", "GitHub Personal Access Token",
             "Required to fetch your commits and pull requests.", [
                 "Go to github.com/settings/tokens",
                 "Click 'Generate new token (classic)' or use fine-grained tokens",
                 "Select scopes: repo, read:user",
                 "Copy the token \u2192 Settings \u2192 GitHub \u2192 Token",
                 "Enter your GitHub username in Settings \u2192 GitHub \u2192 Username",
             ]),
            ("\u2611", "ClickUp API Token",
             "Required to fetch your task updates and completions.", [
                 "Open ClickUp \u2192 avatar (bottom-left) \u2192 Settings",
                 "Go to Apps in the sidebar",
                 "Under API Token, click Generate (or copy existing)",
                 "Paste in Settings \u2192 ClickUp \u2192 API Token",
             ]),
            ("\U0001F50D", "Finding ClickUp Team ID",
             "The number in your workspace URL.", [
                 "Open any ClickUp space in your browser",
                 "URL format: app.clickup.com/12345678/... \u2014 the number is your Team ID",
             ]),
            ("\U0001F464", "Finding ClickUp User ID",
             "Your numeric user ID in the ClickUp API.", [
                 "Call: curl -H 'Authorization: YOUR_TOKEN' https://api.clickup.com/api/v2/team",
                 "Find your user under team.members[].user",
                 "The numeric 'id' field is your User ID",
             ]),
            ("\U0001F4AC", "Slack Bot Token",
             "Required to post EOD reports to a channel.", [
                 "Go to api.slack.com/apps \u2192 Create New App \u2192 From scratch",
                 "Add scopes: chat:write, users:read, users.profile:read, chat:write.customize",
                 "For channel monitoring: add channels:history, channels:read",
                 "Install the app to your workspace",
                 "Copy Bot User OAuth Token (xoxb-...) \u2192 Settings \u2192 Slack \u2192 Bot Token",
                 "Invite bot to your channel: /invite @YourBotName",
             ]),
            ("\U0001F4AC", "Slack Channel Monitoring",
             "Track discussions from specific Slack channels in your Activity tab.", [
                 "Get channel IDs: right-click channel \u2192 View details \u2192 copy ID at bottom",
                 "Paste comma-separated IDs in Settings \u2192 Slack \u2192 Monitor Channels",
                 "Example: C01ABC123,C02DEF456",
                 "The bot must be a member of each channel you want to monitor",
             ]),
            ("\u2728", "AI Summary \u2014 Free with Google Gemini",
             "Get an AI-generated brief of your daily activity. Multiple free providers supported!", [
                 "RECOMMENDED (Free): Go to aistudio.google.com/apikey \u2192 Create API Key",
                 "Select 'Google Gemini (Free)' as Provider in Settings (default)",
                 "Paste your API key in Settings \u2192 AI Summary \u2192 API Key",
                 "Model auto-fills to gemini-2.0-flash (fast & free, 1M tokens/day)",
                 "Alternative free: console.groq.com \u2192 API Keys \u2192 select 'Groq (Free)' provider",
                 "Paid option: platform.openai.com \u2192 API keys \u2192 select 'OpenAI' provider",
                 "Local option: Install Ollama (ollama.com) \u2192 select 'Ollama (Local)' provider",
             ]),
            ("\u23F0", "Schedule",
             "Set the hour (0\u201323) and minute for the daily report. Runs Monday\u2013Friday. Use IANA timezone.",
             None),
            ("\U0001F4A1", "Tips",
             "\u2022 Double-click masked token fields to show/hide\n"
             "\u2022 Use 'Import Config File' to load settings from .env, .txt, .json, .md, .docx\n"
             "\u2022 Keep the app open for automatic scheduled reports\n"
             "\u2022 Use 'Send EOD Now' on Dashboard for manual trigger\n"
             "\u2022 Click Refresh on Activity tab to see AI summaries\n"
             "\u2022 Test each connection after entering tokens",
             None),
        ]

        for r, (icon, title, desc, steps) in enumerate(cards):
            self._build_card(r, icon, title, desc, steps)

    def _build_card(self, row: int, icon: str, title: str, desc: str,
                    steps: list[str] | None) -> None:
        card = T.m3_filled_card(self._scroll, corner_radius=12)
        card.grid(row=row, column=0, sticky="ew", padx=2, pady=(4 if row > 0 else 6, 3))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text=f"{icon}  {title}",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=T.ON_SURFACE, anchor="w"
                     ).pack(fill="x", padx=12, pady=(10, 2))

        ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(size=12),
                     text_color=T.MUTED, anchor="w", justify="left",
                     wraplength=640).pack(fill="x", padx=12, pady=(0, 4))

        if steps:
            sf = ctk.CTkFrame(card, fg_color=T.SURFACE_CONTAINER_HIGH, corner_radius=10)
            sf.pack(fill="x", padx=10, pady=(2, 10))
            sf.grid_columnconfigure(1, weight=1)
            for i, text in enumerate(steps):
                ctk.CTkLabel(sf, text=f"{i + 1}", font=ctk.CTkFont(size=10, weight="bold"),
                             text_color=T.PRIMARY, width=20, anchor="e"
                             ).grid(row=i, column=0, sticky="ne", padx=(8, 4),
                                    pady=(5 if i == 0 else 1, 1))
                ctk.CTkLabel(sf, text=text, font=ctk.CTkFont(size=12),
                             text_color=T.ON_SURFACE, anchor="w", justify="left",
                             wraplength=580).grid(row=i, column=1, sticky="w",
                                                  padx=(0, 8),
                                                  pady=(5 if i == 0 else 1, 1))
            ctk.CTkFrame(sf, height=4, fg_color="transparent").grid(
                row=len(steps), column=0, columnspan=2)
        else:
            ctk.CTkFrame(card, height=6, fg_color="transparent").pack()
