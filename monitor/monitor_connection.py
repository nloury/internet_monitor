import requests
import socket
import datetime as dt
import time
import random
from app.utils.log import CustomLogging


class MonitorConnection:
    """Ping internet connection to check for downtime every n seconds"""
    def __init__(self,
                 check_seconds: int=60,
                 check_seconds_when_down: int=3,
                 ):
        self._logger = CustomLogging('internet_monitor')
        self._check_seconds = check_seconds
        self._check_seconds_when_down = check_seconds_when_down

        # monitoring variables
        self._connected: bool | None = None
        self._outage_timestamp: dt.datetime | None = None

        # targets for monitoring checks
        self._tcp_targets = [
            ('1.1.1.1', 443),
            ('8.8.8.8', 53),
            ('9.9.9.9', 53)
        ]
        self._http_targets = [
            ('https://www.google.com/generate_204', 204, None),
            ('http://detectportal.firefox.com/success.txt', 200, 'success\n'),
        ]

    def run_monitor(self):
        """Continuously monitor internet connection"""
        self._logger.add_log(
            override_message=f'Starting internet connection monitor: checking every {self._check_seconds} seconds',
            level='debug')

        while True:
            connected, detail = self._check_connection()
            checked_at = dt.datetime.now()

            # check if first connection attempt
            if self._connected is None:
                log_message = f'Initial connection check: connection is {"up" if connected else "down"} ({detail})'
                self._logger.add_log(override_message=log_message,level='info')

                self._connected = connected
                if not connected: self._outage_timestamp = checked_at

            # check if connection state has changed
            elif connected != self._connected:
                if connected:  # connection restored
                    # since not first connection, connected + state change = outage stamp is set > don't need to check
                    outage_duration = (checked_at - self._outage_timestamp).total_seconds()
                    self._logger.add_log(
                        override_message=f'Internet connection restored after outage of {outage_duration:.1f} seconds ({detail})',
                        level='info')

                    self._outage_timestamp = None  # reset outage timestamp
                else:  # connection lost
                    self._logger.add_log(override_message=f'Internet connection lost {detail}', level='warning')
                    self._outage_timestamp = checked_at

            self._connected = connected  # update connection state

            # wait until next check
            sleep_time = self._check_seconds if connected else self._check_seconds_when_down
            sleep_jitter = random.uniform(0, sleep_time * 0.2)  # add up to 20% jitter to avoid exact intervals
            time.sleep(sleep_time + sleep_jitter)

    def _check_connection(self) -> tuple[bool, str]:
        """Check internet connection via TCP and HTTP checks"""
        # check TCP reachability
        for n, (host, port) in enumerate(self._tcp_targets, start=1):
            try:
                with socket.create_connection((host, port), timeout=2):
                    return True, f'#{n} tcp:{host}:{port}'
            except OSError:
                pass

        # if TCP fails, check HTTP reachability
        for n, (url, expected_status, expected_body) in enumerate(self._http_targets, start=1):
            try:
                r = requests.head(url, timeout=4, allow_redirects=False)
                if r.status_code == expected_status and expected_body is None:
                    return True, f'#{n} http:{url}'
                if r.status_code in (405, 501) or expected_body is not None:
                    r = requests.get(url, timeout=4, allow_redirects=False)
                    if r.status_code == expected_status and (expected_body is None or r.text == expected_body):
                        return True, f'#{n} http:{url}'
            except requests.RequestException:
                pass

        return False, 'no tcp targets or http checks reachable'
