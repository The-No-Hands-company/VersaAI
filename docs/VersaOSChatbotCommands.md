# VersaOSChatbot Supported Commands

This document lists the commands currently supported by the VersaOSChatbot module.

## Commands

- **open versamodeling**
  - Opens the VersaModeling application.

- **list apps**
  - Displays a list of available applications: VersaModeling, VersaGameEngine, VersaOS.

- **help**
  - Shows a list of supported commands.

- **exit**
  - Exits VersaOS with a goodbye message.

## Example Usage
```
Enter command: help
Commands: open versamodeling, list apps, help, exit.
```

---

## Extending VersaOSChatbot

To add new commands:

1. Edit `VersaOSChatbot.cpp` and add a new `else if` block for your command in `getResponse`.
2. Document the new command here under **Commands**.
3. Optionally, add example usage below.

### Example: Adding a "status" Command

- **status**
  - Shows the current status of VersaOS.

Example usage:
```
Enter command: status
VersaOS is running normally.
```

---

## Changelog

- **2025-07-15**: Initial documentation created with commands: open versamodeling, list apps, help, exit.
