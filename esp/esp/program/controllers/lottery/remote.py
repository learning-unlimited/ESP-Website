"""Thin HTTP client for the remote solver service (a separate repo/deploy,
see lottery-solver-service). Ships a built model file + solve-control params,
polls for status, and fetches the resulting sparse solution.
"""
import json

import requests

from .base import LotteryException


class RemoteSolverError(LotteryException):
    """The solver service returned an error, or couldn't be reached."""


class RemoteSolverClient:
    def __init__(self, url, token, verify=True, connect_timeout=2, read_timeout=5):
        self.base_url = url.rstrip("/")
        self.token = token
        self.verify = verify
        self.timeout = (connect_timeout, read_timeout)

    def _headers(self):
        return {"Authorization": "Bearer %s" % self.token}

    def _request(self, method, path, **kwargs):
        url = "%s%s" % (self.base_url, path)
        try:
            resp = requests.request(
                method, url, headers=self._headers(), timeout=self.timeout, verify=self.verify, **kwargs
            )
        except requests.RequestException as e:
            raise RemoteSolverError("could not reach solver service at %s: %s" % (url, e))
        if resp.status_code >= 400:
            raise RemoteSolverError(
                "solver service returned %s for %s %s: %s" % (resp.status_code, method, path, resp.text)
            )
        return resp

    def submit(self, model_bytes, params):
        """Returns {"job_id": ..., "status": "queued"}."""
        resp = self._request(
            "POST",
            "/v1/jobs/submit",
            files={"model": ("model.mps.gz", model_bytes, "application/gzip")},
            data={"params": json.dumps(params)},
        )
        return resp.json()

    def status(self, job_id):
        """Returns {"status": ..., "progress": [...], "error"?: ...}."""
        return self._request("GET", "/v1/jobs/%s/status" % job_id).json()

    def solution(self, job_id):
        """Returns the sparse {varname: value} solution, or None if no
        incumbent exists yet."""
        url = "%s/v1/jobs/%s/solution" % (self.base_url, job_id)
        try:
            resp = requests.get(url, headers=self._headers(), timeout=self.timeout, verify=self.verify)
        except requests.RequestException as e:
            raise RemoteSolverError("could not reach solver service at %s: %s" % (url, e))
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise RemoteSolverError("solver service returned %s for GET solution: %s" % (resp.status_code, resp.text))
        return resp.json()

    def input(self, job_id):
        return self._request("GET", "/v1/jobs/%s/input" % job_id).json()

    def model_bytes(self, job_id):
        return self._request("GET", "/v1/jobs/%s/model" % job_id).content

    def stop(self, job_id):
        return self._request("POST", "/v1/jobs/%s/stop" % job_id).json()

    def delete(self, job_id):
        return self._request("DELETE", "/v1/jobs/%s" % job_id).json()
