
# Lab-cli

Lab-CLI is a Klish-based command environment designed for hands-on experimentation, demos, and controlled system operations in the lab. Instead of running arbitrary Linux commands, Lab-CLI exposes a safe, curated set of workflows - things like viewing system information, changing basic settings, and triggering lab utilities - all through a structured, network-device-style interface.

Because Lab-CLI runs on top of Klish 3’s client-server architecture, it cleanly separates command parsing from execution logic. That makes it suitable for multi-user environments, containerized setups, and scenarios where command auditing and safety matter. Scripts live in one place, configuration lives in another, and the CLI becomes a stable interface layered on top.

Refer to the following guides for more details:

- [Klish Introduction](docs/README_KLISH.md)
- [CLI in SONiC Ecosystem](docs/README_CLI_SONIC.md)
- [Smart Command Suggestions](docs/README_SUGGESTIONS.md)

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

    NetLab# show greeting
    Hello from NetLab-CLI!
    This is a Klish (clish) demo running in Docker.
    NetLab# exit

Or run a command using the `-c` option:

    klish -c "show greeting"

## Klish Terminal Sessions

Klish 2 operates as a single monolithic binary (`clish`) and handles parsing, execution, and user interaction simultaneously. Klish 3, on the other hand, adopts a Client-Server architecture. This decoupling significantly improves stability, concurrency, and performance.

- `klishd`: A background daemon that loads XML configuration files, maintains the internal database, and listens for incoming connections.

- `klish`: A lightweight "dumb terminal" client. It connects to the daemon (typically via a Unix Socket) to transmit keystrokes and display output.

When a client connects, the daemon creates a unique environment for that specific interaction. The klish client connects to the master klishd process. Upon accepting the connection, the master klishd forks a new child process dedicated exclusively to that connection. This child process represents the Session. This new model provides the following characteristics:

- **Isolation**: Every connected user is assigned a dedicated process with a unique Process ID (PID).

- **Memory Separation**: Because sessions run as separate processes, they do not share memory space. User A cannot access or modify User B's variables. This ensures high stability. A crash in one session will not affect the main daemon or other users.

- **Lifetime**: A session persists only as long as the client remains connected. Terminating the client (e.g., typing `exit` or closing the terminal) causes the corresponding klishd child process to terminate.

To verify this architecture, we can open multiple interactive terminals to the container and inspect the process hierarchy. By running `show terminal session` in two separate terminals, we can observe unique PIDs for each user, confirming they are separate entities.

First client:

    NetLab# show terminal session

    --- Session Information ---
    Session PID: 22
    User ID:     0
    User Name:   root
    Command:     session

Second client:

    NetLab# show terminal session

    --- Session Information ---
    Session PID: 43
    User ID:     0
    User Name:   root
    Command:     session

Inspecting the system processes confirms the relationship between the Master Daemon, the Session Workers, and the Clients. PID 7 is the Master Server. It loaded the XMLs once at startup. It does not execute commands itself; it only listens for new connections.

    # ps -ef | grep klish
    root           7       1  0 02:02 pts/0    00:00:00 klishd -f /etc/klish/klishd.conf -d -v
    root          23       7  0 02:02 pts/0    00:00:00 klishd -f /etc/klish/klishd.conf -d -v
    root          22      10  0 02:02 pts/1    00:00:00 klish
    root          44       7  0 02:03 pts/0    00:00:00 klishd -f /etc/klish/klishd.conf -d -v
    root          43      31  0 02:03 pts/2    00:00:00 klish

Session A (PID 23):

- Parent: PID 7 (The Master).
- Role: A dedicated worker process created to handle Client A (PID 22).
- Stability: If this session crashes, the Master (PID 7) and Session B (PID 44) remain unaffected.

Session B (PID 44):

- Parent: PID 7 (The Master).
- Role: A dedicated worker process created to handle Client B (PID 43).
- Isolation: Totally independent from Session A.

## CLI Features

### Tab Completion (Static)

Klish provides context-aware Tab completion. As you type a command, it analyzes where you are in the syntax tree and suggests only the tokens that are valid at that position. When you type:

    NetLab# show <TAB>

Klish looks at all child elements defined under the `show` command in the XML and shows the available subcommands:

    NetLab# show
    greeting    interface    ip   terminal   version

### Tab Completion (Dynamic)

