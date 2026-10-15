# Command Discovery

## Command Tree View

A Tree View is a hierarchical visualization of the entire command structure defined within the interface. Unlike standard help commands which only show the immediate options available at the current prompt, a tree view maps out every possible path, subcommand, and parameter in a single, nested diagram. This allows administrators and users to see the "big picture" of the system's capabilities at a glance.

The primary purpose of the tree view is to improve discoverability and auditing. In complex network operating systems, commands are often buried several levels deep. A tree view eliminates the need for trial-and-error navigation by exposing the relationships between parent views and child contexts. It serves as a live map of the CLI, ensuring users can quickly locate specific utilities or configuration endpoints.

Klish 3 is designed as a lightweight execution engine and does not include a built-in mechanism to render this visual tree at runtime. It stores the command hierarchy in memory for processing but lacks a native renderer to output it as a text graphic. To achieve this functionality, we can implement a custom solution using an external Python script. This script parses the underlying XML definition files and generates the visual tree.

    NetLab> tree

    [ CLI Tree for /root/.klish/main.xml ]

    └── main : User EXEC mode
        ├── history : Display command history
        ├── exit : Exit
        ├── clear : Clear the terminal screen
        ├── enable : Enter Privileged EXEC mode
        ├── show : Show system information
        │   ├── interface : Show interface details
        │   ├── ip : Show IP-related information
        │   │   └── interface : Show all interfaces with IP configuration
        │   ├── version : Show system version
        │   ├── greeting : Display a welcome message
        │   └── terminal : Display terminal information
        │       └── session : Show current session details
        ├── ping : Ping a destination
        ├── traceroute : Trace route to a destination
        ├── tree : Dump CLI structure tree
        ├── search : Search for a CLI command
        └── tools : Enter tools mode

    └── view_priv_exec : Privileged EXEC mode
        ├── history : Display command history
        ├── disable : Return to User EXEC mode
        ├── exit : Exit
        ├── clear : Clear the terminal screen
        ├── show : Show system information
        │   ├── interface : Show interface details
        │   ├── ip : Show IP-related information
        │   │   └── interface : Show all interfaces with IP configuration
        │   ├── version : Show system version
        │   ├── bgp : Show BGP information
        │   │   ├── summary : Show BGP summary
        │   │   └── neighbors : Show BGP neighbors
        │   ├── interfaces : Show all interfaces
        │   │   ├── counters : Show interface counters
        │   │   └── summary : Show interface summary
        │   ├── running-config : Show running configuration
        │   ├── greeting : Display a welcome message
        │   └── terminal : Display terminal information
        │       └── session : Show current session details
        ├── ping : Ping a destination
        ├── traceroute : Trace route to a destination
        ├── tree : Dump CLI structure tree
        ├── search : Search for a CLI command
        ├── debug : Enable debug output
        │   ├── bgp : Debug BGP events
        │   ├── daemon : Debug daemon events
        │   └── telemetry : Debug telemetry events
        ├── sys-check : Check system resources
        ├── tools : Enter tools mode
        └── configure : Enter configuration mode
            ├── terminal : Configure from the terminal
            └── session : Enter a named configuration session

    └── view_tools : Tools Sub-menu
        ├── date : Show current date
        ├── sys-check : Check system resources
        └── exit : Go back

    └── view_config
        ├── interface : Select an interface to configure
        ├── enable-secret : Manage the enable password
        │   ├── set : Set the enable password
        │   ├── remove : Remove the enable password (lab mode)
        │   └── status : Check if an enable password is configured
        ├── router : Configure a routing protocol
        │   └── bgp : BGP routing protocol
        ├── neighbor : Configure a BGP neighbor
        ├── show : Show configuration information
        │   └── candidate-config : Show candidate configuration (draft)
        ├── commit : Apply buffered changes
        └── exit : Exit to Privileged EXEC mode

    └── view_interface
        ├── ip : Internet Protocol
        │   └── address : Set IP address
        ├── shutdown : Disable the interface
        └── exit : Go back

## Command Search

Large CLIs quickly become difficult to navigate, especially when commands exist across multiple views and nested hierarchies. To make discovery easier, we have included a command search utility. Instead of guessing where a command lives, you can search for it by keyword and see every location where it appears, along with its help text.

    NetLab> search interface
    [ CLI Search: "interface" in /root/.klish/main.xml ]

    1. main -> show -> interface
       help: Show interface details

    2. main -> show -> ip -> interface
       help: Show all interfaces with IP configuration

    3. view_priv_exec -> show -> interface
       help: Show interface details

    4. view_priv_exec -> show -> ip -> interface
       help: Show all interfaces with IP configuration

    5. view_priv_exec -> show -> interfaces
       help: Show all interfaces

    6. view_priv_exec -> show -> interfaces -> counters
       help: Show interface counters

    7. view_priv_exec -> show -> interfaces -> summary
       help: Show interface summary

    8. view_config -> interface
       help: Select an interface to configure

    9. view_interface -> shutdown
       help: Disable the interface
