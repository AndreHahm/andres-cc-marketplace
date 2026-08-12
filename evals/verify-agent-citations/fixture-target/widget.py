"""A tiny fixture module used only by the verify-agent-citations eval suite."""


def load_widget(path):
    """Load a widget definition from disk."""
    with open(path, encoding="utf-8") as f:
        return f.read()


def validate_widget(data):
    """Reject a widget definition with no name field."""
    if "name" not in data:
        raise ValueError("widget definition missing required 'name' field")
    return True


def save_widget(path, data):
    """Persist a widget definition, always UTF-8 encoded."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)
