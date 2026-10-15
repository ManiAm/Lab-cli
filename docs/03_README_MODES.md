# Views, Modes & Access Control

## Views

A **view** in Klish is a logical container that groups related commands together. Think of it as a separate "room" inside the CLI — when you enter a view, you see only the commands that belong to that room.

For example, navigating from the main menu into the `tools` view changes the prompt and shows only the commands available there:

    NetLab> tools
    NetLab(tools)#
      date       Show current date
      sys-check  Check system resources
      exit       Go back

Views provide four key benefits:

1. **Organization** — Instead of presenting every possible command at once, views group them into manageable categories. You only see what is relevant to your current task.

2. **Safety** — Sensitive commands (like `reboot` or `format`) are only accessible inside specific views, reducing the risk of running something dangerous by accident.

3. **Workflow guidance** — When you enter a view for a specific object (for example, a network interface), every command you type automatically applies to that object. You do not need to repeat the object name with every command.

4. **Name reuse** — The same command name can exist in different views without conflict. For example, `restart` could restart a single service inside a Service View, but restart the entire system inside a System View.

This pattern is not unique to Klish. Nearly every managed network device uses the same idea. The next section walks through the industry-standard Cisco IOS hierarchy, so you can see where this design comes from.

## Industry-Standard CLI Model

Cisco IOS introduced the modal CLI that most network vendors follow today. The hierarchy has four levels, each entered by typing a specific command and exited with `exit`. The prompt always to show which level you are in.

### The Cisco IOS Mode Hierarchy

<img src="../pics/cisco-ios-views.png" alt="segment" width="750">

The sections below explain each level step by step: what it is for, how you get into it, and what you can (and cannot) do once inside.

### Step 1 — User EXEC Mode

**Prompt:** `Router>`

This is the first level every user sees after logging in via SSH or console. It provides only basic, read-only commands — `ping`, `traceroute`, `show clock` — and nothing that can modify the device. Think of it as the lobby of a building: you can look around, but you cannot open any doors.

The name *EXEC* refers to the command-execution environment (as opposed to configuration). The *User* qualifier distinguishes this restricted level from the more powerful Privileged EXEC level.

### Step 2 — Privileged EXEC Mode (Enable Mode)

**Prompt:** `Router#`

To reach this level, type `enable` and enter the enable password. The session escalates from the `>` prompt to the `#` prompt.

Privileged EXEC unlocks full operational access: every `show` command (including `show running-config`), diagnostic tools (`debug`, `clear`), and system operations (`copy`, `reload`). However, it does **not** allow configuration changes — you cannot modify interfaces, routing protocols, or any part of the running config. To make changes, you must go one level deeper.

### Step 3 — Global Configuration Mode

**Prompt:** `Router(config)#`

Enter this level by typing `configure terminal` (often abbreviated `conf t`) from Privileged EXEC. Commands here apply to the device as a whole — setting the hostname, adding static routes, or entering a sub-configuration mode for a specific component.

The separation between Privileged EXEC and Global Configuration exists so that operators who only need to monitor and troubleshoot cannot accidentally change the device's configuration.

### Step 4 — Interface Configuration Mode (and Other Sub-Modes)

**Prompt:** `Router(config-if)#`

From Global Configuration, type an interface name — for example, `interface GigabitEthernet0/1` — to enter a sub-configuration mode scoped to that single interface. Every command you type (`ip address`, `shutdown`, `speed`, `duplex`) applies only to that interface.

The same pattern extends to other sub-modes: `(config-router)` for routing protocols, `(config-line)` for console and VTY lines, and so on.

### Mode Summary

| Mode            | Prompt      | Read config? | Clear / reload? | Change config? |
|-----------------|-------------|:------------:|:---------------:|:--------------:|
| User EXEC       | `>`         | Limited      | ✗               | ✗             |
| Privileged EXEC | `#`         | Full         | ✓               | ✗             |
| Global Config   | `(config)#` | Full         | ✓               | ✓             |

The three-tier model separates **observation** (User EXEC) from **operation** (Privileged EXEC) from **configuration** (Global Config). Each deeper level narrows the scope of available commands, and the prompt always reflects the current context.

### The Access-Control Problem

The view/mode hierarchy controls *which commands are available where*, but it does not control *who is allowed to run them*. These are two separate concerns:

