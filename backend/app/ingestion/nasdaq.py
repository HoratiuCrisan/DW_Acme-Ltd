import httpx
from typing import Iterator

from app.config import settings


class NasdaqExtractor:
    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.nasdaq_api_key
        self._base_url = settings.nasdaq_base_url.rstrip("/")

    def fetch_table_data(
        self, datatable_code: str, filters: dict | None = None
    ) -> Iterator[dict]:
        """
        Fetches all pages from a Nasdaq datatable endpoint.
        datatable_code: e.g. "WIKI/PRICES"
        filters: optional query filters, e.g. {"ticker": "AAPL"}
        Yields one dict per row.
        """
        params = {"api_key": self._api_key, "qopts.export": "false"}
        if filters:
            params.update(filters)

        cursor_id = None
        with httpx.Client(timeout=30) as client:
            while True:
                if cursor_id:
                    params["qopts.cursor_id"] = cursor_id

                response = client.get(
                    f"{self._base_url}/{datatable_code}.json",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                datatable = data.get("datatable", {})
                columns = [col["name"] for col in datatable.get("columns", [])]
                rows = datatable.get("data", [])

                for row in rows:
                    yield dict(zip(columns, row))

                meta = data.get("meta", {})
                cursor_id = meta.get("next_cursor_id")
                if not cursor_id:
                    break
