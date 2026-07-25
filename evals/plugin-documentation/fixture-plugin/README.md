# widget-tools

Utilities for creating and validating widget configuration files.

## Installation

```bash
/plugin install widget-tools@<marketplace>
```

Or for local development:

```bash
cc --plugin-dir /path/to/widget-tools
```

## Usage

Ask to "create a widget" and `hello-skill` fires, creating a widget config file at `widgets/<name>.json` with the given type.

## Skills

| Name | Purpose |
|---|---|
| `hello-skill` | Create a new widget configuration file from a name and type |
| `goodbye-skill` | Validate an existing widget configuration file against the widget schema |

## License

MIT
