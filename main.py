"""Windows Startup Launcher — GUI application with tkinter."""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any

from config_manager import get_app_dir, load_config, save_config
from launcher import launch_all, launch_command, restart_all, setup_logging, stop_all
from tray_icon import TrayManager

# ---------------------------------------------------------------------------
# Registry helpers (Windows-only)
# ---------------------------------------------------------------------------

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_VALUE = "StartupLauncher"


def _get_exe_path() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(__file__)


def is_auto_start_enabled() -> bool:
    if os.name != "nt":
        return False
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, REG_VALUE)
        winreg.CloseKey(key)
        return True
    except (FileNotFoundError, OSError):
        return False


def set_auto_start(enabled: bool) -> None:
    if os.name != "nt":
        return
    import winreg
    if enabled:
        exe = _get_exe_path()
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_KEY)
        winreg.SetValueEx(key, REG_VALUE, 0, winreg.REG_SZ, f'"{exe}"')
        winreg.CloseKey(key)
    else:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, REG_VALUE)
            winreg.CloseKey(key)
        except FileNotFoundError:
            pass


# ---------------------------------------------------------------------------
# Edit dialog
# ---------------------------------------------------------------------------

class CommandEditDialog(tk.Toplevel):
    """Modal dialog for adding/editing a command entry."""

    def __init__(self, parent: tk.Widget, entry: dict[str, Any] | None = None) -> None:
        super().__init__(parent)
        self.title("Edit Command" if entry else "Add Command")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result: dict[str, Any] | None = None
        e = entry or {}

        frame = ttk.Frame(self, padding=12)
        frame.grid(sticky="nsew")

        fields = [
            ("Name:", "name"),
            ("Command:", "command"),
            ("Arguments:", "args"),
            ("Working Dir:", "workdir"),
            ("Delay (sec):", "delay_seconds"),
        ]
        self.vars: dict[str, tk.StringVar] = {}
        for i, (label, key) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="e", pady=2)
            var = tk.StringVar(value=str(e.get(key, "")))
            ttk.Entry(frame, textvariable=var, width=40).grid(row=i, column=1, padx=(6, 0), pady=2)
            self.vars[key] = var

        # Checkboxes
        chk_row = len(fields)
        self.enabled_var = tk.BooleanVar(value=e.get("enabled", True))
        ttk.Checkbutton(frame, text="Enabled", variable=self.enabled_var).grid(
            row=chk_row, column=1, sticky="w", pady=2
        )
        self.minimized_var = tk.BooleanVar(value=e.get("run_minimized", False))
        ttk.Checkbutton(frame, text="Run Minimized", variable=self.minimized_var).grid(
            row=chk_row + 1, column=1, sticky="w", pady=2
        )

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=chk_row + 2, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(btn_frame, text="OK", command=self._ok).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=4)

        self.bind("<Return>", lambda _: self._ok())
        self.bind("<Escape>", lambda _: self.destroy())
        self.wait_window()

    def _ok(self) -> None:
        try:
            delay = int(self.vars["delay_seconds"].get() or 0)
        except ValueError:
            delay = 0
        self.result = {
            "name": self.vars["name"].get().strip(),
            "command": self.vars["command"].get().strip(),
            "args": self.vars["args"].get().strip(),
            "workdir": self.vars["workdir"].get().strip(),
            "enabled": self.enabled_var.get(),
            "delay_seconds": delay,
            "run_minimized": self.minimized_var.get(),
        }
        self.destroy()


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class StartupLauncherApp:
    def __init__(self) -> None:
        self.app_dir = get_app_dir()
        setup_logging(self.app_dir)
        self.config = load_config()
        self.tray = TrayManager(
            on_open=self._show_window,
            on_quit=self._quit,
            on_restart_all=self._restart_all,
            on_stop_all=self._stop_all,
        )

        self.root = tk.Tk()
        self.root.title("Startup Launcher")
        self.root.geometry("700x450")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._refresh_list()
        self._update_auto_start_label()

        # Launch configured commands on startup
        failures: list[tuple[str, str]] = []

        def _on_fail(name: str, msg: str) -> None:
            failures.append((name, msg))
            self.tray.notify("Launch Failed", f"{name}: {msg}")

        launch_all(self.config.get("commands", []), on_failure=_on_fail)

        # Minimize to tray after launching if configured
        if self.config.get("minimize_to_tray", True) and self.tray.available:
            self.tray.start()
            self.root.withdraw()

    # ---- UI construction ----

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill="x")

        self.auto_start_label = ttk.Label(top, text="Auto-start: checking...")
        self.auto_start_label.pack(side="left")

        self.auto_start_btn = ttk.Button(top, text="Toggle Auto-Start", command=self._toggle_auto_start)
        self.auto_start_btn.pack(side="left", padx=(10, 0))

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=8)

        cols = ("name", "command", "delay", "enabled")
        self.tree = ttk.Treeview(self.root, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("name", text="Name")
        self.tree.heading("command", text="Command")
        self.tree.heading("delay", text="Delay (s)")
        self.tree.heading("enabled", text="Enabled")
        self.tree.column("name", width=140)
        self.tree.column("command", width=300)
        self.tree.column("delay", width=70, anchor="center")
        self.tree.column("enabled", width=70, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=8, pady=(8, 0))

        btn_bar = ttk.Frame(self.root, padding=8)
        btn_bar.pack(fill="x")
        ttk.Button(btn_bar, text="Add", command=self._add).pack(side="left", padx=2)
        ttk.Button(btn_bar, text="Edit", command=self._edit).pack(side="left", padx=2)
        ttk.Button(btn_bar, text="Remove", command=self._remove).pack(side="left", padx=2)
        ttk.Button(btn_bar, text="Test Run", command=self._test_run).pack(side="left", padx=2)
        ttk.Button(btn_bar, text="Save", command=self._save).pack(side="right", padx=2)

    def _refresh_list(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, cmd in enumerate(self.config.get("commands", [])):
            self.tree.insert("", "end", iid=str(idx), values=(
                cmd.get("name", ""),
                cmd.get("command", ""),
                cmd.get("delay_seconds", 0),
                "Yes" if cmd.get("enabled", True) else "No",
            ))

    # ---- Actions ----

    def _selected_index(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            return None
        return int(sel[0])

    def _add(self) -> None:
        dlg = CommandEditDialog(self.root)
        if dlg.result:
            self.config.setdefault("commands", []).append(dlg.result)
            self._refresh_list()

    def _edit(self) -> None:
        idx = self._selected_index()
        if idx is None:
            messagebox.showinfo("Info", "Select an entry first.")
            return
        dlg = CommandEditDialog(self.root, self.config["commands"][idx])
        if dlg.result:
            self.config["commands"][idx] = dlg.result
            self._refresh_list()

    def _remove(self) -> None:
        idx = self._selected_index()
        if idx is None:
            messagebox.showinfo("Info", "Select an entry first.")
            return
        del self.config["commands"][idx]
        self._refresh_list()

    def _test_run(self) -> None:
        idx = self._selected_index()
        if idx is None:
            messagebox.showinfo("Info", "Select an entry first.")
            return
        entry = self.config["commands"][idx]

        def _on_fail(name: str, msg: str) -> None:
            self.tray.notify("Test Failed", f"{name}: {msg}")

        launch_command(entry, on_failure=_on_fail)

    def _save(self) -> None:
        save_config(self.config)
        messagebox.showinfo("Saved", "Configuration saved.")

    # ---- Auto-start ----

    def _update_auto_start_label(self) -> None:
        enabled = is_auto_start_enabled()
        status = "ON" if enabled else "OFF"
        self.auto_start_label.config(text=f"Auto-start: {status}")

    def _toggle_auto_start(self) -> None:
        current = is_auto_start_enabled()
        set_auto_start(not current)
        self._update_auto_start_label()

    # ---- Window / tray ----

    def _on_close(self) -> None:
        if self.config.get("minimize_to_tray", True) and self.tray.available:
            self.root.withdraw()
        else:
            self._quit()

    def _show_window(self) -> None:
        self.root.deiconify()
        self.root.lift()

    def _restart_all(self) -> None:
        """Stop all managed processes and relaunch them respecting delays."""
        restart_all(self.config.get("commands", []))

    def _stop_all(self) -> None:
        """Stop all managed processes without restarting."""
        stop_all()

    def _quit(self) -> None:
        stop_all()
        self.tray.stop()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = StartupLauncherApp()
    app.run()