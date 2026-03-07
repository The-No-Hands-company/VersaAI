# VersaAI Flutter UI

A professional, cross-platform user interface for VersaAI - built with Flutter.

## 🎯 Features

- **💬 AI Chat Interface** - Real-time conversations with VersaAI
- **🔍 Code Analysis** - AI-powered code explanation, refactoring, debugging, and test generation
- **🌓 Theme Support** - Beautiful light and dark themes
- **🔌 Live Backend Integration** - WebSocket connection to VersaAI backend
- **📱 Cross-Platform** - Runs on Linux, Windows, macOS, Android, iOS, and Web

## 🚀 Quick Start

### Option 1: One-Command Launch (Recommended)

**Linux/Mac:**
```bash
cd /path/to/VersaAI/ui
chmod +x scripts/run_with_backend.sh
./scripts/run_with_backend.sh
```

**Windows:**
```cmd
cd C:\path\to\VersaAI\ui
scripts\run_with_backend.bat
```

This automatically starts both the backend and UI!

### Option 2: Manual Launch

**Terminal 1 - Start Backend:**
```bash
cd /path/to/VersaAI
python start_editor_bridge.py
```

**Terminal 2 - Start Flutter UI:**
```bash
cd /path/to/VersaAI/ui
flutter pub get
flutter run -d linux  # or windows, macos, android, etc.
```

## 📦 Installation

### Prerequisites

- **Flutter SDK** >= 3.2.0 ([Install Flutter](https://flutter.dev/docs/get-started/install))
- **Python 3.8+** (for backend)
- **VersaAI Backend** (see main README)

### Setup

1. **Install Flutter dependencies:**
```bash
cd ui
flutter pub get
```

2. **Verify Flutter installation:**
```bash
flutter doctor
```

3. **Install Python backend dependencies:**
```bash
cd ..
pip install websockets langchain chromadb
```

## 🎨 Usage

### Features Overview

#### 1. AI Chat
- Real-time conversations with VersaAI
- Context-aware responses
- Message history
- Markdown support

#### 2. Code Analysis
- **Explain Code** - Get detailed code explanations
- **Refactor** - AI-powered code improvements
- **Debug** - Debugging assistance
- **Generate Tests** - Automatic unit test generation
- Supports: Python, JavaScript, TypeScript, Java, C++, Dart, Rust, Go

#### 3. Settings
- Theme switcher (Light/Dark)
- Connection status
- Backend configuration

### Connection Modes

The UI automatically detects the backend connection:

- **🟢 Connected (Live Mode)** - Full AI capabilities with real backend
- **🟠 Mock Mode** - Fallback mode with simulated responses
- **🔴 Offline** - No connection, click retry to reconnect

## 🏗️ Architecture

```
ui/
├── lib/
│   ├── api/
│   │   ├── versa_ai_api.dart          ← High-level API client
│   │   └── versa_ai_websocket.dart    ← WebSocket communication
│   ├── models/
│   │   └── chat_message.dart          ← Data models
│   ├── presentation/
│   │   ├── screens/
│   │   │   ├── chat/                  ← Chat interface
│   │   │   ├── code_analysis/         ← Code analysis tools
│   │   │   └── settings/              ← Settings screen
│   │   ├── theme/                     ← App theming
│   │   └── widgets/                   ← Reusable UI components
│   └── main.dart                      ← App entry point
└── pubspec.yaml                       ← Dependencies
```

## 🔧 Development

### Adding New Features

1. **Create Screen:**
```dart
// lib/presentation/screens/my_feature/my_feature_screen.dart
import 'package:flutter/material.dart';

class MyFeatureScreen extends StatefulWidget {
  const MyFeatureScreen({super.key});
  
  @override
  State<MyFeatureScreen> createState() => _MyFeatureScreenState();
}

class _MyFeatureScreenState extends State<MyFeatureScreen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My Feature')),
      body: const Center(child: Text('Coming soon!')),
    );
  }
}
```

2. **Add to Navigation:**
```dart
// lib/main.dart
static const List<Widget> _widgetOptions = <Widget>[
  ChatScreen(),
  CodeAnalysisScreen(),
  MyFeatureScreen(),  // ← Add here
  SettingsScreen(),
];
```

### Running Tests

```bash
# Unit tests
flutter test

# Integration tests
flutter test integration_test/

# Code coverage
flutter test --coverage
```

### Building for Production

**Linux:**
```bash
flutter build linux --release
```

**Windows:**
```bash
flutter build windows --release
```

**macOS:**
```bash
flutter build macos --release
```

**Android:**
```bash
flutter build apk --release
# or
flutter build appbundle --release
```

**iOS:**
```bash
flutter build ios --release
```

**Web:**
```bash
flutter build web --release
```

## 🐛 Troubleshooting

### Backend won't connect

1. **Check backend is running:**
```bash
curl http://localhost:8765
# or
python -c "import websocket; ws = websocket.WebSocket(); ws.connect('ws://localhost:8765'); print('Connected!'); ws.close()"
```

2. **Check firewall settings** - Allow port 8765

3. **Try different URL:**
```dart
// In versa_ai_websocket.dart
static const String defaultUrl = 'ws://127.0.0.1:8765';
```

### Flutter build fails

1. **Clean and rebuild:**
```bash
flutter clean
flutter pub get
flutter run
```

2. **Update Flutter:**
```bash
flutter upgrade
```

3. **Check platform-specific setup:**
```bash
flutter doctor -v
```

### WebSocket errors

- Make sure backend is running first
- Check console logs for detailed error messages
- Verify Python dependencies are installed: `pip install websockets`

## 📚 API Documentation

### VersaAIApi Class

```dart
final api = VersaAIApi();

// Initialize connection
await api.initialize();

// Send chat message
String response = await api.getResponse('Hello, VersaAI!');

// Explain code
String explanation = await api.explainCode(
  'def fibonacci(n): ...',
  language: 'python',
);

// Refactor code
Map<String, dynamic> refactored = await api.refactorCode(
  'for (var i = 0; i < 10; i++) { ... }',
  language: 'javascript',
);

// Debug code
String debugSuggestions = await api.debugCode(
  'problematic code here',
  errorMessage: 'NullPointerException',
  language: 'java',
);

// Generate tests
String tests = await api.generateTests(
  'function add(a, b) { return a + b; }',
  language: 'javascript',
);

// Health check
bool isHealthy = await api.healthCheck();
```

## 🎯 Roadmap

- [ ] Voice input/output
- [ ] Code highlighting in chat
- [ ] Multi-language support (i18n)
- [ ] Conversation export (PDF, Markdown)
- [ ] File upload for context
- [ ] Real-time code completion widget
- [ ] Mobile-optimized layouts
- [ ] Offline mode with local caching

## 📄 License

See main VersaAI LICENSE file.

## 🤝 Contributing

See main VersaAI CONTRIBUTING.md file.

## 📞 Support

- Documentation: `/docs/FLUTTER_UI_INTEGRATION.md`
- Issues: Report in main VersaAI repository
- Backend Setup: See main VersaAI README.md

---

**Built with ❤️ using Flutter**