Klish can also perform dynamic (runtime-generated) Tab completion. Instead of listing static keywords, it can run a script or program to discover valid values. For example, after defining a parameter whose type pulls interface names from `/sys/class/net`, pressing Tab after show interface produces:

    NetLab# show interface <TAB>
    eth0   lo

Here, Klish:

- Detects that you are completing the `iface` parameter.
- Calls the completion script associated with its parameter type.
- Displays each returned value as a completion candidate.

### Inline Help

Klish provides inline help. When you use `?`, it shows both the command keyword and a short description:

    NetLab# show ?
    greeting   Display a welcome message
    interface  Show interface details
    ip         Show IP-related information
    terminal   Display terminal information
    version    Show system version

The left column comes from each command’s `name` attribute, and the right column comes from its `help` attribute. This makes the CLI self-documenting. The user does not need to remember every command.

### Command Abbreviation

Klish 3 uses a strict command resolver by default. In this mode, users must either type the full command name or rely on tab completion to expand it. Typing a partial keyword that does not exactly match a command results in an error, even if the prefix is unique:

    NetLab# his
    Error: Illegal command

Command abbreviations can be enabled explicitly by using the `value` attribute with the `|` delimiter:

    <COMMAND name="history" value="his|tory" />

The portion before `|` (`his`) is the mandatory prefix and the portion after `|` (`tory`) is an optional suffix. The user must type at least the mandatory prefix. Any progressive extension of the optional suffix is accepted. For the example above, the following inputs are valid:

```text
his
hist
histo
histor
history
```

Command abbreviations can be useful when commands are long and operators are already familiar with the CLI syntax, as they reduce typing effort and improve efficiency for experienced users. However, abbreviations can also introduce ambiguity (especially as the command set grows or evolves) which may lead to unexpected command resolution or operator error. For this reason, their use should be deliberate and carefully controlled, and they are often discouraged in favor of explicit commands and reliable tab completion.

### Default Sub-commands

A default sub-command means a parent command has exactly one child, and the CLI automatically runs that child if the user stops early. Conceptually:

    show ip           ⇒ would automatically run the only child
    show ip interface ⇒ runs it explicitly

In Klish 3, this behavior is not automatic. The parent (`ip`) is considered incomplete unless you define an explicit `<ACTION>` for it. If you want `show ip` to execute the same logic as `show ip interface`, you must configure that intentionally in the XML.

### Parameter Validation

In Klish 2, parameter validation was often handled directly within the XML definition using the `pattern` attribute, which accepted a regular expression. The CLI engine itself would check the user's input against this regex before allowing the command to proceed. This provided a simple, declarative way to enforce formats like IP addresses or ranges without writing external code.

In Klish 3, this built-in regex engine has been removed in favor of a more flexible, plugin-based architecture. Validation is now delegated entirely to Symbols (functions) inside plugins. To validate a parameter, you define a `PTYPE` (Parameter Type) that contains an `<ACTION>`. When a user enters a value, Klish passes that value to the action (typically a script or a C function). The action must process the input and return an exit code: 0 for valid and non-zero for invalid. This approach, while slightly more verbose in XML, allows for arbitrarily complex validation logic beyond what simple regular expressions could achieve.

    NetLab# ping 8.8.8.256
    Error: Illegal command

### Command History

Command history refers to the ability to recall previously executed commands, typically accessed via arrow keys (for immediate reuse) or a `history` command (for a full list). In a standard shell environment like Bash, this is straightforward. A single shell process remains active for the entire session, holding all past inputs in its memory.

The standard `history` command fails in Klish 3 due to ephemeral execution environments. When the Klish server receives a command from the client, it spawns a brand new, isolated shell process solely to execute that specific action. This temporary shell is born with a "blank mind". It has no knowledge of previous commands and terminates immediately after its task is done. Therefore, if you create a Klish command that simply invokes `history`, it triggers a fresh shell that has essentially never run anything before, resulting in empty output.

The solution is to manually implement persistence using `<LOG>`. Since the Klish server has access to the command string currently being executed (exposed via the `KLISH_PARENT_LINE` environment variable), you can configure a global `<LOG>` tag to intercept every command and append it to a persistent text file. The `history` command is then redefined not to ask the shell for its memory, but to read and display the contents of this log file.

    NetLab# history
      1  show ip interface
      2  history
      3  show interface eth0

