// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
use std::process::Command;

pub fn run() {
    tauri::Builder::default()
        .setup(|_app| {
            Command::new("uvicorn")
                .args(&["main:app", "--host", "0.0.0.0", "--port", "8000"])
                .current_dir("../../../backend/app")
                .spawn()
                .expect("Failed to spawn sidecar");
            Ok(())
        })
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![greet])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