| Concept            | What it controls                                     |
|--------------------|------------------------------------------------------|
| **View / Mode**    | Which commands are *available* at the current prompt |
| **Access control** | Which users can *execute* a command or enter a mode  |

> Views determine context; access control determines permission.

Early Cisco IOS had just two access-control tiers — User EXEC and Privileged EXEC. You typed `enable`, entered a shared password, and received full admin access. It was all-or-nothing.

This broke down as teams grew. A NOC technician who only needed `show running-config` for troubleshooting also received the ability to `reload` the device, because both commands lived behind the same `enable` gate. The industry responded by layering access-control mechanisms on top of the mode hierarchy. The sections below walk through each one, from simplest to most granular.

#### 1. Privilege Levels (0–15)

Cisco IOS assigns every command a numeric privilege level, and every user session runs at a level. Three levels matter by default:

| Level | What it means |
|-------|---------------|
| 0     | `logout`, `enable`, `disable`, `help`, `exit` — nothing else |
| 1     | User EXEC (`>`) — basic `show`, `ping`, `traceroute` |
| 15    | Privileged EXEC (`#`) — everything |

Typing `enable` with no argument escalates the session to level 15. Levels 2–14 are empty by default, but an administrator can move individual commands into them to create custom tiers:

```text
Router(config)# privilege exec level 5 show running-config
Router(config)# enable secret level 5 SomePassword
```

A user at level 1 can now type `enable 5`, enter `SomePassword`, and gain access to `show running-config` without reaching full level-15 Privileged EXEC.

> **Note:** In practice, most operators only use levels 1 and 15. The 16-tier ladder is rarely exploited.

#### 2. Per-User Privilege Assignment

The `enable <level>` approach works, but the level password is shared — every operator who needs level 5 uses the same `SomePassword`. There is no way to track who ran a command, and revoking one person's access means changing the password for everyone.

The fix is to assign a privilege level directly to a named user account:

```text
Router(config)# username noc_operator privilege 5 secret MyPassword
```

Now `noc_operator` logs in with personal credentials and lands at level 5 automatically — no `enable 5` step required. Each operator has a unique username, so the device can log exactly who did what, and revoking access means removing a single account.

#### 3. Parser Views (Role-Based CLI Views)

Parser views go further by defining named roles with an explicit whitelist of allowed commands:

```text
Router(config)# parser view NOC-VIEW
Router(config-view)# secret MyViewPassword
Router(config-view)# commands exec include show
Router(config-view)# commands exec include ping
Router(config-view)# commands exec exclude clear
```

A user assigned to `NOC-VIEW` can only run the commands listed — everything else is hidden. This is the closest Cisco IOS gets to true Role-Based Access Control (RBAC).

#### 4. TACACS+ / RADIUS (External Per-Command Authorization)

The most granular approach: every command the user types is sent to an external AAA server, which returns *permit* or *deny*. This is what large enterprises use for full per-user, per-command audit and control.


## Mode Hierarchy in Lab-CLI

Lab-CLI implements the same four-tier model described above. When you start the CLI, you land in User EXEC mode with a limited set of safe, read-only commands:

    NetLab> show version
    Linux netlab-cli 6.6.87 ...

    NetLab> show running-config
    Error: Illegal command

To access operational commands, type `enable` to enter Privileged EXEC mode:

    NetLab> enable
    NetLab# show running-config
    Running Configuration (simulated)
    !
    hostname NetLab
    !

To make configuration changes, enter Global Configuration mode, then navigate into a specific interface:

    NetLab# configure terminal
    NetLab(config)# interface eth0
    NetLab(config-if-eth0)# shutdown
    RTNETLINK answers: Operation not permitted

To return to a previous mode, type `exit` at any level. From Privileged EXEC, you can also type `disable` to drop back to User EXEC:

    NetLab(config-if-eth0)# exit
    NetLab(config)# exit
    NetLab# disable
    NetLab>

> **Note on Permissions:** The "Operation not permitted" error above is expected. The CLI runs inside a container without the `NET_ADMIN` capability, so the kernel blocks the state change. The output confirms that Klish successfully triggered the command script.

## Enable Password