Note that this history is global, not per-session. Different CLI sessions all append to the same log file, so every user sees a unified record of commands that have been executed in the lab. This has clear benefits. It behaves like an audit trail, survives reconnects, and makes it easy to review what was tried previously. The trade-off is that it does not behave like a personal shell history. Commands from different users and sessions are mixed together, and history reflects system activity rather than just the current session.

### Text Filters

The Klish 3 engine provides native support for piping command output through text filters using the `|` operator. Any `<COMMAND>` element with the attribute `filter="true"` is automatically available as a pipe target, allowing users to refine output without additional plumbing.

    NetLab# show interface eth0 | grep inet
        inet 172.18.0.2/16 brd 172.18.255.255 scope global eth0

The following utilities are available:

| Utility     | Description                                         |
| ----------- | --------------------------------------------------- |
| **head**    | Keep only the first N lines of output.              |
| **tail**    | Keep only the last N lines of output.               |
| **include** | Show only lines that contain the given text.        |
| **exclude** | Hide lines that contain the given text.             |
| **begin**   | Start output from the first line matching a pattern.|
| **grep**    | Search output for lines matching a text (or regex). |
| **count**   | Count the number of lines in the output.            |

> **`include` vs `grep`:** Both match lines by pattern, but `include` is case-insensitive (`grep -Ei`) while `grep` is case-sensitive (`grep -E`). Use `include` for quick, forgiving searches and `grep` when exact casing matters.

### Formatters

Formatters transform command output into a structured data format such as JSON, XML, or CSV. Unlike text filters that work on raw text line-by-line, a formatter requires the upstream command to produce structured data so the output is semantically meaningful.

| Formatter | Description                                      |
| --------- | ------------------------------------------------ |
| **json**  | Emit output as a JSON document.                  |
| **xml**   | Emit output as an XML document.                  |
| **csv**   | Emit output as comma-separated values.           |

In Klish 3, the `|` character is reserved by the engine for text filters. Formatters therefore use the `format` keyword instead. The `format` parameter is implemented as an optional subcommand inside each `show` command. When present, the command switches to a structured data source (for example, `ip -j addr show` instead of `ip addr show`) and pipes the result through a format converter

Json Example:

    NetLab# show interface eth0 format json

    [
      {
        "ifindex": 3,
        "ifname": "eth0",
        "flags": ["BROADCAST", "MULTICAST", "UP", "LOWER_UP"],
        "mtu": 1500,
        ...
      }
    ]

CSV Example:

    NetLab# show version format csv

    "system","node","release","version","machine"
    "Linux","abcd1234","6.6.87","#1 SMP ...","x86_64"

XML Example:

    NetLab# show ip interface format xml

    <output>
      <item>
        <ifname>lo</ifname>
        <operstate>UNKNOWN</operstate>
        ...
      </item>
      <item>
        <ifname>eth0</ifname>
        ...
      </item>
    </output>

Formatted output can still be piped through text filters. The formatter runs first (inside the command), and the text filter operates on the formatted result via the normal pipe:

    NetLab# show interface eth0 format json | grep ifname
        "ifname": "eth0",

> Piping a text filter after a formatter will return matching lines but may produce an incomplete document.

### Views

A View in Klish is a logical container that groups related commands together. It acts as a distinct "mode" or "context" within the CLI. When a user defines a view, they are creating a specialized environment (a namespace) where only specific, relevant commands exist. Entering a view isolates the user from the global configuration, allowing them to focus on a specific task or subsystem.

For example, navigating from the main menu into the "tools" view changes the prompt to indicate the new context:

    NetLab# tools
    NetLab(tools)#
      date       Show current date
      sys-check  Check system resources
      exit       Go back

Here are the key benefits of using views:

1. **Logical Organization**: Views prevent "command clutter" by organizing hundreds of potential commands into manageable categories. Instead of presenting the user with every possible option at once, views hide irrelevant commands until they are needed.

2. **Contextual Safety**: Views restrict command availability based on context. This prevents accidents by ensuring that sensitive commands (like `reboot` or `format`) are only accessible in specific, privileged views, rather than being available at the top level.

3. **Workflow Guidance**: Views guide the user through a structured workflow. For example, to configure a network card, a user might enter interface view. Once inside, the CLI inherently implies that all subsequent commands (like ip address or shutdown) apply only to that specific interface, reducing the need for repetitive parameters.

