; Mark Imti NSIS Installer Hooks
; Runs after installation to set up the app

!macro preInit
  ; Set default installation directory
  StrCpy $INSTDIR "$LOCALAPPDATA\Mark Imti"
!macroend

!macro customInit
  ; Check if Mark Imti is already running
  nsExec::ExecToLog 'tasklist /FI "IMAGENAME eq mark-jenny-server.exe" /NH'
  Pop $0
  ${If} $0 == "0"
    MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION "Mark Imti is currently running.$\n$\nDo you want to close it and continue installation?" IDOK closeApp
    Abort
    closeApp:
      nsExec::ExecToLog 'taskkill /F /IM mark-jenny-server.exe'
      nsExec::ExecToLog 'taskkill /F /IM mark-jenny.exe'
      Sleep 1000
  ${EndIf}
!macroend

!macro customInstallMode
  ; Check for admin rights for per-machine install
  ${IfThen} $ISADMINSESSION == 1 ${|} StrCpy $perMachineInstallation "true" ${|}
!macroend

!macro customPostInstall
  ; Create data directory
  CreateDirectory "$LOCALAPPDATA\Mark Imti\data"
  CreateDirectory "$LOCALAPPDATA\Mark Imti\extensions"
  CreateDirectory "$LOCALAPPDATA\Mark Imti\models"
  
  ; Create uninstaller info
  WriteRegStr HKCU "Software\Mark Imti" "InstallPath" "$INSTDIR"
  WriteRegStr HKCU "Software\Mark Imti" "Version" "${VERSION}"
  
  ; Offer to launch
  MessageBox MB_YESNO|MB_ICONQUESTION "Installation complete!$\n$\nDo you want to launch Mark Imti now?" IDYES launchApp
  Goto done
  launchApp:
    Exec '"$INSTDIR\mark-jenny.exe"'
  done:
!macroend

!macro customUnInstall
  ; Stop running instances
  nsExec::ExecToLog 'taskkill /F /IM mark-jenny-server.exe'
  nsExec::ExecToLog 'taskkill /F /IM mark-jenny.exe'
  
  ; Ask to keep data
  MessageBox MB_YESNO|MB_ICONQUESTION "Do you want to keep your data (chats, settings, extensions)?" IDYES keepData
  RMDir /r "$LOCALAPPDATA\Mark Imti"
  Goto removeKeys
  keepData:
  removeKeys:
    DeleteRegKey HKCU "Software\Mark Imti"
!macroend
