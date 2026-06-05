# Host Control Server

Use this server when running OmniTool directly on the current desktop session (no OmniBox).

## Start

```powershell
cd OmniParser/omnitool/hostcontrol
python main.py --host 127.0.0.1 --port 5000 --allow_unsafe_execute
```

## Verify

```powershell
curl http://127.0.0.1:5000/probe
```

## Security

`--allow_unsafe_execute` enables arbitrary command execution for mouse/keyboard control.
Keep this bound to localhost and do not expose port 5000 publicly.
