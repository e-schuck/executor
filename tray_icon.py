"""System tray icon integration using pystray + Pillow."""

import logging
import sys
import threading
from typing import Any, Callable

logger = logging.getLogger("StartupLauncher")

try:
    import pystray
    from PIL import Image, ImageDraw

    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False


def _create_default_icon() -> "Image.Image":
    """Generate a simple colored icon programmatically."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Green circle with white play triangle — startup/launcher theme
    draw.ellipse([4, 4, 60, 60], fill=(34, 139, 34, 255))
    draw.polygon([(22, 14), (22, 50), (48, 32)], fill=(255, 255, 255, 255))
    return img


class TrayManager:
    """Manages the system tray icon lifecycle."""

    def __init__(
        self,
        on_open: Callable[[], None] | None = None,
        on_quit: Callable[[], None] | None = None,
        on_restart_all: Callable[[], None] | None = None,
        on_stop_all: Callable[[], None] | None = None,
    ) -> None:
        self._icon: Any = None
        self._thread: threading.Thread | None = None
        self._on_open = on_open
        self._on_quit = on_quit
        self._on_restart_all = on_restart_all
        self._on_stop_all = on_stop_all

    @property
    def available(self) -> bool:
        return HAS_TRAY

    def start(self) -> None:
        if not HAS_TRAY:
            return
        menu = pystray.Menu(
            pystray.MenuItem(
                "Reiniciar todos os processos",
                lambda: self._safe_call("restart_all", self._on_restart_all),
            ),
            pystray.MenuItem(
                "Encerrar todos os processos",
                lambda: self._safe_call("stop_all", self._on_stop_all),
            ),
            pystray.MenuItem(
                "Abrir painel",
                lambda: self._safe_call("open_panel", self._on_open),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Fechar programa",
                lambda: self._handle_quit(),
            ),
        )
        self._icon = pystray.Icon(
            "StartupLauncher",
            icon=_create_default_icon(),
            title="Startup Launcher",
            menu=menu,
        )
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None

    def notify(self, title: str, message: str) -> None:
        """Show a balloon notification (Windows only via pystray)."""
        if self._icon:
            try:
                self._icon.notify(message, title)
            except Exception:
                pass

    def _safe_call(self, action_name: str, callback: Callable[[], None] | None) -> None:
        """Invoke a tray callback with error handling and logging."""
        if callback is None:
            logger.warning("Tray action '%s': no callback registered", action_name)
            return
        try:
            logger.info("Tray action triggered: %s", action_name)
            callback()
        except Exception as e:
            logger.error("Tray action '%s' failed: %s", action_name, e, exc_info=True)

    def _handle_quit(self) -> None:
        """Stop all processes, hide tray icon, and exit the application."""
        logger.info("Tray action triggered: quit")
        try:
            if self._on_stop_all:
                self._on_stop_all()
        except Exception as e:
            logger.error("Error stopping processes during quit: %s", e, exc_info=True)
        try:
            self.stop()
        except Exception as e:
            logger.error("Error stopping tray icon during quit: %s", e, exc_info=True)
        logger.info("Exiting application via tray menu")
        sys.exit(0)