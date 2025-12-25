
## What is Klish?

[Klish](https://src.libcode.org/pkun/klish.git) is an open-source framework for building structured, Cisco-style command-line interfaces (CLIs) on Unix-like systems. It exposes only the commands you define, rather than a general-purpose shell like Bash.

| Feature                         | Bash       | Klish        |
| ------------------------------ | ----------- | ------------ |
| Free command execution         | ✔️ Yes      | ❌ No       |
| Structured syntax enforcement  | ❌ No       | ✔️ Yes      |
| Tab completion from grammar    | ❌ Optional | ✔️ Yes      |
| Mode/view-based CLI            | ❌ No       | ✔️ Yes      |
| Designed for network devices   | ❌ No       | ✔️ Yes      |

Klish is designed for embedded systems, network equipment, and any environment where a controlled CLI is preferable to a full shell.

- **[Schema-driven](https://src.libcode.org/pkun/klish/src/3.2.0/klish.xsd)**: Commands are defined in XML, describing valid commands, arguments, help text, and execution logic.

- **Deterministic**: Input is parsed and validated before execution, improving usability and enforcing syntax rules.

- **Hierarchical CLI**: Klish supports structured, mode-based navigation similar to network OS CLIs, instead of free-form shell scripts.

### Klish vs. Clish

Klish originated from the [clish](https://clish.sourceforge.net/) project, adopting the XML-defined CLI concept. Earlier versions were forked from clish-0.7.3, but the Klish 3.x series is largely a rewrite with an expanded feature set. It attempts to remain compatible with clish XML where practical, although not all features are identical. The original clish project is effectively unmaintained.

### Architecture in Klish 3

Klish 3 introduces a client-server design:

- `klishd` loads CLI definitions and listens for clients
- Clients send commands to the server
- Each session runs in a dedicated handler process
- Communication uses Klish Transfer Protocol (KTP)

This design improves robustness, modularity, and multi-user support. Core utilities are provided by [faux](https://src.libcode.org/pkun/faux.git), a shared C library developed alongside Klish to avoid duplicating common functionality.
