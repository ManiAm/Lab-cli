# CLI Features

## Tab Completion (Static)

Klish provides context-aware Tab completion. As you type a command, it analyzes where you are in the syntax tree and suggests only the tokens that are valid at that position. When you type:

    NetLab> show <TAB>

Klish looks at all child elements defined under the `show` command in the XML and shows the available subcommands:

    NetLab> show
    greeting    interface    ip   terminal   version

## Tab Completion (Dynamic)

Klish can also perform dynamic (runtime-generated) Tab completion. Instead of listing static keywords, it can run a script or program to discover valid values. For example, after defining a parameter whose type pulls interface names from `/sys/class/net`, pressing Tab after show interface produces:

    NetLab> show interface <TAB>
    eth0   lo

Here, Klish:

- Detects that you are completing the `iface` parameter.
- Calls the completion script associated with its parameter type.
- Displays each returned value as a completion candidate.

## Inline Help

Klish provides inline help. When you use `?`, it shows both the command keyword and a short description:

    NetLab> show ?
    greeting   Display a welcome message
    interface  Show interface details
    ip         Show IP-related information
    terminal   Display terminal information
    version    Show system version

The left column comes from each command's `name` attribute, and the right column comes from its `help` attribute. This makes the CLI self-documenting. The user does not need to remember every command.

## Command Abbreviation

Klish 3 uses a strict command resolver by default. In this mode, users must either type the full command name or rely on tab completion to expand it. Typing a partial keyword that does not exactly match a command results in an error, even if the prefix is unique:

    NetLab> his
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

## Default Sub-commands

A default sub-command means a parent command has exactly one child, and the CLI automatically runs that child if the user stops early. Conceptually:

    show ip           ⇒ would automatically run the only child
    show ip interface ⇒ runs it explicitly

In Klish 3, this behavior is not automatic. The parent (`ip`) is considered incomplete unless you define an explicit `<ACTION>` for it. If you want `show ip` to execute the same logic as `show ip interface`, you must configure that intentionally in the XML.

## Parameter Validation

In Klish 2, parameter validation was often handled directly within the XML definition using the `pattern` attribute, which accepted a regular expression. The CLI engine itself would check the user's input against this regex before allowing the command to proceed. This provided a simple, declarative way to enforce formats like IP addresses or ranges without writing external code.

In Klish 3, this built-in regex engine has been removed in favor of a more flexible, plugin-based architecture. Validation is now delegated entirely to Symbols (functions) inside plugins. To validate a parameter, you define a `PTYPE` (Parameter Type) that contains an `<ACTION>`. When a user enters a value, Klish passes that value to the action (typically a script or a C function). The action must process the input and return an exit code: 0 for valid and non-zero for invalid. This approach, while slightly more verbose in XML, allows for arbitrarily complex validation logic beyond what simple regular expressions could achieve.

    NetLab> ping 8.8.8.256
    Error: Illegal command

## Command History

Command history refers to the ability to recall previously executed commands, typically accessed via arrow keys (for immediate reuse) or a `history` command (for a full list). In a standard shell environment like Bash, this is straightforward. A single shell process remains active for the entire session, holding all past inputs in its memory.

The standard `history` command fails in Klish 3 due to ephemeral execution environments. When the Klish server receives a command from the client, it spawns a brand new, isolated shell process solely to execute that specific action. This temporary shell is born with a "blank mind". It has no knowledge of previous commands and terminates immediately after its task is done. Therefore, if you create a Klish command that simply invokes `history`, it triggers a fresh shell that has essentially never run anything before, resulting in empty output.

The solution is to manually implement persistence using `<LOG>`. Since the Klish server has access to the command string currently being executed (exposed via the `KLISH_PARENT_LINE` environment variable), you can configure a global `<LOG>` tag to intercept every command and append it to a persistent text file. The `history` command is then redefined not to ask the shell for its memory, but to read and display the contents of this log file.

    NetLab> history
      1  show ip interface
      2  history
      3  show interface eth0

Note that this history is global, not per-session. Different CLI sessions all append to the same log file, so every user sees a unified record of commands that have been executed in the lab. This has clear benefits. It behaves like an audit trail, survives reconnects, and makes it easy to review what was tried previously. The trade-off is that it does not behave like a personal shell history. Commands from different users and sessions are mixed together, and history reflects system activity rather than just the current session.

## Text Filters

The Klish 3 engine provides native support for piping command output through text filters using the `|` operator. Any `<COMMAND>` element with the attribute `filter="true"` is automatically available as a pipe target, allowing users to refine output without additional plumbing.

    NetLab> show interface eth0 | grep inet
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

## Formatters

Formatters transform command output into a structured data format such as JSON, XML, or CSV. Unlike text filters that work on raw text line-by-line, a formatter requires the upstream command to produce structured data so the output is semantically meaningful.

| Formatter | Description                                      |
| --------- | ------------------------------------------------ |
| **json**  | Emit output as a JSON document.                  |
| **xml**   | Emit output as an XML document.                  |
| **csv**   | Emit output as comma-separated values.           |

In Klish 3, the `|` character is reserved by the engine for text filters. Formatters therefore use the `format` keyword instead. The `format` parameter is implemented as an optional subcommand inside each `show` command. When present, the command switches to a structured data source (for example, `ip -j addr show` instead of `ip addr show`) and pipes the result through a format converter

Json Example:

    NetLab> show interface eth0 format json

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

    NetLab> show version format csv

    "system","node","release","version","machine"
    "Linux","abcd1234","6.6.87","#1 SMP ...","x86_64"

XML Example:

    NetLab> show ip interface format xml

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

    NetLab> show interface eth0 format json | grep ifname
        "ifname": "eth0",

> Piping a text filter after a formatter will return matching lines but may produce an incomplete document.

## External Scripts

While Klish allows you to write small logic blocks directly inside the XML, complex operations are best handled by invoking external Bash or Python scripts. This approach treats the CLI as a "frontend" while offloading the heavy lifting to specialized backend scripts.

The script plugin in Klish spawns a standard shell instance. To invoke an external script, you simply provide the full path to the executable file within the `<ACTION>` tag. You can pass Klish parameters to these scripts either as command-line arguments or by reading the environment variables Klish automatically exports.

The following example demonstrates the `sys-check` command. This command illustrates how Klish captures user input (a parameter) and passes it directly to an underlying Bash script to control execution logic. In this scenario, the user selects the `cpu` target. Klish passes this argument to the script, which then filters the system information accordingly.

    NetLab# sys-check cpu
    --------------------------------
    Checking System: cpu
    --------------------------------
    22:09:21 up 4 days, 13:25,  0 user,  load average: 0.50, 0.49, 0.37
    Processors: 36
    --------------------------------

## Lua

Klish includes Lua as a built-in scripting engine. In Klish 3, the Lua plugin is part of the core architecture and is the preferred way to add logic that needs to be closely integrated with the CLI itself such as context handling, prompts, validation, and session-aware behavior.

Lua is not a replacement for Bash or Python. Instead, it fills a gap those languages cannot easily solve inside a CLI engine. Lua executes inside the Klish process (not as an external program), which allows it to:

- Access CLI context and parameters directly
- Maintain session state without temporary files
- Build dynamic prompts and modes
- Run lightweight control logic without creating new processes