4. **Command Name Reusability**: Views allow you to reuse simple command names without conflict. For example, the command `restart` could restart a specific service when inside the Service View, but restart the entire router when inside the System View. Because they live in different views, they do not interfere with each other.

### External Scripts

While Klish allows you to write small logic blocks directly inside the XML, complex operations are best handled by invoking external Bash or Python scripts. This approach treats the CLI as a "frontend" while offloading the heavy lifting to specialized backend scripts.

The script plugin in Klish spawns a standard shell instance. To invoke an external script, you simply provide the full path to the executable file within the `<ACTION>` tag. You can pass Klish parameters to these scripts either as command-line arguments or by reading the environment variables Klish automatically exports.

The following example demonstrates the `sys-check` command, which is defined within the `tools` view. This command illustrates how Klish captures user input (a parameter) and passes it directly to an underlying Bash script to control execution logic. In this scenario, the user selects the `cpu` target. Klish passes this argument to the script, which then filters the system information accordingly.

    NetLab# tools
    NetLab(tools)#
    NetLab(tools)# sys-check cpu
    --------------------------------
    Checking System: cpu
    --------------------------------
    22:09:21 up 4 days, 13:25,  0 user,  load average: 0.50, 0.49, 0.37
    Processors: 36
    --------------------------------

### Lua

Klish includes Lua as a built-in scripting engine. In Klish 3, the Lua plugin is part of the core architecture and is the preferred way to add logic that needs to be closely integrated with the CLI itself such as context handling, prompts, validation, and session-aware behavior.

Lua is not a replacement for Bash or Python. Instead, it fills a gap those languages cannot easily solve inside a CLI engine. Lua executes inside the Klish process (not as an external program), which allows it to:

- Access CLI context and parameters directly
- Maintain session state without temporary files
- Build dynamic prompts and modes
- Run lightweight control logic without creating new processes

### Configuration View

To ensure system stability and prevent accidental changes, administrative commands are isolated in a dedicated view. You cannot modify system settings from the main menu; you must explicitly enter configuration view. This prevents users from accidentally running destructive commands (like `shutdown`) while just browsing status.

The following example demonstrates entering configuration view, selecting an interface, and attempting to modify its state. Note that as you navigate deeper into specific components (like an interface), the prompt changes to indicate exactly what object you are modifying.

    NetLab# configure terminal
    NetLab(config)# interface <TAB>
    eth0   lo
    NetLab(config)# interface eth0
    NetLab(config-if-eth0)# shutdown
    RTNETLINK answers: Operation not permitted

> Note on Permissions: The "Operation not permitted" error shown above is expected behavior in this development environment. The CLI is running inside a generic container without the NET_ADMIN capability, so the Linux kernel blocks the state change. However, the output confirms that the Klish logic successfully triggered the command script.

### Configuration Sessions

In complex network environments, making changes one by one can be risky. If you lose connectivity halfway through a configuration update, the device might be left in a broken or inconsistent state. To solve this, the CLI supports configuration sessions, often referred to as transactional configuration.

- **Draft**: When you enter a session, you are not modifying the live system. Instead, you are editing a candidate configuration also known as a draft. Think of this as a shopping cart; you can add, remove, or change items without affecting the real world yet.

- **Transaction**: A transaction is a group of commands that are treated as a single unit. You define the entire state you want the device to be in, review it, and then apply it all at once.

- **Commit**: It takes your draft (candidate configuration) and applies it to the running configuration (the live system). Until you type `commit`, your changes are invisible to the network.

- **Discard**: If you change your mind before committing, you can simply discard the session. The draft is deleted, and the device remains exactly as it was.

- **Rollback**: In a full production system, this allows you to revert the system to a previous valid state if a committed change causes issues.

To demonstrate this capability in our Klish 3 environment without a heavy database backend, we implemented a file-based state mechanism. This allows us to simulate distinct "live" and "session" modes using standard Linux filesystem operations.

When a user enters a configuration session, the CLI creates a unique session file and sets a session flag for that specific Process ID (PID). This ensures that multiple administrators can work on different drafts simultaneously without their changes colliding.

    NetLab# configure session s-1
    NetLab(config-session-s-1)#

