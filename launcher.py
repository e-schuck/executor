"""Subprocess launcher with delay support and logging."""

import logging
import os
import subprocess
import threading
import time
from typing import Any

logger = logging.getLogger("StartupLauncher")


def setup_logging(app_dir: str) -> None:
    """Configure file + console logging."""
    log_path = os.path.join(app_dir, "startup_launcher.log")
    handlers: list[logging.Handler] = [
        logging.FileHandler(log_path, encoding="utf-8"),
    ]
    # Only add console handler when not frozen (dev mode)
    import sys
    if not getattr(sys, "frozen", False):
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=True,
    )


def launch_command(entry: dict[str, Any], on_failure: Any | None = None) -> None:
    """Launch a single command entry in a background thread."""
    name = entry.get("name", "Unknown")
    command = entry.get("command", "")
    args = entry.get("args", "")
    workdir = entry.get("workdir", "")
    delay = entry.get("delay_seconds", 0)
    run_minimized = entry.get("run_minimized", False)

    if not command:
        logger.warning("[%s] Skipping: empty command", name)
        return

    def _run() -> None:
        if delay > 0:
            logger.info("[%s] Waiting %d seconds before launch...", name, delay)
            time.sleep(delay)

        cmd_parts = [command]
        if args:
            cmd_parts.extend(args.split())

        kwargs: dict[str, Any] = {}
        if workdir and os.path.isdir(workdir):
            kwargs["cwd"] = workdir

        # On Windows, use CREATE_NO_WINDOW flag if run_minimized
        if os.name == "nt":
            import ctypes
            CREATE_NO_WINDOW = 0x08000000
            if run_minimized:
                kwargs["creationflags"] = CREATE_NO_WINDOW

        try:
            logger.info("[%s] Starting: %s", name, " ".join(cmd_parts))
            subprocess.Popen(cmd_parts, **kwargs)
            logger.info("[%s] Launched successfully", name)
        except FileNotFoundError:
            msg = f"[{name}] Command not found: {command}"
            logger.error(msg)
            if on_failure:
                on_failure(name, msg)
        except PermissionError:
            msg = f"[{name}] Permission denied: {command}"
            logger.error(msg)
            if on_failure:
                on_failure(name, msg)
        except OSError as e:
            msg = f"[{name}] OS error: {e}"
            logger.error(msg)
            if on_failure:
                on_failure(name, msg)
        except Exception as e:
            msg = f"[{name}] Unexpected error: {e}"
            logger.error(msg)
            if on_failure:
                on_failure(name, msg)

    thread = threading.Thread(target=_run, daemon=True, name=f"launch-{name}")
    thread.start()


def launch_all(commands: list[dict[str, Any]], on_failure: Any | None = None) -> None:
    """Launch all enabled commands."""
    enabled = [c for c in commands if c.get("enabled", True)]
    logger.info("Launching %d enabled command(s)...", len(enabled))
    for entry in enabled:
        launch_command(entry, on_failure=on_failure)