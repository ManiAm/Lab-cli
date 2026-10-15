
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

### Client-Server Architecture

Klish 2 operates as a single monolithic binary (`clish`) and handles parsing, execution, and user interaction simultaneously. Klish 3, on the other hand, adopts a Client-Server architecture. This decoupling significantly improves stability, concurrency, and performance.

- `klishd`: A background daemon that loads XML configuration files, maintains the internal database, and listens for incoming connections.

- `klish`: A lightweight "dumb terminal" client. It connects to the daemon (typically via a Unix Socket) to transmit keystrokes and display output.

Communication between the two uses the Klish Transfer Protocol (KTP). Core utilities are provided by [faux](https://src.libcode.org/pkun/faux.git), a shared C library developed alongside Klish to avoid duplicating common functionality.

### Terminal Sessions

When a client connects, the daemon creates a unique environment for that specific interaction. The klish client connects to the master klishd process. Upon accepting the connection, the master klishd forks a new child process dedicated exclusively to that connection. This child process represents the Session. This new model provides the following characteristics:

- **Isolation**: Every connected user is assigned a dedicated process with a unique Process ID (PID).

- **Memory Separation**: Because sessions run as separate processes, they do not share memory space. User A cannot access or modify User B's variables. This ensures high stability. A crash in one session will not affect the main daemon or other users.

- **Lifetime**: A session persists only as long as the client remains connected. Terminating the client (e.g., typing `exit` or closing the terminal) causes the corresponding klishd child process to terminate.

To verify this architecture, we can open multiple interactive terminals to the container and inspect the process hierarchy. By running `show terminal session` in two separate terminals, we can observe unique PIDs for each user, confirming they are separate entities.

First client:

    NetLab> show terminal session

    --- Session Information ---
    Session PID: 22
    User ID:     0
    User Name:   root
    Command:     session

Second client:

    NetLab> show terminal session

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
