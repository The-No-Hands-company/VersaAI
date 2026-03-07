using UnityEditor;
using UnityEngine;
using UnityEngine.Networking;

public class VersaAIEditorWindow : EditorWindow {
    string prompt = "";
    string response = "";

    [MenuItem("Window/VersaAI Assistant")]
    public static void ShowWindow() {
        GetWindow<VersaAIEditorWindow>("VersaAI Assistant");
    }

    void OnGUI() {
        GUILayout.Label("VersaAI Prompt", EditorStyles.boldLabel);
        prompt = EditorGUILayout.TextField("Prompt", prompt);
        if (GUILayout.Button("Send to VersaAI")) {
            SendPrompt();
        }
        GUILayout.Label("Response:", EditorStyles.boldLabel);
        GUILayout.TextArea(response);
    }

    void SendPrompt() {
        UnityWebRequest www = UnityWebRequest.Post("http://localhost:5000/versaai/prompt", "prompt=" + prompt);
        www.SendWebRequest();
        while (!www.isDone) {}
        if (www.result == UnityWebRequest.Result.Success) {
            response = www.downloadHandler.text;
        } else {
            response = "Error: " + www.error;
        }
    }
}
