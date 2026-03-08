mod commands;

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            commands::chat_send,
            commands::agent_list,
            commands::agent_execute,
            commands::rag_ingest,
            commands::rag_query,
            commands::health_check,
        ])
        .run(tauri::generate_context!())
        .expect("error running VersaAI desktop app");
}
