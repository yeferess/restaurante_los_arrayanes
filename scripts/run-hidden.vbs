' Ejecuta un .bat de esta carpeta sin ventana visible y espera a que termine,
' para que la tarea programada siga en estado Running mientras el servicio vive.
' La salida se guarda en scripts\logs\<nombre>.log (se sobrescribe en cada arranque).
' Uso: wscript.exe run-hidden.vbs start-backend.bat
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
batName = WScript.Arguments(0)
batPath = fso.BuildPath(scriptDir, batName)

logDir = fso.BuildPath(scriptDir, "logs")
If Not fso.FolderExists(logDir) Then fso.CreateFolder(logDir)
logPath = fso.BuildPath(logDir, fso.GetBaseName(batName) & ".log")

WScript.Quit shell.Run("cmd /c """"" & batPath & """ > """ & logPath & """ 2>&1""", 0, True)
