"""tap-calendar tap class."""

from typing import List

from singer_sdk import Tap, Stream
from singer_sdk import typing as th  # JSON schema typing helpers

from tap_calendar.streams import (
    EventsStream
)

STREAM_TYPES = [
    EventsStream
]


class TapCalendar(Tap):
    """tap-calendar tap class."""
    name = "tap-calendar"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "oauth_credentials.client_id",
            th.StringType,
            description="Your google client_id",
        ),
        th.Property(
            "oauth_credentials.client_secret",
            th.StringType,
            description="Your google client_secret",
        ),
        th.Property(
            "oauth_credentials.refresh_token",
            th.StringType,
            description="Your google refresh token",
        ),
        th.Property("user_id", th.StringType, description="Your Google User ID"),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        return [stream(tap=self) for stream in STREAM_TYPES]
