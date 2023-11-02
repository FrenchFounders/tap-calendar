"""tap-calendar Authentication."""


from singer_sdk.authenticators import OAuthAuthenticator, SingletonMeta


class CalendarAuthenticator(OAuthAuthenticator, metaclass=SingletonMeta):
    """Authenticator class for tap-calendar."""

    @property
    def oauth_request_body(self) -> dict:
        """Define the OAuth request body for the tap-calendar API."""
        oauth_credentials = self.config.get("oauth_credentials", {})
        return {
            "grant_type": "refresh_token",
            "client_id": oauth_credentials.get("client_id"),
            "client_secret": oauth_credentials.get("client_secret"),
            "refresh_token": oauth_credentials.get("refresh_token"),
        }

    @classmethod
    def create_for_stream(cls, stream) -> "CalendarAuthenticator":
        return cls(
            stream=stream,
            auth_endpoint="https://oauth2.googleapis.com/token",
            oauth_scopes="https://www.googleapis.com/auth/calendar.readonly",
        )