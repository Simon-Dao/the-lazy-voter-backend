import requests
import time
import random
import logging
from threading import Lock
import json

logger = logging.getLogger(__name__)

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
    def _do_get(self, url, headers, params=None, timeout=10):
        # wrapper for requests.get
        return requests.get(url, headers=headers, params=params, timeout=timeout)

    def safe_request(self, url, headers=None, max_retries=5, timeout=10):
        headers = headers or {"Accept": "application/json"}
        attempts = 0
        while attempts < max_retries:
            attempts += 1

            if "api.open.fec" in url:
                self._rate_limit(6)
            else:
                self._rate_limit(1.2)
            try:
                resp = self._do_get(url, headers=headers, timeout=timeout)

                if headers.get('Accept') == 'application/xml':
                    return resp

                resp.raise_for_status()
                self.call_number += 1
                try:
                    return resp.json()
                except json.JSONDecodeError:
                    logger.warning("Failed to decode JSON response (URL: %s)", url)
                    raise
            except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                logger.warning("Request failed (attempt %d/%d) for URL %s: %s", attempts, max_retries, url, e)
                backoff = min(60, 2 ** attempts) + random.random()
                time.sleep(backoff)
        logger.error("Max retries exceeded for URL: %s", url)
        raise RuntimeError(f"Failed to fetch: {url}")

    def safe_request_params(self, url, headers=None, params=None, max_retries=5, timeout=10):
        headers = headers or {"Accept": "application/json"}
        params = params or {}
        attempts = 0
        while attempts < max_retries:
            attempts += 1
            if "api.open.fec" in url:
                self._rate_limit(6)
            else:
                self._rate_limit(1.2)
            try:
                resp = self._do_get(url, headers=headers, params=params, timeout=timeout)

                if headers.get('Accept') == 'application/xml':
                    return resp

                resp.raise_for_status()
                self.call_number += 1
                try:
                    return resp.json()
                except json.JSONDecodeError:
                    logger.warning("Failed to decode JSON response with params (URL: %s)", url)
                    raise
            except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                logger.warning("Request with params failed (attempt %d/%d) for URL %s: %s", attempts, max_retries, url, e)
                backoff = min(60, 2 ** attempts) + random.random()
                time.sleep(backoff)
        logger.error("Max retries exceeded for URL with params: %s", url)
        raise RuntimeError(f"Failed to fetch with params: {url}")