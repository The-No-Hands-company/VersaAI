# Flutter UI Integration with VersaAI

## 🎯 Overview

Complete guide to integrating the Flutter UI (`ui/`) with VersaAI's backend services.

## 📁 Current Architecture

```
VersaAI/
├── ui/                          ← Flutter Frontend (Cross-platform)
│   ├── lib/
│   │   ├── api/
│   │   │   └── versa_ai_api.dart    ← Backend API client (TO UPDATE)
│   │   ├── models/
│   │   │   └── chat_message.dart
│   │   ├── presentation/
│   │   │   ├── screens/
│   │   │   │   ├── chat/
│   │   │   │   └── settings/
│   │   │   ├── theme/
│   │   │   └── widgets/
│   │   └── utils/
│   │       └── ai_service.dart
│   └── pubspec.yaml
│
└── versaai/                     ← Python Backend
    ├── code_editor_bridge/
    │   ├── server.py            ← WebSocket Server (ws://localhost:8765)
    │   ├── chat_service.py
    │   └── completion_service.py
    ├── model_router.py
    ├── rag/
    └── memory/
```

## 🚀 Integration Steps

### Phase 1: WebSocket Connection (30 min)

#### 1.1 Add WebSocket Dependency
**File:** `ui/pubspec.yaml`

```yaml
dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.2
  provider: ^6.0.5
  intl: ^0.19.0
  web_socket_channel: ^2.4.0  # ← ADD THIS
  http: ^1.1.0                # ← ADD THIS
```

#### 1.2 Create WebSocket API Client
**File:** `ui/lib/api/versa_ai_websocket.dart` (NEW)

```dart
import 'dart:async';
import 'dart:convert';
import 'dart:developer' as developer;
import 'package:web_socket_channel/web_socket_channel.dart';

class VersaAIWebSocket {
  static const String defaultUrl = 'ws://localhost:8765';
  
  WebSocketChannel? _channel;
  final Map<String, Completer<Map<String, dynamic>>> _pendingRequests = {};
  int _messageIdCounter = 0;
  
  final StreamController<Map<String, dynamic>> _messageController = 
      StreamController.broadcast();
  
  Stream<Map<String, dynamic>> get messages => _messageController.stream;
  
  bool get isConnected => _channel != null;
  
  Future<void> connect([String url = defaultUrl]) async {
    try {
      developer.log('🔌 Connecting to VersaAI backend: $url');
      
      _channel = WebSocketChannel.connect(Uri.parse(url));
      
      // Listen to incoming messages
      _channel!.stream.listen(
        _handleMessage,
        onError: _handleError,
        onDone: _handleDisconnect,
      );
      
      developer.log('✅ Connected to VersaAI backend');
    } catch (e) {
      developer.log('❌ Connection failed: $e', error: e);
      rethrow;
    }
  }
  
  void _handleMessage(dynamic rawMessage) {
    try {
      final data = jsonDecode(rawMessage as String);
      developer.log('📨 Received: ${data['type']}');
      
      final messageId = data['id'] as String?;
      
      // Resolve pending request
      if (messageId != null && _pendingRequests.containsKey(messageId)) {
        _pendingRequests[messageId]!.complete(data);
        _pendingRequests.remove(messageId);
      }
      
      // Broadcast to listeners
      _messageController.add(data);
    } catch (e) {
      developer.log('❌ Error parsing message: $e', error: e);
    }
  }
  
  void _handleError(error) {
    developer.log('❌ WebSocket error: $error', error: error);
    disconnect();
  }
  
  void _handleDisconnect() {
    developer.log('🔌 Disconnected from VersaAI backend');
    _channel = null;
  }
  
  Future<Map<String, dynamic>> sendRequest(
    String type,
    Map<String, dynamic> payload,
  ) async {
    if (!isConnected) {
      throw Exception('Not connected to VersaAI backend');
    }
    
    final messageId = 'msg_${_messageIdCounter++}';
    final completer = Completer<Map<String, dynamic>>();
    _pendingRequests[messageId] = completer;
    
    final message = {
      'id': messageId,
      'type': type,
      ...payload,
    };
    
    developer.log('📤 Sending: $type');
    _channel!.sink.add(jsonEncode(message));
    
    // Timeout after 30 seconds
    return completer.future.timeout(
      const Duration(seconds: 30),
      onTimeout: () {
        _pendingRequests.remove(messageId);
        throw TimeoutException('Request timed out');
      },
    );
  }
  
  Future<String> chat(String message, {
    String sessionId = 'default',
    Map<String, dynamic>? fileContext,
    String taskType = 'general',
  }) async {
    final response = await sendRequest('chat', {
      'session_id': sessionId,
      'message': message,
      'file_context': fileContext,
      'task_type': taskType,
    });
    
    if (response['status'] == 'error') {
      throw Exception(response['message']);
    }
    
    return response['response'] as String;
  }
  
  Future<String> explainCode(
    String code, {
    String language = 'text',
    String? filePath,
  }) async {
    final response = await sendRequest('explain', {
      'code': code,
      'language': language,
      'file_path': filePath,
    });
    
    if (response['status'] == 'error') {
      throw Exception(response['message']);
    }
    
    return response['explanation'] as String;
  }
  
  Future<Map<String, dynamic>> getCompletion(
    Map<String, dynamic> context,
  ) async {
    final response = await sendRequest('completion', {
      'context': context,
    });
    
    if (response['status'] == 'error') {
      throw Exception(response['message']);
    }
    
    return response;
  }
  
  Future<bool> ping() async {
    try {
      final response = await sendRequest('ping', {});
      return response['status'] == 'ok';
    } catch (e) {
      return false;
    }
  }
  
  void disconnect() {
    _channel?.sink.close();
    _channel = null;
    _pendingRequests.clear();
  }
  
  void dispose() {
    disconnect();
    _messageController.close();
  }
}
```

