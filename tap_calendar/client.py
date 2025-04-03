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
            params["pageToken"] = next_page_token
        return params

    def validate_response(self, response: requests.Response, context=None) -> None:
        if response.status_code == 410:
            self.logger.warning("Received 410 Gone: sync token expired. Resetting sync token for full sync...")
            self._tap.reset_state()
        return super().validate_response(response)

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        """Parse the response and return an iterator of result rows."""
        #  Extract custom replication key from json response, then add it in record
        json = response.json()
        event_summary = json.get("summary")
        for item in json.get("items",{}):
            item["user_email"] = event_summary
            item["nextSyncToken"] = json.get("nextSyncToken",None)
        yield from extract_jsonpath(self.records_jsonpath, input=json)
