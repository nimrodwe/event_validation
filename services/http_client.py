"""HTTP client — GET/POST with timeout and retries."""

import time

import requests

from services.http_status import HttpStatus


class HttpClient:
    def __init__(self, timeout=5, retries=3, backoff=0.5):
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff

    def request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        last_error = None

        for attempt in range(1, self.retries + 1):
            try:
                response = requests.request(method, url, **kwargs)
                # Retry transient server errors; return other responses as-is.
                if response.status_code >= HttpStatus.SERVER_ERROR_MIN and attempt < self.retries:
                    time.sleep(self.backoff * attempt)
                    continue
                return response
            except (requests.Timeout, requests.ConnectionError) as err:
                last_error = err
                if attempt >= self.retries:
                    raise
                time.sleep(self.backoff * attempt)

        if last_error is not None:
            raise last_error
        raise RuntimeError("HTTP request failed after retries: " + method + " " + url)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)
