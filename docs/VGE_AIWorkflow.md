# VGE AI Workflow: From Creative Prompt to Game Project

## 1. Intent Parsing
- Detect broad/creative prompts (e.g., "I want to make a Fortnite-like FPS game").
- Use NLP/ML for genre, mechanic, and asset recognition.

## 2. Dialogue Management
- If prompt is vague, ask clarifying questions (VGEDialogueManager).
- Gather requirements interactively.

## 3. Planning Agent
- Decompose high-level requests into actionable steps (VGEPlanningAgent).
- Track progress and completion.

## 4. Knowledge Base
- Suggest templates, assets, and code snippets (VGEKnowledgeBase).
- Use genre/mechanic keys to retrieve starting points.

## Example Flow
1. User: "I want to make a Fortnite-like FPS game."
2. VersaAI: "To help you, I need more details. Do you want multiplayer? Building mechanics? What art style?"
3. User: "Yes, multiplayer and building. Realistic art style."
4. VersaAI: Planning agent decomposes steps, knowledge base suggests templates.

## Extending
- Integrate with asset libraries and engine APIs for real project generation.
- Use context/session to track user choices and workflow.
