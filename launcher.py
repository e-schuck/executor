"""Subprocess launcher with delay support, process tracking, and logging."""

import logging
import os
import signal
import subprocess
import threading
import time
from typing import Any

logger = logging.getLogger("StartupLauncher")

# Global registry of tracked subprocesses keyed by command name
_tracked_processes: dict[str, subprocess.Popen] = {}
_lock = threading.Lock()


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


def _kill_process(name: str, proc: subprocess.Popen) -> None:
    """Terminate a single tracked process, handling edge cases."""
    try:
        if proc.poll() is not None:
            logger.info("[%s] Process already exited (pid=%s)", name, proc.pid)
            return
        logger.info("[%s] Terminating process (pid=%s)...", name, proc.pid)
        proc.terminate()
        try:
            proc.wait(timeout=5)
            logger.info("[%s] Process terminated gracefully", name)
        except subprocess.TimeoutExpired:
            logger.warning("[%s] Process did not exit in 5s, force killing...", name)
            proc.kill()
            proc.wait(timeout=3)
            logger.info("[%s] Process force killed", name)
    except PermissionError:
        logger.error("[%s] Permission denied when trying to kill process", name)
    except OSError as e:
        logger.error("[%s] OS error killing process: %s", name, e)
    except Exception as e:
        logger.error("[%s] Unexpected error killing process: %s", name, e)


def stop_all() -> None:
    """Kill all tracked managed processes."""
    with _lock:
        if not _tracked_processes:
            logger.info("stop_all: no tracked processes to stop")
            return
        logger.info("stop_all: stopping %d tracked process(es)...", len(_tracked_processes))
        for name, proc in list(_tracked_processes.items()):
            _kill_process(name, proc)
        _tracked_processes.clear()
    logger.info("stop_all: all processes stopped")


def restart_all(commands: list[dict[str, Any]], on_failure: Any | None = None) -> None:
    """Stop all tracked processes, then relaunch enabled commands respecting delays."""
    logger.info("restart_all: beginning restart cycle")
    stop_all()
    launch_all(commands, on_failure=on_failure)
    logger.info("restart_all: restart cycle complete")


def launch_command(entry: dict[str, Any], on_failure: Any | None = None) -> None:
    """Launch a single command entry in a background thread and track its process."""
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
            CREATE_NO_WINDOW = 0x08000000
            if run_minimized:
                kwargs["creationflags"] = CREATE_NO_WINDOW

        try:
            logger.info("[%s] Starting: %s", name, " ".join(cmd_parts))
            proc = subprocess.Popen(cmd_parts, **kwargs)
            with _lock:
                # If a previous process with same name exists, kill it first
                old = _tracked_processes.get(name)
                if old is not None and old.poll() is None:
                    _kill_process(name, old)
                _tracked_processes[name] = proc
            logger.info("[%s] Launched successfully (pid=%s)", name, proc.pid)
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