Every configuration command acts as a smart command. The command checks the user's current mode. On "live" mode, it executes the system command immediately. On "session" mode it buffers the command by appending the text to the session's candidate file instead of executing it.

    NetLab(config-session-s-1)# interface eth0
    NetLab(config-if-eth0)# shutdown
    NetLab(config-if-eth0)# exit
    NetLab(config-session-s-1)#

The `commit` command is the execution engine. It reads the candidate file line-by-line and executes the buffered commands in order. Once the script finishes successfully, the candidate file is cleared, signifying that the transaction is complete and the draft has become the live configuration.

    NetLab(config-session-s-1)# commit

### Smart Command Suggestions

When a command fails, most CLIs respond with a generic error message like `Illegal command` and stop. The user is left guessing what went wrong — was it a typo, a missing word, the wrong order, or a command from a different tool? Smart command suggestions analyze the invalid input, identify the most likely intent, and print the closest valid commands so the user can recover quickly.

#### How the Integration Works

All valid commands in klish are defined in XML files. At startup, the daemon loads these files and builds an in-memory tree of every command, subcommand, and keyword the user is allowed to type. When the user enters a command, the daemon walks this tree word by word. If every word matches a node in the tree, the command executes. If any word has no match, the daemon returns a generic `Illegal command` error.

The upstream klish project (written in C) has no built-in way to intercept this failure and suggest corrections. Because klish is an external dependency that we do not maintain, the goal is to change as little of its source code as possible. The integration is therefore split into two independent layers:

    klish/
    ├── patches/
    │   └── klish-suggest.patch    # C hook (small, stable)
    └── scripts/
        └── suggest.py             # suggestion algorithm (Python, swappable)

**Layer 1 — The hook** (`klish-suggest.patch`) is a small C patch applied to the klish source at build time. It modifies a single function in the daemon: when command parsing fails, before the error is sent back to the client, the hook stores the rejected command line in the environment variable `KLISH_SUGGEST_LINE` and invokes an external script via `popen()`. Each line the script prints is appended to the error message. The hook has no knowledge of suggestion algorithms — it only runs the script and relays its output.