#### 1.3 Update API Layer
**File:** `ui/lib/api/versa_ai_api.dart`

```dart
import 'dart:developer' as developer;
import 'versa_ai_websocket.dart';

class VersaAIApi {
  final VersaAIWebSocket _websocket = VersaAIWebSocket();
  bool _isInitialized = false;
  
  Future<void> initialize() async {
    if (_isInitialized) return;
    
    try {
      await _websocket.connect();
      _isInitialized = true;
      
      developer.log('✅ VersaAI API initialized', name: 'VersaAI');
    } catch (e) {
      developer.log(
        '⚠️  Failed to connect to VersaAI backend. Using mock mode.',
        name: 'VersaAI',
      );
      developer.log('Error: $e', name: 'VersaAI');
    }
  }
  
  Future<String> getResponse(String message) async {
    if (!_isInitialized) {
      await initialize();
    }
    
    // Try WebSocket connection
    if (_websocket.isConnected) {
      try {
        return await _websocket.chat(message);
      } catch (e) {
        developer.log('❌ Chat failed: $e', name: 'VersaAI');
        // Fall back to mock
      }
    }
    
    // Fallback to mock response
    developer.log('⚠️  Using MOCK implementation', name: 'VersaAI');
    await Future.delayed(const Duration(seconds: 1));
    return 'This is a mocked response from VersaAI for your message: "$message"';
  }
  
  Future<String> explainCode(String code, {String language = 'text'}) async {
    if (!_isInitialized) await initialize();
    
    if (_websocket.isConnected) {
      try {
        return await _websocket.explainCode(code, language: language);
      } catch (e) {
        developer.log('❌ Explain code failed: $e', name: 'VersaAI');
      }
    }
    
    return 'Mock explanation: This code performs... [mock mode]';
  }
  
  Future<bool> healthCheck() async {
    if (!_isInitialized) await initialize();
    return _websocket.isConnected && await _websocket.ping();
  }
  
  void dispose() {
    _websocket.dispose();
  }
}
```

### Phase 2: Enhanced UI Features (1 hour)

#### 2.1 Add Connection Status Indicator
**File:** `ui/lib/presentation/widgets/connection_status.dart` (NEW)

```dart
import 'package:flutter/material.dart';

class ConnectionStatus extends StatelessWidget {
  final bool isConnected;
  final VoidCallback? onRetry;
  
  const ConnectionStatus({
    super.key,
    required this.isConnected,
    this.onRetry,
  });
  
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: isConnected ? Colors.green.shade700 : Colors.red.shade700,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isConnected ? Icons.cloud_done : Icons.cloud_off,
            size: 16,
            color: Colors.white,
          ),
          const SizedBox(width: 6),
          Text(
            isConnected ? 'Connected' : 'Offline',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
          if (!isConnected && onRetry != null) ...[
            const SizedBox(width: 8),
            GestureDetector(
              onTap: onRetry,
              child: const Icon(
                Icons.refresh,
                size: 16,
                color: Colors.white,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
```

#### 2.2 Add Code Explanation Feature
**File:** `ui/lib/presentation/screens/code_analysis/code_analysis_screen.dart` (NEW)

```dart
import 'package:flutter/material.dart';
import 'package:versa_ai_ui/api/versa_ai_api.dart';

class CodeAnalysisScreen extends StatefulWidget {
  const CodeAnalysisScreen({super.key});
  
  @override
  State<CodeAnalysisScreen> createState() => _CodeAnalysisScreenState();
}

class _CodeAnalysisScreenState extends State<CodeAnalysisScreen> {
  final _codeController = TextEditingController();
  final _api = VersaAIApi();
  String? _explanation;
  bool _isLoading = false;
  
  Future<void> _analyzeCode() async {
    if (_codeController.text.isEmpty) return;
    
    setState(() {
      _isLoading = true;
      _explanation = null;
    });
    
    try {
      final explanation = await _api.explainCode(_codeController.text);
      setState(() {
        _explanation = explanation;
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Code Analysis'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _codeController,
              maxLines: 10,
              decoration: const InputDecoration(
                labelText: 'Paste your code here',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _isLoading ? null : _analyzeCode,
              child: _isLoading
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Analyze Code'),
            ),
            const SizedBox(height: 24),
            if (_explanation != null) ...[
              const Text(
                'Explanation:',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Expanded(
                child: SingleChildScrollView(
                  child: Text(_explanation!),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
  
  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }
}
```

