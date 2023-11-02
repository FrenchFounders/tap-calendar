# tap-calendar

`tap-calendar` is a Singer tap for Google Calendar.

Built with the [Meltano Tap SDK](https://sdk.meltano.com) for Singer Taps.

## Installation

```bash
pipx install tap-calendar
```

tap is available by running:

```bash
tap-calendar --about
```

### Configure using environment variables

This Singer tap will automatically import any environment variables within the working directory's
`.env` if the `--config=ENV` is provided, such that config values will be considered if a matching
environment variable is set either in the terminal context or in the `.env` file.

## Usage

You can easily run `tap-calendar` by itself or in a pipeline using [Meltano](https://meltano.com/).

### Executing the Tap Directly

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

Create tests within the `tap_calendar/tests` subfolder and
  then run:

```bash
poetry run pytest
```

You can also test the `tap-calendar` CLI interface directly using `poetry run`:

```bash
poetry run tap-calendar --help
```

### Testing with [Meltano]

```bash
# Install meltano
pipx install meltano
# Initialize meltano within this directory
cd tap-calendar
meltano install
```

Now you can test and orchestrate using Meltano:

```bash
# Test invocation:
meltano invoke tap-calendar --version
# OR run a test `elt` pipeline:
meltano elt tap-calendar <target-loader>
```

