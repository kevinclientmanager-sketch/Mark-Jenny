# Windows Installation

## Requirements
- Windows 10/11 64-bit
- 4GB RAM, 2GB disk

## Install
1. Download `MARK-IMTI_0.1.0_x64.msi` or `NSIS` installer from Releases
2. Run installer → choose Start Menu + Desktop shortcut
3. First launch creates `%APPDATA%/markimti` (projects, files, `mark_imti.db`, `uploads/`, logs)
4. Tray icon appears - right-click: Show, Quit, Startup on boot (toggle)
5. Logs at `%APPDATA%/markimti/logs/app.log`, crash dumps at `crashes/`

## Desktop Capabilities
- Native window (Tauri WebView), not just wrapped page - uses `ComputerController` for FileSystem/Process/Clipboard where permitted
- `Connect My Computer` pairs via tray consent - explicit permission per spec
- Background execution: tasks continue via `BackgroundWorker` even if window closed, recover on restart via `CheckpointManager`
- Offline: SQLite + local files/memory/skills/scheduling work without internet; sync on reconnect (no silent overwrite)

## Uninstall
- Control Panel → Apps → Mark-Imti → Uninstall (removes app, keeps `%APPDATA%/markimti` unless checked)
- Or `Uninstall` shortcut in Start Menu

## Build from source (Windows)
```powershell
cd MARK-IMTI/frontend
npm install
npm run tauri build  # requires Rust + Tauri CLI: cargo install tauri-cli
# Output: src-tauri/target/release/bundle/msi/*.msi and nsis/*.exe
```