In the current Lab-CLI implementation, typing `enable` immediately escalates to Privileged EXEC mode with no authentication. This is intentional for a lab environment where frictionless access matters more than security. In a production system, the `enable` command would prompt for a password before granting access.

### How Vendors Implement It

The enable password mechanism follows the same pattern across all major vendors. It comes down to three steps: store a hash, prompt the user, and compare.

**Step 1 — The administrator sets a password.**

When the administrator configures `enable secret`, the device does **not** store the plaintext password. Instead, it passes the password through a one-way hashing algorithm and stores only the resulting hash in the configuration file:

```text
Router(config)# enable algorithm-type scrypt secret MySecretPassword
```

The running configuration shows the hash, never the original password:

```text
enable secret 9 $9$salt$hashed_output_here
```

The `9` indicates the scrypt algorithm. The stored string contains the algorithm identifier, the random salt, and the hash — everything the device needs to verify a password later, but nothing that can be reversed to recover the original.

**Step 2 — A user types `enable` and enters a password.**

The device prompts for the password, reads it without echoing characters to the screen, and hashes the input using the same algorithm and salt that were stored in Step 1.

**Step 3 — The device compares the two hashes.**

If the newly computed hash matches the stored hash, the user is granted access. If not, the device prints "Access denied" and the session stays in User EXEC. At no point does the device need to know or reconstruct the original password.

### Hash Algorithm Evolution

Cisco IOS has gone through several hash types over the years, each replacing the previous one as cryptographic standards advanced:

| Type | Algorithm       | Status        | Notes |
|------|-----------------|---------------|-------|
| 0    | Cleartext       | Deprecated    | Password stored as-is — visible to anyone who reads the config |
| 7    | Vigenère cipher | Deprecated    | Reversible in seconds with freely available tools |
| 5    | Salted MD5      | Deprecated    | One-way hash, but MD5 is now considered too fast for password hashing — vulnerable to brute-force with modern GPUs |
| 8    | PBKDF2/SHA-256  | Supported     | 80-bit salt, 20,000 iterations — deliberately slow to resist brute-force |
| 9    | scrypt          | Best practice | 80-bit salt, 16,384 iterations — memory-hard, making GPU attacks impractical |

The key insight is that modern algorithms (Type 8 and 9) are intentionally **slow and memory-expensive** to compute. This is the opposite of what you want in most software, but for password hashing, slowness is the entire point — it makes brute-force attacks take years instead of minutes.

### Enable Password in Lab-CLI

Lab-CLI implements the enable password mechanism described above. By default, no password is set (lab mode — `enable` grants access immediately). An administrator can configure a password from Global Configuration mode:

```text
NetLab> enable
NetLab# configure terminal
NetLab(config)# enable-secret set
New enable password: ********
Confirm password: ********
% Enable password has been set
NetLab(config)# exit
NetLab# exit
```

Once set, `enable` prompts for the password before granting access:

```text
NetLab> enable
Password: ********
NetLab#
```

A wrong password keeps the user in User EXEC:

```text
NetLab> enable
Password: ********
% Access denied
NetLab>
```

To remove the password and return to lab mode:

```text
NetLab(config)# enable-secret remove
% Enable password removed (lab mode — no password required)
```

**How it works under the hood:**

1. `enable-secret set` hashes the password with SHA-512 (via `openssl passwd -6`) and stores only the hash in `/etc/netlab/enable.secret`.
2. The `enable` command in `main.xml` runs two `<ACTION>` tags in sequence:

```xml
<COMMAND name="enable" help="Enter Privileged EXEC mode">
    <ACTION sym="script" in="tty" out="tty">bash /opt/netlab-cli/scripts/enable_auth.sh</ACTION>
    <ACTION sym="nav@klish">push view_priv_exec</ACTION>
</COMMAND>
```

3. The first ACTION runs `enable_auth.sh`, which reads the password interactively (`read -s`), hashes the input with the same salt, and compares. It exits 0 on match, 1 on mismatch.
4. The second ACTION (`nav push`) only executes if the first exits with code 0. If the password is wrong, Klish stops and the user stays in User EXEC.
5. If no password file exists, the script exits 0 immediately — no prompt, no delay.

This is the same hash-then-compare mechanism used by `/etc/shadow` on Linux and by PAM (`pam_unix.so`) for system login authentication.

## Configuration Sessions

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
