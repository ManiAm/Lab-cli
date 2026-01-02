
# Lab-cli

Lab-CLI is a Klish-based command environment designed for hands-on experimentation, demos, and controlled system operations in the lab. Instead of running arbitrary Linux commands, Lab-CLI exposes a safe, curated set of workflows - things like viewing system information, changing basic settings, and triggering lab utilities - all through a structured, network-device-style interface.

Because Lab-CLI runs on top of Klish 3’s client-server architecture, it cleanly separates command parsing from execution logic. That makes it suitable for multi-user environments, containerized setups, and scenarios where command auditing and safety matter. Scripts live in one place, configuration lives in another, and the CLI becomes a stable interface layered on top.

Refer to the following guides for more details:

- [Klish Introduction](README_KLISH.md)
- [CLI in SONiC Ecosystem](README_CLI_SONIC.md)

## Project Structure

The project is self-contained inside a container, giving you an isolated, reproducible setup. All CLI definitions, scripts, and configuration files live under the `klish/` directory and are bundled into the image at build time.

    ├─ docker-compose.yml
    ├─ Dockerfile
    └─ klish/
        ├─ xml/
        │  └─ main.xml
        ├─ scripts/
        │  └─ ...
        ├─ config/
        │  ├─ klishd.conf       # server config
        │  └─ klish.conf        # client config
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

Some CLIs (for example IOS-style CLIs) allow command abbreviations. This can be convenient when:

- Commands are long
- Operators already know the syntax well
- Speed of typing matters

Klish 2 had a fuzzy matching logic that would execute a command if it was unambiguous (e.g., `ver --> version`). Klish 3 removed this to prevent ambiguity and simplify the resolution engine. This is a fundamental change in Klish 3. It uses a strict command resolver that requires exact matches (or explicit aliases). Keywords must be typed in full even if the prefix is unique.

    NetLab# show ver
    Error: Illegal command

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

In Klish 3, the pipe (`|`) character is handled natively by the engine to chain commands, but you must explicitly mark commands as "filters" for them to be available after the pipe. You do this by adding the attribute `filter="true"` to the `<COMMAND>` tag.

    NetLab# show interface eth0 | grep inet
        inet 172.18.0.2/16 brd 172.18.255.255 scope global eth0

The following utilities are available:

| Utility     | Description                                         |
| ----------- | --------------------------------------------------- |
| **head**    | Keep only the first N lines of output.              |
| **tail**    | Keep only the last N lines of output.               |
| **include** | Show only lines that contain the given text.        |
| **exclude** | Hide lines that contain the given text.             |
| **grep**    | Search output for lines matching a text (or regex). |
| **count**   | Count the number of lines in the output.            |

### Formatters

Formatters are specialized tools designed to completely transform the structure of data, rather than just filtering its content. Unlike simple text utilities (like `grep` or `head`) that work line-by-line, a formatter typically consumes the entire dataset at once, parses its internal logic, and rebuilds it into a structured format like JSON, XML, or CSV. Because this process changes the fundamental nature of the data, formatters are usually terminal commands meaning they are the final step in a command chain. You rarely pipe the output of a JSON formatter into another text tool because the predictable structure is lost or changed.

We technically can use pipes for formatters, but it is fragile compared to filters like `head` or `tail`. A standard pipe (`|`) only transmits raw text (Standard Output). It does not transmit metadata about what generated that text. Filters don't care about context. "Give me the first 5 lines" works equally well for a list of files, a list of IPs, or a poem. However, formatters need context. To convert text to JSON, the parser must know if the text is an IP address table, a file directory, or user stats. Raw text is ambiguous. A command such as `show interface | json` fails unless you explicitly tell the JSON tool, "This text coming from the pipe is network interface data".

There is no "Magic Wand" algorithm that can take the output of any arbitrary command and correctly format it into JSON, XML, or CSV. Every command has a unique output signature. `ls -l` produces columns of permissions and filenames; `ip addr` produces indented blocks of key-value pairs; `free -m` produces a grid of memory stats. Because the input structures vary so wildly, each command requires its own specific formatter logic. You cannot write a single function that handles `ls`, `ip`, and `uname` simultaneously.

The most robust way to handle formatting is when the command itself supports it natively. A notable example is the modern Linux `ip` command. Instead of relying on an external tool to read its text output and guess the structure, the developers of `ip` built the formatting logic internally. The command `ip -j addr show` skips printing printing human-readable text and directly outputs structured JSON.

We have added three sample CLIs:

    NetLab# export interface format json
    NetLab# export interface format xml
    NetLab# export interface format csv

Generating the full interface dataset in standard JSON format:

    NetLab# export interface format json

    [
      {
        "ifindex": 1,
        "ifname": "lo",
        "flags": [
          "LOOPBACK",
          "UP",
          "LOWER_UP"
        ],
        "mtu": 65536,
    ...

Generating a flattened comma-separated values list, useful for spreadsheets:

    NetLab# export interface format csv

    "interface","state","mtu","ip"
    "lo","UNKNOWN",65536,"127.0.0.1"
    "eth0","UP",1500,"172.18.0.2"

You can still pipe formatted output into text filters:

    NetLab# export interface format json | grep eth
        "ifname": "eth0",
        "link_type": "ether",
            "label": "eth0",

> Note that doing so may result in invalid JSON structure.

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
        ├── export : Export system data
        │   └── interface : Export interface data
        │       └── format : Output format (All interfaces)
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

    3. main -> export -> interface
      help: Export interface data

    4. main -> export -> interface -> format
      help: Output format (All interfaces)

    5. view_config -> interface
      help: Select an interface to configure

    6. view_interface -> shutdown
      help: Disable the interface
