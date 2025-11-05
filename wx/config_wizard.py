"""
GUI Configuration Wizard for wx-cli

A user-friendly graphical interface for configuring wx-cli settings.
Uses tkinter (included with Python) for cross-platform GUI support.
"""

from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


class ConfigWizard:
    """GUI wizard for wx-cli configuration."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("wx-cli Configuration Wizard")
        self.root.geometry("600x700")
        self.root.resizable(False, False)

        # Find .env file location
        self.project_root = Path(__file__).parent.parent
        self.env_file = self.project_root / ".env"
        self.env_example = self.project_root / ".env.example"

        # Load existing configuration
        self.config = self._load_existing_config()

        # Create UI
        self._create_ui()

    def _load_existing_config(self) -> dict[str, str]:
        """Load existing .env configuration if it exists."""
        config = {
            "OPENROUTER_API_KEY": "",
            "GEMINI_API_KEY": "",
            "UNITS": "imperial",
            "PRIVACY_MODE": "1",
            "AI_TEMPERATURE": "0.2",
            "AI_MAX_TOKENS": "900",
            "WX_NOTIFICATIONS": "0",
        }

        if self.env_file.exists():
            try:
                with open(self.env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip()
                            if key in config:
                                config[key] = value
            except Exception:  # noqa: BLE001
                pass

        return config

    def _create_ui(self):
        """Create the user interface."""
        # Header
        header_frame = ttk.Frame(self.root, padding="10")
        header_frame.pack(fill=tk.X)

        title_label = ttk.Label(
            header_frame,
            text="🌤️ wx-cli Configuration",
            font=("Arial", 16, "bold"),
        )
        title_label.pack()

        subtitle_label = ttk.Label(
            header_frame,
            text="Configure your weather bot settings",
            font=("Arial", 10),
        )
        subtitle_label.pack()

        # Separator
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Main content frame with scrollbar
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas for scrolling
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # API Keys Section
        self._create_section_header(scrollable_frame, "🔑 API Keys")

        # OpenRouter API Key
        self._create_label(
            scrollable_frame,
            "OpenRouter API Key (Primary):",
            "Get your key at: https://openrouter.ai/keys",
        )
        self.openrouter_entry = self._create_entry(
            scrollable_frame,
            self.config["OPENROUTER_API_KEY"],
            show="*",
        )

        # Gemini API Key
        self._create_label(
            scrollable_frame,
            "Gemini API Key (Optional Fallback):",
            "Get your key at: https://aistudio.google.com/app/apikey",
        )
        self.gemini_entry = self._create_entry(
            scrollable_frame,
            self.config["GEMINI_API_KEY"],
            show="*",
        )

        # Separator
        ttk.Separator(scrollable_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)

        # Preferences Section
        self._create_section_header(scrollable_frame, "⚙️ Preferences")

        # Units
        self._create_label(scrollable_frame, "Temperature Units:")
        units_frame = ttk.Frame(scrollable_frame)
        units_frame.pack(fill=tk.X, padx=20, pady=5)

        self.units_var = tk.StringVar(value=self.config["UNITS"])
        ttk.Radiobutton(
            units_frame,
            text="Imperial (°F, mph)",
            variable=self.units_var,
            value="imperial",
        ).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(
            units_frame,
            text="Metric (°C, m/s)",
            variable=self.units_var,
            value="metric",
        ).pack(side=tk.LEFT, padx=10)

        # Privacy Mode
        privacy_frame = ttk.Frame(scrollable_frame)
        privacy_frame.pack(fill=tk.X, padx=20, pady=10)

        self.privacy_var = tk.BooleanVar(value=self.config["PRIVACY_MODE"] == "1")
        privacy_check = ttk.Checkbutton(
            privacy_frame,
            text="Enable Privacy Mode",
            variable=self.privacy_var,
        )
        privacy_check.pack(side=tk.LEFT)

        privacy_info = ttk.Label(
            privacy_frame,
            text="(Disables history - required for 'wx explain')",
            font=("Arial", 8),
            foreground="gray",
        )
        privacy_info.pack(side=tk.LEFT, padx=10)

        # Windows Notifications (Windows only)
        if sys.platform == "win32":
            notifications_frame = ttk.Frame(scrollable_frame)
            notifications_frame.pack(fill=tk.X, padx=20, pady=10)

            self.notifications_var = tk.BooleanVar(
                value=self.config.get("WX_NOTIFICATIONS", "0") == "1"
            )
            notifications_check = ttk.Checkbutton(
                notifications_frame,
                text="Enable Desktop Notifications",
                variable=self.notifications_var,
            )
            notifications_check.pack(side=tk.LEFT)

            notifications_info = ttk.Label(
                notifications_frame,
                text="(Requires: pip install win10toast)",
                font=("Arial", 8),
                foreground="gray",
            )
            notifications_info.pack(side=tk.LEFT, padx=10)

        # Separator
        ttk.Separator(scrollable_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)

        # Advanced Settings Section
        self._create_section_header(scrollable_frame, "🔧 Advanced Settings")

        # AI Temperature
        self._create_label(
            scrollable_frame,
            "AI Temperature (0.0-2.0):",
            "Lower = more focused, Higher = more creative",
        )
        temp_frame = ttk.Frame(scrollable_frame)
        temp_frame.pack(fill=tk.X, padx=20, pady=5)

        self.temperature_var = tk.StringVar(value=self.config["AI_TEMPERATURE"])
        self.temperature_entry = ttk.Entry(temp_frame, textvariable=self.temperature_var, width=10)
        self.temperature_entry.pack(side=tk.LEFT, padx=5)

        temp_label = ttk.Label(temp_frame, text="(Default: 0.2)", font=("Arial", 8), foreground="gray")
        temp_label.pack(side=tk.LEFT, padx=5)

        # AI Max Tokens
        self._create_label(
            scrollable_frame,
            "Max Response Tokens:",
            "Higher = longer responses (costs more)",
        )
        tokens_frame = ttk.Frame(scrollable_frame)
        tokens_frame.pack(fill=tk.X, padx=20, pady=5)

        self.max_tokens_var = tk.StringVar(value=self.config["AI_MAX_TOKENS"])
        self.max_tokens_entry = ttk.Entry(tokens_frame, textvariable=self.max_tokens_var, width=10)
        self.max_tokens_entry.pack(side=tk.LEFT, padx=5)

        tokens_label = ttk.Label(
            tokens_frame, text="(Default: 900)", font=("Arial", 8), foreground="gray"
        )
        tokens_label.pack(side=tk.LEFT, padx=5)

        # Spacer
        ttk.Frame(scrollable_frame, height=20).pack()

        # Button Frame
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # Buttons
        test_button = ttk.Button(
            button_frame,
            text="Test Connection",
            command=self._test_connection,
        )
        test_button.pack(side=tk.LEFT, padx=5)

        save_button = ttk.Button(
            button_frame,
            text="Save Configuration",
            command=self._save_config,
        )
        save_button.pack(side=tk.RIGHT, padx=5)

        cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.root.quit,
        )
        cancel_button.pack(side=tk.RIGHT, padx=5)

        reset_button = ttk.Button(
            button_frame,
            text="Reset to Defaults",
            command=self._reset_defaults,
        )
        reset_button.pack(side=tk.LEFT, padx=5)

    def _create_section_header(self, parent: ttk.Frame, text: str):
        """Create a section header."""
        label = ttk.Label(
            parent,
            text=text,
            font=("Arial", 12, "bold"),
        )
        label.pack(anchor=tk.W, padx=10, pady=(10, 5))

    def _create_label(self, parent: ttk.Frame, text: str, subtext: str | None = None):
        """Create a label with optional subtext."""
        label = ttk.Label(parent, text=text, font=("Arial", 10))
        label.pack(anchor=tk.W, padx=20, pady=(10, 2))

        if subtext:
            sublabel = ttk.Label(
                parent,
                text=subtext,
                font=("Arial", 8),
                foreground="gray",
            )
            sublabel.pack(anchor=tk.W, padx=20)

    def _create_entry(self, parent: ttk.Frame, default_value: str, show: str | None = None) -> ttk.Entry:
        """Create an entry field."""
        entry = ttk.Entry(parent, width=50, show=show)
        entry.insert(0, default_value)
        entry.pack(anchor=tk.W, padx=20, pady=5)
        return entry

    def _validate_config(self) -> tuple[bool, str]:
        """Validate configuration values."""
        openrouter_key = self.openrouter_entry.get().strip()

        # Check if at least one API key is provided
        gemini_key = self.gemini_entry.get().strip()
        if not openrouter_key and not gemini_key:
            return False, "Please provide at least one API key (OpenRouter or Gemini)"

        # Validate API key format
        if openrouter_key and len(openrouter_key) < 20:
            return False, "OpenRouter API key appears too short (should be 20+ characters)"

        if gemini_key and len(gemini_key) < 20:
            return False, "Gemini API key appears too short (should be 20+ characters)"

        # Validate temperature
        try:
            temp = float(self.temperature_var.get())
            if not (0.0 <= temp <= 2.0):
                return False, "AI Temperature must be between 0.0 and 2.0"
        except ValueError:
            return False, "AI Temperature must be a valid number"

        # Validate max tokens
        try:
            tokens = int(self.max_tokens_var.get())
            if tokens < 100 or tokens > 4000:
                return False, "Max Tokens must be between 100 and 4000"
        except ValueError:
            return False, "Max Tokens must be a valid integer"

        return True, ""

    def _save_config(self):
        """Save configuration to .env file."""
        # Validate first
        valid, error_msg = self._validate_config()
        if not valid:
            messagebox.showerror("Validation Error", error_msg)
            return

        try:
            # Read template or existing file
            if self.env_file.exists():
                with open(self.env_file) as f:
                    lines = f.readlines()
            elif self.env_example.exists():
                with open(self.env_example) as f:
                    lines = f.readlines()
            else:
                lines = []

            # Update configuration values
            config_updates = {
                "OPENROUTER_API_KEY": self.openrouter_entry.get().strip(),
                "GEMINI_API_KEY": self.gemini_entry.get().strip(),
                "UNITS": self.units_var.get(),
                "PRIVACY_MODE": "1" if self.privacy_var.get() else "0",
                "AI_TEMPERATURE": self.temperature_var.get(),
                "AI_MAX_TOKENS": self.max_tokens_var.get(),
            }

            if sys.platform == "win32":
                config_updates["WX_NOTIFICATIONS"] = "1" if self.notifications_var.get() else "0"

            # Update existing lines or add new ones
            updated_keys = set()
            new_lines = []

            for line in lines:
                original_line = line
                if line.strip() and not line.strip().startswith("#") and "=" in line:
                    key = line.split("=", 1)[0].strip()
                    if key in config_updates:
                        new_lines.append(f"{key}={config_updates[key]}\n")
                        updated_keys.add(key)
                    else:
                        new_lines.append(original_line)
                else:
                    new_lines.append(original_line)

            # Add any keys that weren't in the file
            for key, value in config_updates.items():
                if key not in updated_keys:
                    new_lines.append(f"{key}={value}\n")

            # Write to file
            with open(self.env_file, "w") as f:
                f.writelines(new_lines)

            messagebox.showinfo(
                "Success",
                f"Configuration saved to:\n{self.env_file}\n\n"
                "You can now use wx-cli with your settings!",
            )

            self.root.quit()

        except Exception as e:  # noqa: BLE001
            messagebox.showerror(
                "Error",
                f"Failed to save configuration:\n{e}",
            )

    def _test_connection(self):
        """Test API connection."""
        openrouter_key = self.openrouter_entry.get().strip()
        gemini_key = self.gemini_entry.get().strip()

        if not openrouter_key and not gemini_key:
            messagebox.showwarning(
                "No API Keys",
                "Please enter at least one API key before testing.",
            )
            return

        # Simple validation test
        result_messages = []

        if openrouter_key:
            if len(openrouter_key) >= 20:
                result_messages.append("✓ OpenRouter key format looks valid")
            else:
                result_messages.append("✗ OpenRouter key appears too short")

        if gemini_key:
            if len(gemini_key) >= 20:
                result_messages.append("✓ Gemini key format looks valid")
            else:
                result_messages.append("✗ Gemini key appears too short")

        messagebox.showinfo(
            "Connection Test",
            "\n".join(result_messages)
            + "\n\nNote: Full API validation happens when you run wx commands.",
        )

    def _reset_defaults(self):
        """Reset all fields to default values."""
        if messagebox.askyesno(
            "Reset to Defaults",
            "Are you sure you want to reset all settings to defaults?\n\n"
            "Your API keys will be cleared.",
        ):
            self.openrouter_entry.delete(0, tk.END)
            self.gemini_entry.delete(0, tk.END)
            self.units_var.set("imperial")
            self.privacy_var.set(True)
            self.temperature_var.set("0.2")
            self.max_tokens_var.set("900")
            if sys.platform == "win32":
                self.notifications_var.set(False)


def main():
    """Run the configuration wizard."""
    root = tk.Tk()

    # Set icon if available (optional)
    try:
        if sys.platform == "win32":
            root.iconbitmap(default="wx.ico")
    except Exception:  # noqa: BLE001
        pass

    # Create wizard
    wizard = ConfigWizard(root)

    # Center window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")

    # Run
    root.mainloop()


if __name__ == "__main__":
    main()
