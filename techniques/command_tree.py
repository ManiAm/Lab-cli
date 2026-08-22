"""
Shared command tree and helper functions for all technique implementations.

The tree models a simplified CLI command structure. Each key is a keyword;
nested dictionaries represent subcommands. Keys wrapped in angle brackets
(like <IP>) are variable argument placeholders that accept any user value.
"""

COMMAND_TREE = {
    "channel-group": {
        "<ID>": {},
    },
    "configure": {
        "terminal": {},
    },
    "debug": {
        "bgp": {},
        "daemon": {},
        "telemetry": {},
    },
    "history": {},
    "interface": {
        "Ethernet": {
            "<ID>": {},
        },
        "port-channel": {
            "<ID>": {},
        },
    },
    "neighbor": {
        "<IP>": {
            "remote-as": {
                "<ASN>": {},
            },
        },
    },
    "ping": {
        "<IP>": {},
    },
    "router": {
        "bgp": {
            "<ASN>": {},
        },
    },
    "show": {
        "bgp": {
            "neighbors": {
                "<IP>": {
                    "advertised-routes": {},
                    "received-routes": {},
                },
            },
            "summary": {},
        },
        "greeting": {},
        "interface": {},
        "interfaces": {
            "counters": {},
            "summary": {},
        },
        "ip": {
            "interface": {},
            "route": {},
        },
        "running-config": {},
        "terminal": {},
        "version": {},
    },
    "traceroute": {
        "<IP>": {},
    },
}


def is_variable(key):
    """Check if a tree key is a variable argument placeholder."""
    return key.startswith("<") and key.endswith(">")


def get_keywords(node):
    """Return fixed keyword children of a tree node (excludes variables)."""
    return sorted(k for k in node if not is_variable(k))


def get_variables(node):
    """Return variable argument placeholders of a tree node."""
    return [k for k in node if is_variable(k)]


def get_all_commands(tree, prefix=""):
    """Flatten the tree into a list of all complete command template paths.

    Variable placeholders like <IP> appear literally in the returned strings.
    Intermediate nodes that lead only to variable children are also included,
    since the variable part is user-supplied.
    """
    commands = []
    for key, subtree in tree.items():
        path = f"{prefix} {key}".strip() if prefix else key
        if not subtree:
            commands.append(path)
        else:
            commands.extend(get_all_commands(subtree, path))
    return sorted(commands)


SHOW_CANDIDATES = get_keywords(COMMAND_TREE["show"])

ALL_COMMANDS = get_all_commands(COMMAND_TREE)
