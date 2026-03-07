# ChatbotAI: Core Conversational Module

`ChatbotAI` is the core, shared conversational engine for VersaAI. It can be extended for any application (VersaOS, VersaModeling, VersaGameEngine, etc.) by subclassing and adding app-specific logic or commands.

## How to Use
- Use `ChatbotAI` directly for generic conversation.
- For app-specific assistants, subclass `ChatbotAI` (e.g., `VersaOSChatbot`, `VersaModelingChatbot`).
- Select the appropriate model and agents for each app context.

## Example: VersaModelingChatbot
- **generate cube**: Generates a 3D cube in VersaModeling.
- **list tools**: Lists available modeling tools.
- **help**: Shows supported commands.
- **exit**: Exits VersaModeling assistant.

## Extending
1. Create a new subclass of `ChatbotAI` for your app.
2. Implement/override `getResponse` for app-specific commands.
3. Document new commands in the docs folder.

## Benefits
- One AI assistant architecture for all apps.
- Easy to extend and maintain.
- Consistent user experience across your software ecosystem.