### Phase 3: Testing & Deployment (30 min)

#### 3.1 Create Integration Test
**File:** `ui/test/integration/websocket_test.dart` (NEW)

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:versa_ai_ui/api/versa_ai_websocket.dart';

void main() {
  group('VersaAI WebSocket Integration', () {
    late VersaAIWebSocket ws;
    
    setUp(() {
      ws = VersaAIWebSocket();
    });
    
    tearDown(() {
      ws.dispose();
    });
    
    test('should connect to backend', () async {
      await ws.connect();
      expect(ws.isConnected, true);
    });
    
    test('should ping server', () async {
      await ws.connect();
      final pong = await ws.ping();
      expect(pong, true);
    });
    
    test('should send chat message', () async {
      await ws.connect();
      final response = await ws.chat('Hello, VersaAI!');
      expect(response, isNotEmpty);
    });
  });
}
```

#### 3.2 Create Launch Scripts
**File:** `ui/scripts/run_with_backend.sh` (NEW)

```bash
#!/bin/bash
# Launch VersaAI backend + Flutter UI

set -e

echo "🚀 Starting VersaAI Full Stack"

# Start backend in background
echo "📡 Starting VersaAI backend..."
cd ..
python3 start_editor_bridge.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start Flutter UI
echo "🎨 Starting Flutter UI..."
cd ui
flutter run -d linux

# Cleanup on exit
trap "kill $BACKEND_PID" EXIT
```

**File:** `ui/scripts/run_with_backend.bat` (NEW - Windows)

```bat
@echo off
echo 🚀 Starting VersaAI Full Stack

REM Start backend in background
echo 📡 Starting VersaAI backend...
cd ..
start /B python start_editor_bridge.py

REM Wait for backend
timeout /t 3 /nobreak

REM Start Flutter UI
echo 🎨 Starting Flutter UI...
cd ui
flutter run -d windows

pause
```

## 📋 Complete Setup Checklist

### Backend Setup
- [ ] Install Python dependencies: `pip install websockets`
- [ ] Test backend: `python start_editor_bridge.py`
- [ ] Verify WebSocket: Open `ws://localhost:8765` in browser console

### Flutter UI Setup
- [ ] Add dependencies: `cd ui && flutter pub get`
- [ ] Create new files: `versa_ai_websocket.dart`, `connection_status.dart`
- [ ] Update `versa_ai_api.dart`
- [ ] Test connection: `flutter run`

### Integration Testing
- [ ] Run backend: `python start_editor_bridge.py`
- [ ] Run Flutter: `cd ui && flutter run`
- [ ] Send test message in UI
- [ ] Verify response from backend

## 🎯 Quick Start Commands

```bash
# Terminal 1: Start Backend
cd /path/to/VersaAI
python start_editor_bridge.py

# Terminal 2: Start Flutter UI
cd /path/to/VersaAI/ui
flutter run -d linux  # or -d windows, -d macos

# All-in-one (Linux/Mac)
cd ui && chmod +x scripts/run_with_backend.sh && ./scripts/run_with_backend.sh
```

## 🔧 Troubleshooting

### Backend won't start
```bash
# Install missing dependencies
pip install websockets langchain chromadb faiss-cpu

# Check if port is in use
lsof -i :8765  # Linux/Mac
netstat -ano | findstr :8765  # Windows
```

### Flutter can't connect
1. Verify backend is running: `curl http://localhost:8765`
2. Check firewall settings
3. Try fallback URL: `ws://127.0.0.1:8765`
4. Enable verbose logging in Flutter

### WebSocket disconnects
- Increase timeout in `versa_ai_websocket.dart`
- Add reconnection logic
- Check network stability

## 🚀 Next Steps

1. **Add Advanced Features:**
   - Multi-model selection UI
   - Conversation history persistence
   - Code completion in real-time
   - File upload for context

2. **Mobile Support:**
   - Test on Android/iOS
   - Optimize for mobile UI
   - Add push notifications

3. **Production Deployment:**
   - Add authentication
   - HTTPS/WSS support
   - Docker containerization
   - Cloud deployment (AWS/GCP/Azure)

## 📚 Resources

- [Flutter WebSocket Guide](https://flutter.dev/docs/cookbook/networking/web-sockets)
- [VersaAI Backend API](../versaai/code_editor_bridge/README.md)
- [WebSocket Protocol](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

---

**Status:** Ready for Integration ✅
**Estimated Time:** 2-3 hours
**Difficulty:** Intermediate
