# VersaAI Code Editor Integration

## Overview

This document outlines the integration of VersaAI's intelligent code assistance capabilities into the NLPL Code Editor, transforming it into an AI-powered development environment.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    NLPL Code Editor                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Monaco Editor (UI)                      │  │
│  │  - Syntax highlighting                               │  │
│  │  - Code editing                                      │  │
│  │  - IntelliSense integration                          │  │
│  └────────────┬─────────────────────────────────────────┘  │
│               │                                              │
│  ┌────────────▼─────────────────────────────────────────┐  │
│  │         VersaAI Integration Layer (Node.js)          │  │
│  │  - IPC Bridge (Electron)                             │  │
│  │  - Python subprocess management                      │  │
│  │  - Model router communication                        │  │
│  └────────────┬─────────────────────────────────────────┘  │
│               │                                              │
└───────────────┼──────────────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────────────┐
│                   VersaAI Backend (Python)                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Model Router                            │   │
│  │  - DeepSeek Coder 1.3B/6.7B (local)                 │   │
│  │  - StarCoder2 7B/15B (local)                        │   │
│  │  - CodeLlama 7B/13B/34B (local)                     │   │
│  │  - Qwen2.5-Coder 7B/14B (local)                     │   │
│  │  - GPT-4/Claude (API fallback)                      │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              RAG System                              │   │
│  │  - Codebase indexing                                 │   │
│  │  - Semantic search                                   │   │
│  │  - Context retrieval                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Memory & Context Management                  │   │
│  │  - Conversation history                              │   │
│  │  - File context tracking                             │   │
│  │  - Project knowledge graph                           │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────┘
```

## Integration Points

### 1. **Code Completion & Suggestions**
- **Real-time code completion** using DeepSeek/StarCoder models
- **Context-aware suggestions** based on current file and project structure
- **Multi-language support** (NLPL, Python, TypeScript, C++, etc.)

### 2. **Inline AI Assistant**
- **Cmd+K** (Mac) / **Ctrl+K** (Win/Linux): Inline AI chat
- **Code explanation** for selected text
- **Refactoring suggestions**
- **Bug detection** and fix recommendations

### 3. **Sidebar AI Panel**
- **Persistent chat interface** for code discussions
- **File-aware conversations** (knows current file context)
- **Project-wide code search** using RAG
- **Multi-model support** (switch between local models)

### 4. **Code Actions**
- **Generate code** from natural language
- **Write tests** for selected functions
- **Add documentation** and comments
- **Optimize code** performance

## Implementation Steps

### Phase 1: Backend Integration (Week 1)

#### Step 1.1: Create VersaAI Bridge Service
```bash
versaai/
├── code_editor_bridge/
│   ├── __init__.py
│   ├── server.py              # WebSocket/HTTP server for editor
│   ├── completion_service.py  # Code completion logic
│   ├── chat_service.py        # AI chat interface
│   └── indexer_service.py     # Codebase indexing
```

#### Step 1.2: Implement Code Completion Service
```python
# versaai/code_editor_bridge/completion_service.py
class CodeCompletionService:
    def __init__(self, model_router):
        self.router = model_router
        self.cache = CompletionCache()
        
    async def get_completion(self, context):
        """
        Get code completion based on context
        
        Args:
            context: {
                'file_path': str,
                'language': str,
                'prefix': str,  # Code before cursor
                'suffix': str,  # Code after cursor
                'line': int,
                'column': int
            }
        """
        # Use best model for code task
        model = self.router.route_to_best_model(
            task_type="code_completion",
            language=context['language']
        )
        
        # Build prompt with file context
        prompt = self._build_completion_prompt(context)
        
        # Get completion
        completion = await model.complete(prompt)
        
        return self._parse_completion(completion)
```

#### Step 1.3: Implement Chat Service
```python
# versaai/code_editor_bridge/chat_service.py
class EditorChatService:
    def __init__(self, model_router, rag_system):
        self.router = model_router
        self.rag = rag_system
        self.conversations = {}  # session_id -> conversation
        
    async def chat(self, session_id, message, file_context=None):
        """
        Handle chat message with file context
        
        Args:
            session_id: Unique session identifier
            message: User message
            file_context: Current file information
        """
        # Retrieve relevant code context
        if file_context:
            code_context = await self.rag.retrieve_context(
                query=message,
                file_path=file_context['path'],
                max_tokens=2000
            )
        else:
            code_context = None
            
        # Route to best model
        response = await self.router.chat(
            message=message,
            context=code_context,
            conversation_id=session_id,
            task_type="code_assistant"
        )
        
        return response
```

#### Step 1.4: Create WebSocket Server
```python
# versaai/code_editor_bridge/server.py
import asyncio
import websockets
import json

