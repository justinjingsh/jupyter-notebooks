"""IGSession: just enough of the IG REST API for download_ig_prices.ipynb -
POST /session to authenticate, then GET /prices/{epic} (Version: 3) with
resolution/from/to/pageSize/pageNumber to page through history. Mirrors the
IGSession class in
C:\\repos\\github.com\\ig-quant-trading\\src\\ig_quant_trading\\client.py."""

import time

import requests

BASE_URLS = {
    "demo": "https://demo-api.ig.com/gateway/deal",
    "live": "https://api.ig.com/gateway/deal",
}


class IGSession:
    _TIMEOUT = 15

    def __init__(self, api_key, username, password, account_type="demo"):
        self.base_url = BASE_URLS[account_type]
        self.account_type = account_type
        self.api_key  = api_key
        self._http    = requests.Session()
        self._authenticate(username, password)

    def _authenticate(self, username, password):
        resp = self._http.post(
            f"{self.base_url}/session",
            headers={
                "X-IG-API-KEY": self.api_key,
                "Content-Type": "application/json; charset=UTF-8",
                "Version": "1",
            },
            json={"identifier": username, "password": password},
            timeout=self._TIMEOUT,
        )
        if resp.status_code == 401:
            raise RuntimeError("Invalid credentials - check IG_USERNAME / IG_PASSWORD")
        if resp.status_code == 403:
            raise RuntimeError(
                "API key rejected - check IG_API_KEY and that it matches "
                f"the '{self.account_type}' environment"
            )
        resp.raise_for_status()
        self._cst = resp.headers["CST"]
        self._xst = resp.headers["X-SECURITY-TOKEN"]
        print("Authenticated OK")

    def _headers(self, version):
        return {
            "X-IG-API-KEY": self.api_key,
            "CST": self._cst,
            "X-SECURITY-TOKEN": self._xst,
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "application/json; charset=UTF-8",
            "Version": str(version),
        }

    def _get(self, path, version, params=None):
        resp = self._http.get(
            f"{self.base_url}{path}",
            headers=self._headers(version),
            params=params,
            timeout=self._TIMEOUT,
        )
        if resp.status_code == 403 and "allowance" in resp.text:
            raise RuntimeError(f"IG historical-data allowance exceeded: {resp.text}")
        if not resp.ok:
            raise RuntimeError(f"API error {resp.status_code}: {resp.text}")
        return resp.json()

    def get_prices(self, epic, resolution, start, end, page_size=200):
        """Page through GET /prices/{epic} (v3) for [start, end]. Returns
        (candles, allowance_dict)."""
        candles, allowance = [], {}
        page = 1
        while True:
            data = self._get(
                f"/prices/{epic}",
                version="3",
                params={
                    "resolution": resolution,
                    "from": start,
                    "to": end,
                    "pageSize": page_size,
                    "pageNumber": page,
                },
            )
            candles.extend(data.get("prices", []))
            meta = data.get("metadata", {})
            allowance = meta.get("allowance", allowance)
            page_data = meta.get("pageData", {})
            total_pages = page_data.get("totalPages", 1)
            if page >= total_pages or not data.get("prices"):
                break
            page += 1
            time.sleep(1)  # be gentle on the per-minute request allowance
        return candles, allowance
