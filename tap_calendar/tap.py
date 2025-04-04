"""tap-calendar tap class."""

from typing import Any, List

from singer_sdk import Tap, Stream
from singer_sdk import typing as th  # JSON schema typing helpers
from singer_sdk._singerlib import StateMessage, write_message

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
            secret=True,
            description="Your google client_secret",
        ),
        th.Property(
            "oauth_credentials.refresh_token",
            th.StringType,
            secret=True,
            description="Your google refresh token",
        ),
        th.Property(
            "user_id",
            th.StringType,
            description="Your Google User ID"
        ),
        th.Property(
            "aws_sqs.queue_name",
            th.StringType,
            description="SQS queue name used to received a message when the refresh token has expired"
        )
    ).to_dict()

    def reset_state(self) -> None:
        """Custom method to reset state (in case of 410 response)"""
        self.replication_key_value = None
        write_message(StateMessage({'bookmarks' : {}}))

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        return [stream(tap=self) for stream in STREAM_TYPES]
