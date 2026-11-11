"""System tray icon integration using pystray + Pillow."""

import threading
from typing import Any, Callable

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
    ) -> None:
        self._icon: Any = None
        self._thread: threading.Thread | None = None
        self._on_open = on_open
        self._on_quit = on_quit

    @property
    def available(self) -> bool:
        return HAS_TRAY

    def start(self) -> None:
        if not HAS_TRAY:
            return
        menu = pystray.Menu(
            pystray.MenuItem("Open", lambda: self._on_open and self._on_open()),
            pystray.MenuItem("Quit", lambda: self._on_quit and self._on_quit()),
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
            self._icon.stop()
            self._icon = None

    def notify(self, title: str, message: str) -> None:
        """Show a balloon notification (Windows only via pystray)."""
        if self._icon:
            try:
                self._icon.notify(message, title)
            except Exception:
                pass