class VersaAIEditorServer:
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.completion_service = CodeCompletionService(model_router)
        self.chat_service = EditorChatService(model_router, rag)
        
    async def handle_message(self, websocket, path):
        async for message in websocket:
            data = json.loads(message)
            
            if data['type'] == 'completion':
                result = await self.completion_service.get_completion(
                    data['context']
                )
            elif data['type'] == 'chat':
                result = await self.chat_service.chat(
                    session_id=data['session_id'],
                    message=data['message'],
                    file_context=data.get('file_context')
                )
            elif data['type'] == 'index_project':
                result = await self.indexer.index_directory(
                    data['project_path']
                )
            
            await websocket.send(json.dumps(result))
    
    async def start(self):
        async with websockets.serve(self.handle_message, self.host, self.port):
            print(f"VersaAI Editor Bridge running on ws://{self.host}:{self.port}")
            await asyncio.Future()  # Run forever

# Start server
if __name__ == "__main__":
    server = VersaAIEditorServer()
    asyncio.run(server.start())
```

### Phase 2: Frontend Integration (Week 2)

#### Step 2.1: Add VersaAI Client to Editor

Create new file in code editor:
```bash
code_editor/src/renderer/versaai/
├── VersaAIClient.ts          # WebSocket client
├── CompletionProvider.ts     # Monaco completion provider
├── ChatPanel.tsx             # AI chat UI component
└── types.ts                  # TypeScript types
```

#### Step 2.2: WebSocket Client
```typescript
// code_editor/src/renderer/versaai/VersaAIClient.ts
export class VersaAIClient {
  private ws: WebSocket | null = null;
  private readonly url = 'ws://localhost:8765';
  private messageHandlers: Map<string, (data: any) => void> = new Map();

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.url);
      
      this.ws.onopen = () => {
        console.log('Connected to VersaAI');
        resolve();
      };
      
      this.ws.onerror = (error) => {
        console.error('VersaAI connection error:', error);
        reject(error);
      };
      
      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const handler = this.messageHandlers.get(data.id);
        if (handler) {
          handler(data);
          this.messageHandlers.delete(data.id);
        }
      };
    });
  }

  async getCompletion(context: CompletionContext): Promise<string[]> {
    const id = crypto.randomUUID();
    
    return new Promise((resolve) => {
      this.messageHandlers.set(id, (data) => {
        resolve(data.completions);
      });
      
      this.ws?.send(JSON.stringify({
        id,
        type: 'completion',
        context
      }));
    });
  }

  async chat(message: string, fileContext?: FileContext): Promise<string> {
    const id = crypto.randomUUID();
    
    return new Promise((resolve) => {
      this.messageHandlers.set(id, (data) => {
        resolve(data.response);
      });
      
      this.ws?.send(JSON.stringify({
        id,
        type: 'chat',
        session_id: 'editor-session',
        message,
        file_context: fileContext
      }));
    });
  }
}
```

#### Step 2.3: Monaco Completion Provider
```typescript
// code_editor/src/renderer/versaai/CompletionProvider.ts
import * as monaco from 'monaco-editor';
import { VersaAIClient } from './VersaAIClient';

export class VersaAICompletionProvider implements monaco.languages.CompletionItemProvider {
  constructor(private client: VersaAIClient) {}

