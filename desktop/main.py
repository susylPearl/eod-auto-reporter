#!/usr/bin/env python3
"""
EOD Auto Reporter — Desktop App

Entry point for the macOS desktop application.

This script:
  1. Ensures the project root is on sys.path.
  2. Loads config from ~/Library/Application Support/EOD Reporter/.
  3. If no config exists yet, attempts to import from .env.
  4. Injects config into os.environ so app.config.Settings() works.
  5. Launches the customtkinter GUI.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def main() -> None:
    """Launch the desktop application."""
    import customtkinter as ctk

    from desktop.config_store import config_exists, load_config, save_config, import_from_dotenv
    from desktop.service_bridge import init_env_from_config

    # --- Load or bootstrap config ---
    if not config_exists():
        dotenv_path = _PROJECT_ROOT / ".env"
        imported = import_from_dotenv(dotenv_path)
        if imported:
            save_config(imported)
            print(f"Imported settings from {dotenv_path}")
        else:
            save_config(load_config())  # save defaults
            print("Created default config — open Settings to configure.")

    config = load_config()

    # --- Inject into environment (must happen BEFORE app.* imports) ---
    init_env_from_config(config)

    # --- Theme ---
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    # --- Launch ---
    from desktop.app_window import AppWindow

    app = AppWindow()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
