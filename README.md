# plankarep

plankarep builds text reports from [Planka](https://planka.app) data. It runs
one or more [`plnk`](https://github.com/plattnum/planka-cli) commands, collects
the JSON output, and renders a [Jinja2](https://jinja.palletsprojects.com/)
template with that data.

Each entry in the `[views]` table of the configuration becomes one template
variable. The variable holds the `data` array from the `plnk` response.

## Requirements

- Python 3.14 or later.
- `plnk` on your `PATH`. plankarep calls `plnk` for every view.
- Jinja2 and Click. The package installs both.

You need `pod2man` only when you build the package from source. `pod2man` ships
with Perl.

## Install

Install the package as a tool with `uv`:

```sh
uv tool install git+https://github.com/madduck/plankarep
```

## Configuration

plankarep reads a TOML file. The default path is `./plankarep.toml`. The file
has three tables.

The `[plankarep]` table holds the rendering options:

- `autoescape`: a boolean. `true` escapes HTML-significant characters (`&`,
  `<`, `>`) in template variables. An omitted key is the same as `false`,
  because plankarep produces plain-text reports. An unknown key stops the
  program.

The `[plnk]` table holds the parameters that every `plnk` call shares.
plankarep accepts these keys:

- `server`: the Planka server URL. plankarep passes it as `--server`.
- `token`: the Planka API token. plankarep passes it as `--token`.
- `names`: a boolean. `true` adds `--names`, `false` adds `--no-names`, and an
  omitted key adds neither.
- `project`: a project name. plankarep exports it as `PLNK_PROJECT`.
- `board`: a board name. plankarep exports it as `PLNK_BOARD`.
- `list`: a list name. plankarep exports it as `PLNK_LIST`.

An unknown key stops the program.

The `[views]` table maps a view name to the `plnk` arguments for that view.
plankarep always adds `--output json`.

```toml
[plankarep]
autoescape = false

[plnk]
server = "https://planka.example.org"
token = "foobar"
names = true
project = "My Project"
board = "My Board"

[views]
overdue = "card list --due-before today"
```

For this configuration, plankarep runs:

```sh
PLNK_PROJECT="My Project" PLNK_BOARD="My Board" \
  plnk --output json \
  --server https://planka.example.org \
  --token foobar \
  --names \
  card list --due-before today
```

## Usage

Run the command with a configuration and a template:

```sh
plankarep --config /path/to/config.toml --template /path/to/template.j2 > output.txt
```

`--config` defaults to `./plankarep.toml`. `--template` defaults to
`./plankarep.j2`. Pass `-` as the template to read it from standard input.

`--output` writes the result to a file. The default is standard output.

```sh
plankarep --config config.toml --template report.j2 --output report.txt
```

## Template example

The template below reads the `overdue` view from the configuration above:

```jinja
Overdue projects:

{% for card in overdue %}
- {{ card.name }} (ID: {{ card.id }})
{% endfor %}
```

The result:

```text
Overdue projects:

- Vollmacht anpassen (ID: 1798734652668642385)
- Verfügung hochladen (ID: 1719634473726772597)
```

A template variable that no view defines stops the program. plankarep uses
Jinja2 strict undefined handling.

plankarep loads templates from the directory of the template file. A template
can therefore use `{% extends %}` and `{% include %}` with relative paths. When
you read the template from standard input, the loader uses the current working
directory.

## Filters and tests

plankarep adds three helpers to the template context.

- `datefmt` formats an ISO 8601 timestamp. The default format is `%Y-%m-%d`.
  A `None` value renders as an empty string.

  ```jinja
  {{ card.dueDate | datefmt('%d.%m.%Y') }}
  ```

- `past` tests whether a timestamp is earlier than now.

  ```jinja
  {% if card.dueDate is past %}overdue{% endif %}
  ```

- `future` tests whether a timestamp is later than now.

  ```jinja
  {% if card.dueDate is future %}upcoming{% endif %}
  ```

## Exit codes

plankarep exits with `0` on success. It exits with `1` when a view fails, when a
template is missing or invalid, or when the configuration is missing or
invalid. A failed view prints the `stderr` output of `plnk`.

## Development

Create the environment and run the quality gates:

```sh
uv sync
uv run pytest
uv run pre-commit run --all-files
```

## License

MIT. See `LICENSE`.
