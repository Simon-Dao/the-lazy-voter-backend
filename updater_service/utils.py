import requests
import time
from threading import Lock
import json

class Request:
    def __init__(self):
        self.LAST_CALL_TIME = 0.0
        self.rate_lock = Lock()
        self.call_number = 0

    def _rate_limit(self, RATE_LIMIT_SECONDS):
        with self.rate_lock:
            now = time.time()
            elapsed = now - self.LAST_CALL_TIME
            if elapsed < RATE_LIMIT_SECONDS:
                time.sleep(RATE_LIMIT_SECONDS - elapsed)
            self.LAST_CALL_TIME = time.time()

    def safe_request(self, url, headers={"Accept": "application/json"}):
        while True:

            if "api.open.fec" in url:
                self._rate_limit(6)
            else:
                self._rate_limit(1.2)
            try:
                resp = requests.get(url, headers=headers, timeout=10)

                if headers.get('Accept') == 'application/xml':
                    return resp

                resp.raise_for_status()
                self.call_number += 1
                return resp.json()
            except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                print(f"Request failed, retrying... Error: {e} | URL: {url}")
                time.sleep(1)  # brief wait before retrying

    def safe_request_params(self, url, headers={"Accept": "application/json"}, params={}):
        while True:
            self._rate_limit()
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=10)

                if headers.get('Accept') == 'application/xml':
                    return resp

                resp.raise_for_status()
                self.call_number += 1
                return resp.json()
            except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                print(f"Request with params failed, retrying... Error: {e} | URL: {url}")
                time.sleep(1)  # brief wait before retrying