  async provideCompletionItems(
    model: monaco.editor.ITextModel,
    position: monaco.Position,
    context: monaco.languages.CompletionContext
  ): Promise<monaco.languages.CompletionList> {
    
    const prefix = model.getValueInRange({
      startLineNumber: 1,
      startColumn: 1,
      endLineNumber: position.lineNumber,
      endColumn: position.column
    });
    
    const suffix = model.getValueInRange({
      startLineNumber: position.lineNumber,
      startColumn: position.column,
      endLineNumber: model.getLineCount(),
      endColumn: model.getLineMaxColumn(model.getLineCount())
    });

    const completions = await this.client.getCompletion({
      file_path: model.uri.fsPath,
      language: model.getLanguageId(),
      prefix,
      suffix,
      line: position.lineNumber,
      column: position.column
    });

    return {
      suggestions: completions.map((completion, index) => ({
        label: completion,
        kind: monaco.languages.CompletionItemKind.Text,
        insertText: completion,
        range: {
          startLineNumber: position.lineNumber,
          startColumn: position.column,
          endLineNumber: position.lineNumber,
          endColumn: position.column
        },
        sortText: `${index}`.padStart(5, '0')
      }))
    };
  }
}
```

#### Step 2.4: Chat Panel Component
```typescript
// code_editor/src/renderer/versaai/ChatPanel.tsx
import React, { useState, useEffect, useRef } from 'react';
import { VersaAIClient } from './VersaAIClient';
import './ChatPanel.css';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export const ChatPanel: React.FC<{
  client: VersaAIClient;
  currentFile?: string;
}> = ({ client, currentFile }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await client.chat(input, {
        path: currentFile || '',
        language: currentFile?.split('.').pop() || 'text'
      });

      const assistantMessage: Message = {
        role: 'assistant',
        content: response,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      // Show error message
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="versaai-chat-panel">
      <div className="chat-header">
        <h3>🤖 VersaAI Assistant</h3>
        {currentFile && <span className="current-file">{currentFile}</span>}
      </div>
      
      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message message-${msg.role}`}>
            <div className="message-content">{msg.content}</div>
            <div className="message-time">
              {msg.timestamp.toLocaleTimeString()}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Ask VersaAI anything about your code..."
          disabled={loading}
        />
        <button onClick={sendMessage} disabled={loading}>
          {loading ? '⏳' : '📤'}
        </button>
      </div>
    </div>
  );
};
```

#### Step 2.5: Integrate into Main App
```typescript
// code_editor/src/renderer/App.tsx (additions)
import { VersaAIClient } from './versaai/VersaAIClient';
import { VersaAICompletionProvider } from './versaai/CompletionProvider';
import { ChatPanel } from './versaai/ChatPanel';

function App() {
  const [versaAI, setVersaAI] = useState<VersaAIClient | null>(null);
  const [showAIPanel, setShowAIPanel] = useState(false);

  useEffect(() => {
    // Initialize VersaAI
    const client = new VersaAIClient();
    client.connect().then(() => {
      setVersaAI(client);
      
      // Register completion provider
      monaco.languages.registerCompletionItemProvider('*', 
        new VersaAICompletionProvider(client)
      );
    }).catch(err => {
      console.error('Failed to connect to VersaAI:', err);
    });
  }, []);

  return (
    <div className="app">
      <Toolbar>
        <button onClick={() => setShowAIPanel(!showAIPanel)}>
          🤖 AI Assistant
        </button>
      </Toolbar>
      
      <div className="main-content">
        <Sidebar />
        <EditorArea />
        
        {showAIPanel && versaAI && (
          <ChatPanel 
            client={versaAI} 
            currentFile={currentFile}
          />
        )}
      </div>
    </div>
  );
}
```

### Phase 3: Advanced Features (Week 3-4)

#### 3.1 Multi-Model Selection UI
```typescript
// Allow users to choose between models
const [selectedModel, setSelectedModel] = useState('auto');

<select onChange={(e) => setSelectedModel(e.target.value)}>
  <option value="auto">Auto (Best Model)</option>
  <option value="deepseek-1.3b">DeepSeek Coder 1.3B (Fast)</option>
  <option value="deepseek-6.7b">DeepSeek Coder 6.7B (Balanced)</option>
  <option value="starcoder2-7b">StarCoder2 7B (Quality)</option>
  <option value="codellama-34b">CodeLlama 34B (Best)</option>
  <option value="gpt-4">GPT-4 (API)</option>
</select>
```

#### 3.2 Code Actions
```typescript
// Right-click menu integration
monaco.editor.addAction({
  id: 'versaai-explain',
  label: 'VersaAI: Explain Code',
  contextMenuGroupId: 'versaai',
  run: async (editor) => {
    const selection = editor.getSelection();
    const text = editor.getModel()?.getValueInRange(selection);
    
    if (text) {
      const explanation = await versaAI.chat(
        `Explain this code:\n\n${text}`
      );
      // Show explanation in panel
    }
  }
});
```

#### 3.3 Project Indexing
```typescript
// Index project on open
async function indexProject(projectPath: string) {
  await versaAI.send({
    type: 'index_project',
    project_path: projectPath
  });
  
  // Show indexing progress
  showNotification('Indexing project for AI assistance...');
}
```

## Installation & Setup

### 1. Install VersaAI in Code Editor

```bash
cd /path/to/code_editor
npm install --save ws  # WebSocket client

# Link VersaAI (development)
cd ../VersaAI
pip install -e .
```

### 2. Start VersaAI Bridge Server

```bash
# Terminal 1: Start VersaAI backend
cd VersaAI
python -m versaai.code_editor_bridge.server
```

### 3. Start Code Editor

```bash
# Terminal 2: Start editor
cd code_editor
npm run dev
```

## Benefits

✅ **Intelligent Code Completion** - Context-aware suggestions using state-of-the-art models
✅ **Multi-Model Support** - Automatically use best model for each task
✅ **Privacy-Focused** - Local models keep code private
✅ **Cost-Effective** - Free local models, paid API as fallback
✅ **Project-Aware** - RAG system understands your codebase
✅ **NLPL Native** - Special support for NLPL language
✅ **Fast & Responsive** - Optimized for low-latency completion

## Next Steps

1. ✅ Implement backend bridge service
2. ✅ Create WebSocket communication layer
3. ✅ Integrate Monaco completion provider
4. ✅ Build chat panel UI
5. ⏳ Add code actions (explain, refactor, test)
6. ⏳ Implement project indexing
7. ⏳ Add model selection UI
8. ⏳ Performance optimization & caching

---

**Status:** Ready for Implementation
**Priority:** High (Core Feature)
**Timeline:** 2-3 weeks for full integration
