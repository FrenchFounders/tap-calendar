"""tap-calendar tap class."""

from typing import List

from singer_sdk import Stream, Tap
from singer_sdk import typing as th  # JSON schema typing helpers

from tap_calendar.streams import EventsStream, UsersStream

STREAM_TYPES = [
    UsersStream,
    EventsStream,
]


class TapCalendar(Tap):
    """tap-calendar tap class."""

    name = "tap-calendar"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "service_account_credentials",
            th.StringType,
            secret=True,
            required=True,
            description=(
                "JSON content of the Google service account key. The "
                "service account must have Domain-Wide Delegation "
                "enabled with the scopes "
                "'admin.directory.user.readonly' and 'calendar.readonly'."
            ),
        ),
        th.Property(
            "delegated_admin_email",
            th.StringType,
            required=True,
            description=(
                "Email of a Google Workspace admin used to impersonate "
                "when calling the Admin SDK Directory API to list users."
            ),
        ),
        th.Property(
            "excluded_user_emails",
            th.ArrayType(th.StringType),
            default=[],
            description=(
                "List of user emails to exclude from sync (e.g. shared "
                "mailboxes, system accounts, former employees). "
                "Matching is case-insensitive."
            ),
        ),
        th.Property(
            "start_date",
            th.StringType,
            description=(
                "RFC3339 lower bound applied as ``timeMin`` on the "
                "initial full sync of each user (until a syncToken is "
                "acquired). Optional: if omitted, Google returns every "
                "event the user has."
            ),
        ),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        return [stream(tap=self) for stream in STREAM_TYPES]
