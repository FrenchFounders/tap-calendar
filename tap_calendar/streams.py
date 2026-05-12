"""Stream type classes for tap-calendar."""

from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from tap_calendar.client import CalendarStream, DirectoryStream

SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")


class UsersStream(DirectoryStream):
    """List active users of the Google Workspace tenant.

    Acts as the parent stream: each emitted user becomes the context for
    a child ``EventsStream`` sync.
    """

    name = "calendar_users"
    path = "/users"
    primary_keys = ["id"]
    records_jsonpath = "$.users[*]"
    next_page_token_jsonpath = "$.nextPageToken"
    schema_filepath = SCHEMAS_DIR / "users.json"

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            # 'my_customer' resolves to the tenant of the delegated admin.
            "customer": "my_customer",
            "maxResults": 500,
            "projection": "basic",
            "query": "isSuspended=false",
            "showDeleted": False,
        }
        if next_page_token:
            params["pageToken"] = next_page_token
        return params

    def parse_response(self, response) -> Iterable[dict]:
        payload = response.json()
        excluded = {
            email.lower()
            for email in (self.config.get("excluded_user_emails") or [])
        }
        for user in payload.get("users", []):
            if user.get("suspended") or user.get("archived"):
                continue
            email = (user.get("primaryEmail") or "").lower()
            if email in excluded:
                self.logger.info(
                    "Excluding user %s (matched excluded_user_emails)",
                    email,
                )
                continue
            yield user

    def get_child_context(self, record: dict, context: Optional[dict]) -> dict:
        return {
            "user_id": record["id"],
            "user_email": record["primaryEmail"],
        }


class EventsStream(CalendarStream):
    name = "calendar_events"
    schema_filepath = SCHEMAS_DIR / "events.json"
    replication_key = "nextSyncToken"
    records_jsonpath = "$.items[*]"
    next_page_token_jsonpath = "$.nextPageToken"
    path = "/calendars/primary/events"

    parent_stream_type = UsersStream
    ignore_parent_replication_key = True
    state_partitioning_keys = ["user_id"]

    # ``syncToken`` is an opaque base64 blob — it is not lexically
    # ordered, so the default Singer SDK ``new > old`` guard would
    # sometimes refuse to advance the bookmark. We always want the
    # newest token returned by Google to win.
    check_sorted = False

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        params = super().get_url_params(context, next_page_token)
        # Read the sync token directly from state — we can't use
        # ``get_starting_replication_key_value`` because the Singer SDK
        # falls back to ``config['start_date']`` when no bookmark
        # exists, which would send an RFC3339 timestamp as a Google
        # ``syncToken`` (HTTP 400 "Invalid sync token value.").
        state = self.get_context_state(context) or {}
        sync_token = (
            state.get("replication_key_value")
            or state.get("progress_markers", {}).get("replication_key_value")
        )
        if sync_token:
            params["syncToken"] = sync_token
        else:
            start_date = self.config.get("start_date")
            if start_date:
                params["timeMin"] = start_date
        return params
