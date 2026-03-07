bl_info = {
    "name": "VersaAI Assistant",
    "author": "VersaAI Team",
    "version": (0, 1),
    "blender": (4, 50, 0),
    "location": "View3D > Sidebar > VersaAI",
    "description": "AI-powered assistant for Blender tasks.",
    "category": "3D View",
}

import bpy
import requests

class VersaAI_OT_Prompt(bpy.types.Operator):
    bl_idname = "versaai.prompt"
    bl_label = "Ask VersaAI"
    bl_description = "Send a prompt to VersaAI and get a response."

    prompt: bpy.props.StringProperty(name="Prompt")
    response: bpy.props.StringProperty(name="Response", default="")
    session_id: bpy.props.StringProperty(name="Session ID", default="default")
    server_url: bpy.props.StringProperty(name="Server URL", default="http://localhost:5000/versaai/prompt")

    def execute(self, context):
        # Send prompt to VersaAI REST API with session/context
        try:
            payload = {"prompt": self.prompt, "session_id": self.session_id}
            r = requests.post(self.server_url, json=payload)
            self.response = r.json().get("response", "No response.")
        except Exception as e:
            self.response = str(e)
        self.report({'INFO'}, self.response)
        return {'FINISHED'}

class VersaAI_PT_Panel(bpy.types.Panel):
    bl_label = "VersaAI Assistant"
    bl_idname = "VIEW3D_PT_versaai"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'VersaAI'

    def draw(self, context):
        layout = self.layout
        op = layout.operator(VersaAI_OT_Prompt.bl_idname)
        layout.prop(op, "prompt")
        layout.prop(op, "session_id")
        layout.prop(op, "server_url")
        layout.label(text="Response:")
        layout.prop(op, "response")
        layout.separator()
        layout.label(text="Example tasks:")
        layout.label(text="- generate cube")
        layout.label(text="- auto-arrange scene")
        layout.label(text="- search asset tree")

classes = [VersaAI_OT_Prompt, VersaAI_PT_Panel]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
