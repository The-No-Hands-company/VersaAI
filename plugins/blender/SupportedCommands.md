# Supported Commands for VersaAI Blender Plugin

## Mesh Generation
- `generate cube` — Creates a new cube mesh in the scene.
- `generate sphere` — Creates a new sphere mesh.
- `generate torus` — Creates a torus mesh.

## Scene Automation
- `auto-arrange scene` — Automatically arranges objects for better layout.
- `center all objects` — Moves all objects to the scene center.

## Asset Search
- `search asset tree` — Finds assets in your Blender project.
- `find texture wood` — Searches for wood textures.

## Multi-Turn Conversation
- Use session ID to maintain context across multiple prompts.
- Example:
  - Prompt 1: `generate cube`
  - Prompt 2: `move cube to (1,2,3)`

## Custom Tasks
- More commands can be added as VersaAI evolves.
- You can request new features via prompt (e.g., `add lighting setup`).