**Layer 2 — The algorithm** (`suggest.py`) is a standalone Python script that performs the suggestion logic. It reads the rejected command line from `KLISH_SUGGEST_LINE`, walks the command tree, and applies the [combined approach](docs/README_SUGGESTIONS.md#technique-16-combined-approach) to score candidates. Matches are printed to stdout; the hook appends them to the error shown to the user.

Because the two layers are independent, the algorithm can be updated without recompiling klish. Editing `suggest.py` alone is sufficient — the C patch, the Dockerfile, and the rest of the project remain untouched.

#### Categories of Mistakes

The suggestion engine handles several categories of user errors. Each category is explained below with an example.

##### Misspelled Command

The user typed a word that is close to a valid keyword but contains a typo — a missing letter, an extra letter, swapped adjacent letters, or a wrong letter.

    NetLab# show interfce
    Error: Illegal command
    Closest match:
      show interface

Here `interfce` is missing the letter `a`, which counts as an insertion edit (cost 1).

This also works when multiple words contain typos. The engine scores each word and sums the costs:

    NetLab# confgure termnial
    Error: Illegal command
    Closest match:
      configure terminal

Two corrections: `confgure` → `configure` (missing `i`, insertion cost 1) and `termnial` → `terminal` (adjacent `n` and `i` swapped, transposition cost 0). The total score is 1, which falls within the acceptance threshold.

##### Incomplete Command

The user typed a valid prefix but stopped too early. The command needs additional keywords to be complete. The engine finds all commands that begin with what was typed and lists them as completions.

    NetLab# show interfaces
    Error: Illegal command
    Closest match:
      show interfaces counters
      show interfaces summary

Nothing is misspelled. `show interfaces` is a valid beginning, but it is not a complete command on its own — it requires either `counters` or `summary` to finish.

##### Abbreviation

Experienced users often shorten commands (for example, typing `sh ip int` instead of `show ip interface`). These shortened forms look like severe typos to a generic distance matcher, but the engine recognizes that each word is a valid prefix of the corresponding keyword and expands it.

    NetLab# sh ip int
    Error: Illegal command
    Closest match:
      show ip interface

Each word is the beginning of the full keyword: `sh` → `show`, `ip` → `ip` (exact match), `int` → `interface`.

##### Swapped Words

The user typed the correct words but in the wrong order. This is common with commands that mix keywords and values, where the user accidentally places a value before its keyword.

    NetLab# router 65001 bgp
    Error: Illegal command
    Closest match:
      router bgp 65001

All three words — `router`, `65001`, and `bgp` — are present. They only need to be rearranged into the correct sequence `router bgp 65001`.

##### Hyphenated Keyword

Some commands use hyphenated keywords like `running-config` or `port-channel`. Users often type the parts as separate words or misspell one half. The engine splits each hyphenated keyword into its constituent parts and matches the user's words against them individually.

    NetLab# show rning config
    Error: Illegal command
    Closest match:
      show running-config

The engine splits `running-config` into `running` and `config`, matches `rning` against `running` (close enough at cost 1), and `config` against `config` (exact match). It then reassembles the result as `show running-config`.

##### Cross-Vendor Syntax

Network engineers often move between devices from different vendors (Cisco IOS, Juniper JUNOS, Arista EOS). When they type a command that is valid on another platform but does not exist locally, character-level scoring finds no close match because the keywords are entirely different. An AI backend covers this gap: it interprets the intent behind the typed command and maps it to the closest equivalent in the local command set.

Without AI enabled, such commands produce a generic error with no suggestion:

    NetLab# show ip bgp neighbors 10.0.0.1 received-routes
    Error: Illegal command

With AI enabled, the engine recognizes the intent and maps it to the local equivalent:

    NetLab# show ip bgp neighbors 10.0.0.1 received-routes
    Error: Illegal command
    Closest match:
      show bgp neighbors 10.0.0.1 received-routes

The input is valid Cisco IOS syntax. The local CLI uses `show bgp` instead of `show ip bgp`, but the intent is the same. This stage is off by default and requires connectivity to an inference server. When disabled or unreachable, the user still receives any suggestions produced by the local stages.

### Command Tree View

A Tree View is a hierarchical visualization of the entire command structure defined within the interface. Unlike standard help commands which only show the immediate options available at the current prompt, a tree view maps out every possible path, subcommand, and parameter in a single, nested diagram. This allows administrators and users to see the "big picture" of the system's capabilities at a glance.

The primary purpose of the tree view is to improve discoverability and auditing. In complex network operating systems, commands are often buried several levels deep. A tree view eliminates the need for trial-and-error navigation by exposing the relationships between parent views and child contexts. It serves as a live map of the CLI, ensuring users can quickly locate specific utilities or configuration endpoints.

Klish 3 is designed as a lightweight execution engine and does not include a built-in mechanism to render this visual tree at runtime. It stores the command hierarchy in memory for processing but lacks a native renderer to output it as a text graphic. To achieve this functionality, we can implement a custom solution using an external Python script. This script parses the underlying XML definition files and generates the visual tree.

    NetLab# tree

    [ CLI Tree for /root/.klish/main.xml ]

    └── main : Top-level view
        ├── tools : Enter tools mode
        ├── configure : Enter configuration mode
        │   └── terminal : Configure from the terminal
        ├── history : Display command history
        ├── exit : Exit
        ├── clear : Clear the terminal screen
        ├── show : Show system information
        │   ├── interface : Show interface details
        │   ├── ip : Show IP-related information
        │   │   └── interface : Show all interfaces with IP configuration
        │   ├── version : Show system version
        │   └── greeting : Display a welcome message
        ├── ping : Ping a destination
        ├── tree : Dump CLI structure tree
        └── search : Search

    └── view_tools : Tools Sub-menu
        ├── date : Show current date
        ├── sys-check : Check system resources
        └── exit : Go back

    └── view_config
        ├── interface : Select an interface to configure
        └── exit : Exit to main menu

    └── view_interface
        ├── ip : Internet Protocol
        │   └── address : Set IP address
        ├── shutdown : Disable the interface
        └── exit : Go back

### Command Search

Large CLIs quickly become difficult to navigate, especially when commands exist across multiple views and nested hierarchies. To make discovery easier, we have included a command search utility. Instead of guessing where a command lives, you can search for it by keyword and see every location where it appears, along with its help text.

    NetLab# search interface
    [ CLI Search: "interface" in /root/.klish/main.xml ]

    1. main -> show -> interface
      help: Show interface details

    2. main -> show -> ip -> interface
      help: Show all interfaces with IP configuration

    3. view_config -> interface
      help: Select an interface to configure

    4. view_interface -> shutdown
      help: Disable the interface
