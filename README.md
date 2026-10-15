# Lab-cli

Lab-CLI is a Klish-based command environment designed for hands-on experimentation, demos, and controlled system operations in the lab. Instead of running arbitrary Linux commands, Lab-CLI exposes a safe, curated set of workflows - things like viewing system information, changing basic settings, and triggering lab utilities - all through a structured, network-device-style interface.

Because Lab-CLI runs on top of Klish 3's client-server architecture, it cleanly separates command parsing from execution logic. That makes it suitable for multi-user environments, containerized setups, and scenarios where command auditing and safety matter. Scripts live in one place, configuration lives in another, and the CLI becomes a stable interface layered on top.

## Project Structure

The project is self-contained inside a container, giving you an isolated, reproducible setup. All CLI definitions, scripts, and configuration files live under the `klish/` directory and are bundled into the image at build time.

    ├─ docker-compose.yml
    ├─ Dockerfile
    └─ klish/
        ├─ xml/
        │  └─ main.xml
        ├─ scripts/
        │  └─ ...
        ├─ patches/
        │  └─ klish-suggest.patch  # smart command suggestions
        ├─ config/
        │  ├─ klishd.conf          # server config
        │  └─ klish.conf           # client config
        └─ entrypoint.sh

## Getting Started

Build the container:

    docker compose build

Start the container in background:

    docker compose up -d

Check the logs to verify that everything started correctly:

    docker logs netlab-cli

Open an interactive shell to the container:

    docker exec -it netlab-cli bash

Start the Klish interactive CLI:

    klish

Sample output:

    NetLab> show greeting
    Hello from NetLab-CLI!
    This is a Klish (clish) demo running in Docker.
    NetLab> exit

Or run a command using the `-c` option:

    klish -c "show greeting"

## Documentation

| Guide                                                      | What it covers |
|------------------------------------------------------------|----------------|
| [Klish Introduction](docs/01_README_KLISH.md)              | Client-server architecture, terminal sessions, process isolation |
| [CLI Features](docs/02_README_CLI_FEATURES.md)             | Tab completion, help, abbreviation, history, filters, formatters, scripting |
| [Modes & Access Control](docs/03_README_MODES.md)          | Views, Cisco IOS hierarchy, enable password, config sessions |
| [Command Discovery](docs/04_README_DISCOVERY.md)           | Tree view and command search |
| [Smart Command Suggestions](docs/05_README_SUGGESTIONS.md) | Typo correction, abbreviation expansion, cross-vendor mapping |
| [CLI in SONiC Ecosystem](docs/06_README_CLI_SONIC.md)      | CLI frameworks in the SONiC ecosystem |
