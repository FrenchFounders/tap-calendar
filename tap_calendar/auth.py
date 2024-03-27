"""tap-calendar Authentication."""
from uuid import uuid4

from singer_sdk.authenticators import OAuthAuthenticator, SingletonMeta
import logging
import boto3
import json

class CalendarAuthenticator(OAuthAuthenticator, metaclass=SingletonMeta):
    """Authenticator class for tap-calendar."""

    sqs = None

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

    def get_aws_sqs(self):
        if self.sqs is None:
            self.sqs = boto3.resource(
                "sqs",
                aws_access_key_id=self.config.get("aws_access_key"),
                aws_secret_access_key=self.config.get("aws_secret_key"),
                region_name=self.config.get("aws_region", "us-east-1"),
            )
        return self.sqs

    def send_aws_sqs(self):
        queue_name = self.config.get("aws_sqs", {}).get("queue_name")
        if queue_name:
            sqs = self.get_aws_sqs()
            queue = sqs.get_queue_by_name(QueueName=queue_name)
            msg = {"Id": str(uuid4()), "MessageBody": json.dumps({"event": "teamGoogleTokenExpired", "payload": {"userId": self.config.get("user_id")}})}
            result = queue.send_messages(Entries=[msg])
            logging.info(f"Sent invalid_grant message to AWS SQS queue {queue_name} : {result}")

    @property
    def update_access_token(self):
        try:
            super().update_access_token()
        except RuntimeError as error:
            if "{'error': 'invalid_grant', 'error_description': 'Bad Request'}" in str(error):
                user_id = self.config.get("user_id")
                user_email = self.config.get("user_email")
                logging.info(f'Received invalid_grant for {user_email} (id={user_id})')
                self.send_aws_sqs()

            raise error
