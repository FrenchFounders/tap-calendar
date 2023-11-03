"""Stream type classes for tap-calendar."""

from pathlib import Path
from typing import Any, Dict, Optional


from tap_calendar.client import CalendarStream


SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")

class EventsStream(CalendarStream):
    """Define custom stream."""
    name = "events"
    schema_filepath = SCHEMAS_DIR / "events.json"
    replication_key = "nextSyncToken"
    records_jsonpath = "$.items[*]"
    next_page_token_jsonpath = "$.nextPageToken"
    path = "/calendars/primary/events"


    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params= super().get_url_params(context, next_page_token)
        syncToken = self.get_starting_replication_key_value(context)
        if syncToken:
            params["syncToken"] = syncToken
        else:
            #TODO parameterize it
            params["timeMin"] = "2022-01-01T00:00:00Z"
        return params
    
    def post_process(self, row:dict, context:dict):
        # Posting row when event hasn't been deleted
        if row.get("status") != "cancelled":
            return row

    
    