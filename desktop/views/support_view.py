"""
Support View — documentation and setup guide.
"""

from __future__ import annotations

from typing import Any, Dict

import customtkinter as ctk

from desktop.utils import FixedScrollableFrame, bind_mousewheel_to_scroll

_CARD_BG = ("#ffffff", "#1e1f2e")
_CARD_BORDER = ("#e5e7eb", "#2d2f3d")
_MUTED = ("#6b7280", "#8b8d97")
_ACCENT = ("#6366f1", "#818cf8")
_STEP_BG = ("#f3f4f6", "#252736")


def _section_card(parent: FixedScrollableFrame, icon: str, title: str, desc: str, steps: list[str] | None = None) -> ctk.CTkFrame:
    card = ctk.CTkFrame(parent, corner_radius=14, fg_color=_CARD_BG, border_color=_CARD_BORDER, border_width=1)
    card.grid_columnconfigure(0, weight=1)
    hf = ctk.CTkFrame(card, fg_color="transparent")
    hf.pack(fill="x", padx=20, pady=(16, 4))
    ctk.CTkLabel(hf, text=f"{icon}  {title}", font=ctk.CTkFont(size=17, weight="bold"), anchor="w").pack(side="left")
    ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(size=13), text_color=_MUTED, anchor="w", justify="left", wraplength=660).pack(fill="x", padx=20, pady=(0, 4))
    if steps:
        sf = ctk.CTkFrame(card, fg_color=_STEP_BG, corner_radius=10)
        sf.pack(fill="x", padx=16, pady=(4, 16))
        sf.grid_columnconfigure(1, weight=1)
        for i, text in enumerate(steps):
            ctk.CTkLabel(sf, text=f"{i + 1}", font=ctk.CTkFont(size=11, weight="bold"), text_color=_ACCENT, width=22, anchor="e").grid(row=i, column=0, sticky="ne", padx=(12, 6), pady=(6 if i == 0 else 2, 2))
            ctk.CTkLabel(sf, text=text, font=ctk.CTkFont(size=13), anchor="w", justify="left", wraplength=600).grid(row=i, column=1, sticky="w", padx=(0, 12), pady=(6 if i == 0 else 2, 2))
        ctk.CTkFrame(sf, height=8, fg_color="transparent").grid(row=len(steps), column=0, columnspan=2)
    else:
        ctk.CTkFrame(card, height=12, fg_color="transparent").pack()
    return card


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
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        ctk.CTkLabel(hdr, text="\u2753  Support & Documentation", font=ctk.CTkFont(size=28, weight="bold"), anchor="w").pack(side="left")

        self._scroll = FixedScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self._scroll.grid(row=1, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)
        bind_mousewheel_to_scroll(self._scroll)

        r = 0
        cards: list[tuple] = [
            ("\U0001F680", "Getting Started", "Configure your tokens and schedule in the Settings tab. Use the Test buttons to verify each connection before saving.", None),
            ("\U0001F4BB", "GitHub Personal Access Token", "Required to fetch your commits and pull requests.", [
                "Go to github.com/settings/tokens",
                "Click 'Generate new token (classic)' or use fine-grained tokens",
                "Select scopes: repo, read:user",
                "Copy the token \u2192 Settings \u2192 GitHub \u2192 Token",
                "Enter your GitHub username in Settings \u2192 GitHub \u2192 Username",
            ]),
            ("\u2611", "ClickUp API Token", "Required to fetch your task updates and completions.", [
                "Open ClickUp \u2192 avatar (bottom-left) \u2192 Settings",
                "Go to Apps in the sidebar",
                "Under API Token, click Generate (or copy existing)",
                "Paste in Settings \u2192 ClickUp \u2192 API Token",
            ]),
            ("\U0001F50D", "Finding ClickUp Team ID", "The number in your workspace URL.", [
                "Open any ClickUp space in your browser",
                "URL format: app.clickup.com/12345678/... \u2014 the number is your Team ID",
            ]),
            ("\U0001F464", "Finding ClickUp User ID", "Your numeric user ID in the ClickUp API.", [
                "Call: curl -H 'Authorization: YOUR_TOKEN' https://api.clickup.com/api/v2/team",
                "Find your user under team.members[].user",
                "The numeric 'id' field is your User ID",
            ]),
            ("\U0001F4AC", "Slack Bot Token", "Required to post EOD reports to a channel.", [
                "Go to api.slack.com/apps \u2192 Create New App \u2192 From scratch",
                "Add scopes: chat:write, users:read, users.profile:read, chat:write.customize",
                "For channel monitoring: add channels:history, channels:read",
                "Install the app to your workspace",
                "Copy Bot User OAuth Token (xoxb-...) \u2192 Settings \u2192 Slack \u2192 Bot Token",
                "Invite bot to your channel: /invite @YourBotName",
            ]),
            ("\U0001F4AC", "Slack Channel Monitoring", "Track discussions from specific Slack channels in your Activity tab.", [
                "Get channel IDs: right-click channel name \u2192 View channel details \u2192 copy ID at bottom",
                "Paste comma-separated IDs in Settings \u2192 Slack \u2192 Monitor Channels",
                "Example: C01ABC123,C02DEF456",
                "The bot must be a member of each channel you want to monitor",
            ]),
            ("\u2728", "AI Summary — Free with Google Gemini", "Get an AI-generated brief of your daily activity. Multiple free providers supported!", [
                "RECOMMENDED (Free): Go to aistudio.google.com/apikey \u2192 Create API Key",
                "Select 'Google Gemini (Free)' as Provider in Settings (default)",
                "Paste your API key in Settings \u2192 AI Summary \u2192 API Key",
                "Model auto-fills to gemini-2.0-flash (fast & free, 1M tokens/day)",
                "Alternative free: console.groq.com \u2192 API Keys \u2192 select 'Groq (Free)' provider",
                "Paid option: platform.openai.com \u2192 API keys \u2192 select 'OpenAI' provider",
                "Local option: Install Ollama (ollama.com) \u2192 select 'Ollama (Local)' provider",
                "Click Refresh on Activity tab to see the AI summary",
            ]),
            ("\U0001F464", "Slack User ID (optional)", "For OOO detection and profile picture. Right-click your name in Slack \u2192 Copy member ID.", None),
            ("\u23F0", "Schedule", "Set the hour (0\u201323) and minute for the daily report. Runs Monday\u2013Friday. Use IANA timezone.", None),
            ("\U0001F4A1", "Tips", "\u2022 Double-click masked token fields to show/hide\n\u2022 Use 'Import Config File' to load settings from .env, .txt, or .json\n\u2022 Keep the app open for automatic scheduled reports\n\u2022 Use 'Send EOD Now' on Dashboard for manual trigger\n\u2022 AI summaries require an OpenAI API key with credits\n\u2022 Test each connection after entering tokens", None),
        ]

        for icon, title, desc, steps in cards:
            card = _section_card(self._scroll, icon, title, desc, steps)
            card.grid(row=r, column=0, sticky="ew", pady=(0, 10))
            r += 1
