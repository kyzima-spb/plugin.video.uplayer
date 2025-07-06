from kodi_useful import current_addon
import xbmc

from .webserver import httpd


class Monitor(xbmc.Monitor):
    def __init__(self):
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
        self._update_httpd_status()

    def stop(self):
        httpd.stop()


def run():
    monitor = Monitor()

    while not monitor.abortRequested():
        # Sleep/wait for abort for 10 seconds
        if monitor.waitForAbort(10):
            # Abort was requested while waiting. We should exit
            break

    monitor.stop()
