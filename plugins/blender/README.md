# VersaAI Blender 4.5 Plugin

## Overview
VersaAI Assistant brings AI-powered workflows to Blender. Enter prompts, automate tasks, and interact with VersaAI directly in the Blender UI.

## Installation
1. Copy `versaai_blender_addon.py` to your Blender addons directory.
2. In Blender, go to Edit > Preferences > Add-ons > Install, and select the file.
3. Enable the "VersaAI Assistant" addon.

## Usage
- Open the Sidebar in the 3D View and select the "VersaAI" tab.
- Enter your prompt (e.g., `generate cube`, `auto-arrange scene`, `search asset tree`).
- Set a session ID for multi-turn conversations.
- Configure the server URL if using a remote VersaAI instance.
- Click "Ask VersaAI" to send your prompt and view the response.

## Supported Example Commands
- `generate cube` — Create a new cube mesh in the scene.
- `auto-arrange scene` — Automatically arrange objects for better layout.
- `search asset tree` — Find assets in your Blender project.
- Multi-turn conversations (with session ID).

## Notes
- VersaAI must be running and accessible at the configured server URL.
- More commands and features can be added as VersaAI evolves.

## Troubleshooting
- If you see errors about `bpy` or properties, ensure you are running the addon inside Blender.
- Check the server URL and VersaAI backend status if you get connection errors.
