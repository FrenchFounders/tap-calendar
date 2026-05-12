"""REST client handling, including CalendarStream base class."""

from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import requests
from singer_sdk.helpers.jsonpath import extract_jsonpath
from singer_sdk.streams import RESTStream

from tap_calendar.auth import (
    CALENDAR_SCOPES,
    DIRECTORY_SCOPES,
    CalendarAuthenticator,
)

SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")


class GoogleAPIStream(RESTStream):
    """Base stream for any Google API call using the service account.

    The impersonated subject depends on context (the admin for the
    Directory API, the end user for the Calendar API) so we resolve the
    authenticator per request rather than via the standard
    ``authenticator`` property — but we still use the Singer SDK
    ``OAuthJWTAuthenticator`` machinery via ``auth_headers``.
    """

    #: OAuth scopes required by the subclass.
    scopes: tuple = ()

    @property
    def http_headers(self) -> dict:
        headers = {}
        if "user_agent" in self.config:
            headers["User-Agent"] = self.config.get("user_agent")
        return headers

    @property
    def authenticator(self):
        # Disabled: the impersonated subject is context-dependent, so
        # the authenticator is resolved in ``prepare_request`` below.
        return None

    def get_impersonated_subject(self, context: Optional[dict]) -> str:
        """Return the email of the user to impersonate for this request."""
        raise NotImplementedError

    def prepare_request(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> requests.PreparedRequest:
        request = super().prepare_request(context, next_page_token)
        subject = self.get_impersonated_subject(context)
        authenticator = CalendarAuthenticator.create_for_subject(
            stream=self,
            subject=subject,
            scopes=self.scopes,
        )
        # ``auth_headers`` triggers ``update_access_token`` if the
        # cached token is expired — full framework lifecycle, no
        # bespoke refresh logic.
        request.headers.update(authenticator.auth_headers)
        return request

    def validate_response(
        self, response: requests.Response, context=None
    ) -> None:
        # Surface the Google response body on 4xx — the default Singer
        # SDK error message only carries the HTTP status, which makes
        # debugging Google's authorization layer painful.
        if 400 <= response.status_code < 500:
            body = response.text[:1000] if response.text else "<empty>"
            self.logger.error(
                "Google API %s on %s: %s",
                response.status_code,
                response.request.url if response.request else response.url,
                body,
            )
        return super().validate_response(response)


class CalendarStream(GoogleAPIStream):
    """Stream class for endpoints under the Calendar API."""

    url_base = "https://www.googleapis.com/calendar/v3"
    is_timestamp_replication_key = False
    scopes = CALENDAR_SCOPES

    def get_impersonated_subject(self, context: Optional[dict]) -> str:
        if not context or "user_email" not in context:
            raise RuntimeError(
                "CalendarStream requires a context with 'user_email' "
                "(provided by the parent UsersStream)."
            )
        return context["user_email"]

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        params = super().get_url_params(context, next_page_token)
        if next_page_token:
            params["pageToken"] = next_page_token
        return params

    def validate_response(self, response: requests.Response, context=None) -> None:
        if response.status_code == 410:
            # Google: "Sync token is no longer valid, a full sync is
            # required." This happens when a partition's syncToken is
            # too old (>~30 days inactive). Clear the bookmark for
            # THIS partition only — the next run for this user will
            # do a full sync, and the current run keeps going for the
            # other users.
            self.logger.warning(
                "Received 410 Gone for %s: sync token expired. "
                "Cleared partition bookmark — next run will full-sync.",
                context,
            )
            state = self.get_context_state(context)
            if state:
                state.pop("replication_key", None)
                state.pop("replication_key_value", None)
                progress = state.get("progress_markers") or {}
                progress.pop("replication_key_value", None)
            # Returning without raising means Singer SDK will try to
            # parse the response body — which is the JSON error doc
            # (no ``items``), so ``parse_response`` yields nothing for
            # this user and the sync moves on to the next partition.
            return
        return super().validate_response(response)

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        """Parse the response and return an iterator of result rows."""
        payload = response.json()
        # Always set ``nextSyncToken`` on every record. Google only
        # returns it on the very last page (``None`` on intermediate
        # pages) — ``post_process`` further down will replace that
        # ``None`` with the current bookmark so we don't overwrite a
        # real syncToken with nothing.
        next_sync_token = payload.get("nextSyncToken")
        for item in payload.get("items", []):
            item["nextSyncToken"] = next_sync_token
        yield from extract_jsonpath(self.records_jsonpath, input=payload)

    def post_process(
        self, row: dict, context: Optional[dict] = None
    ) -> Optional[dict]:
        """Inject the impersonated user's identity and finalise the
        replication key.

        Intermediate-page records carry ``nextSyncToken=None``: we
        replace that with the bookmark already in state, so Singer
        SDK's incrementer sees ``new == old`` and performs a no-op
        update instead of nuking the bookmark. On the last page,
        ``nextSyncToken`` is the real Google value and gets written
        as the new bookmark.
        """
        if context:
            row["user_id"] = context.get("user_id")
            row["user_email"] = context.get("user_email")
        if row.get("nextSyncToken") is None:
            state = self.get_context_state(context) or {}
            row["nextSyncToken"] = state.get("replication_key_value")
        return row


class DirectoryStream(GoogleAPIStream):
    """Stream class for the Admin SDK Directory API."""

    url_base = "https://admin.googleapis.com/admin/directory/v1"
    scopes = DIRECTORY_SCOPES

    def get_impersonated_subject(self, context: Optional[dict]) -> str:
        admin_email = self.config.get("delegated_admin_email")
        if not admin_email:
            raise RuntimeError(
                "delegated_admin_email must be configured to call the "
                "Admin SDK Directory API."
            )
        return admin_email
