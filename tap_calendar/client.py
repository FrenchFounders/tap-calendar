"""REST client handling, including CalendarStream base class."""

import requests
from pathlib import Path
from typing import Any, Dict, Optional, Iterable

from memoization import cached

from singer_sdk.helpers.jsonpath import extract_jsonpath
from singer_sdk.streams import RESTStream

from tap_calendar.auth import CalendarAuthenticator


SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")


class CalendarStream(RESTStream):
    """tap-calendar stream class."""

    url_base = "https://www.googleapis.com/calendar/v3"
    is_timestamp_replication_key=False


    @property
    @cached
    def authenticator(self) -> CalendarAuthenticator:
        """Return a new authenticator object."""
        return CalendarAuthenticator.create_for_stream(self)

    @property
    def http_headers(self) -> dict:
        """Return the http headers needed."""
        headers = {}
        if "user_agent" in self.config:
            headers["User-Agent"] = self.config.get("user_agent")
        return headers

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params = super().get_url_params(context, next_page_token)
        if next_page_token:
            params["page"] = next_page_token
        return params


    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        """Parse the response and return an iterator of result rows."""
        #  Extract custom replication key from json response, then add it in record
        json = response.json()
        for item in json.get("items",{}):
            item["nextSyncToken"] = json.get("nextSyncToken",None)
        yield from extract_jsonpath(self.records_jsonpath, input=json)
