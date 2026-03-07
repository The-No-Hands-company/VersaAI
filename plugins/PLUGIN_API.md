# VersaAI Plugin API & Integration Strategy

## API Overview
VersaAI exposes a REST API for plugin integration. Plugins for Blender, Unity, Unreal, etc. can communicate with VersaAI via HTTP requests.

### Example REST Endpoints
- `POST /versaai/prompt` — Send a prompt and get a response.
- `POST /versaai/agent` — Invoke an agent for a specific task.
- `GET /versaai/models` — List available models.
- `POST /versaai/model/select` — Switch model for a session/app.

## Integration Strategy
- **Blender**: Use Python (`requests` library) to call the REST API from an addon.
- **Unity**: Use C# (`UnityWebRequest`) to call the REST API from an editor extension.
- **Unreal Engine**: Use C++ (`HTTP module`) or Blueprints to call the REST API from a plugin.
- **Other Tools**: Any language that supports HTTP can integrate with VersaAI.

## Example Request (Python)
```python
import requests
r = requests.post("http://localhost:5000/versaai/prompt", json={"prompt": "generate cube"})
print(r.json()["response"])
```

## Example Request (C# for Unity)
```csharp
using UnityEngine.Networking;
UnityWebRequest www = UnityWebRequest.Post("http://localhost:5000/versaai/prompt", "prompt=generate cube");
www.SendWebRequest();
```

## Example Request (C++ for Unreal)
```cpp
// Use Unreal's HTTP module to POST to VersaAI
```

## Best Practices
- Keep plugin UI simple and focused on user prompts/tasks.
- Handle errors and connection issues gracefully.
- Document supported commands and agent capabilities for each tool.
