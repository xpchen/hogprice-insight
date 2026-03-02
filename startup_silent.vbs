Dim ws, proj, cmd
Set ws = CreateObject("WScript.Shell")

' Get project root directory
proj = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\") - 1)

' Start backend silently (WindowStyle=0: hidden, bWaitOnReturn=False: non-blocking)
cmd = "cmd /c cd /d """ & proj & "\backend"" && call env\Scripts\activate && python -m uvicorn main:app --host 0.0.0.0 --port 8000"
ws.Run cmd, 0, False

' Wait for backend to initialize
WScript.Sleep 4000

' Start frontend silently
cmd = "cmd /c cd /d """ & proj & "\frontend"" && npm run dev"
ws.Run cmd, 0, False

' Wait for frontend to initialize
WScript.Sleep 6000

' Open browser
ws.Run "http://localhost:5173"
