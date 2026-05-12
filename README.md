# tap-calendar

`tap-calendar` is a Singer tap for Google Calendar.

It replicates the events of every **active** user of a Google Workspace
tenant using a single **service account with Domain-Wide Delegation**:

1. The tap calls the Admin SDK Directory API (impersonating a Workspace
   admin) to list active users.
2. For each user, the tap impersonates that user and reads their
   primary calendar via the Calendar API.

Built with the [Meltano Tap SDK](https://sdk.meltano.com).

## Google Workspace setup

1. Create a service account in Google Cloud and download its JSON key.
2. In the Workspace admin console, enable **Domain-Wide Delegation** for
   that service account with the following OAuth scopes:
   - `https://www.googleapis.com/auth/admin.directory.user.readonly`
   - `https://www.googleapis.com/auth/calendar.readonly`
3. Pick a Workspace **admin** account whose identity will be borrowed to
   list users (`delegated_admin_email`). Any super admin works; a
   dedicated, least-privileged admin role is recommended.

## Settings

| Setting                        | Required | Description |
|--------------------------------|----------|-------------|
| `service_account_credentials`  | yes      | **Stringified JSON** of the service account key (not a file path). Easiest is `cat key.json \| jq -c .` or `json.dumps(...)`. |
| `delegated_admin_email`        | yes      | Workspace admin to impersonate for the Directory API. |
| `excluded_user_emails`         | no       | Array of user emails to skip (shared mailboxes, system accounts…). Case-insensitive. |
| `start_date`                   | no       | RFC3339 lower bound applied as `timeMin` on the initial full sync of each user. If omitted, Google returns every event the user has. |

State is partitioned per `user_id`, so each user has its own
`syncToken` bookmark and incremental syncs are independent.

## Installation

```bash
pipx install tap-calendar
```

```bash
tap-calendar --about
```

### Configure using environment variables

This Singer tap will automatically import any environment variables
within the working directory's `.env` if `--config=ENV` is provided.
The service account JSON can be passed as a single line via
`TAP_CALENDAR_SERVICE_ACCOUNT_CREDENTIALS`.

## Usage

```bash
tap-calendar --version
tap-calendar --help
tap-calendar --config CONFIG --discover > ./catalog.json
```

### Initialize your Development Environment

```bash
pipx install poetry
poetry install
```

### Create and Run Tests

```bash
poetry run pytest
```

### Testing with Meltano

```bash
pipx install meltano
cd tap-calendar
meltano install
meltano invoke tap-calendar --version
meltano elt tap-calendar <target-loader>
```
