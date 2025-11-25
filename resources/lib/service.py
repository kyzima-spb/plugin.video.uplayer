import time

from kodi_useful import current_addon
import xbmc

from .webserver import httpd


class Monitor(xbmc.Monitor):
    def __init__(self):
        self._pending = False
        self._last_changed = 0
        self._update_httpd_status()

    def _update_httpd_status(self):
        httpd.set_address(
            current_addon.get_setting('httpd.host'),
            current_addon.get_setting('httpd.port', int),
        )

        if not current_addon.get_setting('httpd.enabled', bool):
            httpd.stop()
        elif httpd.is_running():
            httpd.restart()
        else:
            httpd.start(run_in_thread=True)

    def onSettingsChanged(self) -> None:
        self._pending = True
        self._last_changed = time.time()

    def process_pending_changes(self) -> None:
        if self._pending and time.time() - self._last_changed >= 3:
            self._pending = False
            self._update_httpd_status()

    def stop(self):
        httpd.stop()


def run():
    monitor = Monitor()

    while not monitor.abortRequested():
        monitor.process_pending_changes()

        if monitor.waitForAbort(.5):
            break

    monitor.stop()
