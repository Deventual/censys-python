import json
import os
import unittest

import requests


class CensysException(Exception):

    def __init__(self, status_code, message, headers=None, body=None, const=None):
        self.status_code = status_code
        self.message = message
        self.headers = headers or {}
        self.body = body
        self.const = const

    def __repr__(self):
        return "%i (%s): %s" % (self.status_code, self.const, self.message or self.body)

    __str__ = __repr__


class CensysRateLimitExceededException(CensysException):
    pass


class CensysNotFoundException(CensysException):
    pass


class CensysUnauthorizedException(CensysException):
    pass


class CensysAPIBase(object):

    DEFAULT_URL = "https://www.censys.io/api/v1"
    DEFAULT_TIMEOUT = 30

    EXCEPTIONS = {
        403: CensysUnauthorizedException,
        404: CensysNotFoundException,
        429: CensysRateLimitExceededException
    }

    def __init__(self, api_id=None, api_secret=None, url=None, timeout=None):
        self.api_id = api_id or os.environ.get("CENSYS_API_ID", None)
        self.api_secret = api_secret or os.environ.get("CENSYS_API_SECRET", None)
        if not self.api_id or not self.api_secret:
            raise CensysException(401, "No API ID or API secret configured.")
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._api_url = url or os.environ.get("CENSYS_API_URL", None) or self.DEFAULT_URL
        # create a session that we'll use for making requests
        self._session = requests.Session()
        self._session.auth = (self.api_id, self.api_secret)
        self._session.timeout = timeout
        self._session.headers.update({"accept": "application/json, */8"})
        # test that everything works by requesting the users account information
        self.account()

    def _get_exception_class(self, i):
        return self.EXCEPTIONS.get(i, CensysException)

    # wrapper functions that handle making all our REST calls to the API,
    # checking for errors, and decoding the results
    def _make_call(self, method, endpoint, args=None, data=None):
        if endpoint.startswith("/"):
            url = "".join((self._api_url, endpoint))
        else:
            url = "/".join((self._api_url, endpoint))
        args = args or {}
        if data:
            data = json.dumps(data or {})
            res = method(url, params=args, data=data)
        else:
            res = method(url, params=args)
        if res.status_code == 200:
            return res.json()
        else:
            try:
                message = res.json()["error"]
                const = res.json().get("error_type", None)
            except KeyError:
                message = None
                const = "unknown"
            censys_exception = self._get_exception_class(res.status_code)
            raise censys_exception(
                status_code=res.status_code,
                message=message,
                headers=res.headers,
                body=res.text,
                const=const)

    def _get(self, endpoint, args=None):
        return self._make_call(self._session.get, endpoint, args)

    def _post(self, endpoint, args=None, data=None):
        return self._make_call(self._session.post, endpoint, args, data)

    def _delete(self, endpoint, args=None):
        return self._make_call(self._session.delete, endpoint, args)

    def account(self):
        return self._get("account")


class CensysAPIBaseTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._api = CensysAPIBase()

    def test_my_account(self):
        res = self._api.account()
        self.assertEqual(res["api_id"], self._api.api_id)
        self.assertEqual(res["api_secret"], self._api.api_secret)


if __name__ == "__main__":
    unittest.main()
