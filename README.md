# BG3_SE_GUI

An external desktop GUI (PyQt6) for triggering Baldur's Gate 3 Script Extender
(BG3SE) actions while you play — similar in spirit to WeMod, but built the way
BG3SE actually works rather than by patching process memory.

## How it works (read this first)

BG3SE isn't a live memory trainer like WeMod — it's a DLL (`bin/DWrite.dll`,
already installed on your system) that loads a sandboxed Lua scripting
environment into the game at launch. There's no built-in "toggle switches"
concept; those only exist if a Lua mod implements them.

So this project has two halves:

1. **`mod/`** — a small BG3SE Lua mod (`BG3GuiBridge`) that runs *inside* the
   game. Every ~0.5s it checks a `command.json` file for a request, runs it,
   and writes the result to `status.json`.
2. **`gui/`** — a PyQt6 app that runs *outside* the game as a normal Linux
   window. Clicking a button writes `command.json`; a status bar shows the
   result.

Both sides read/write the **same folder on disk**. BG3SE's `Ext.IO` API is
sandboxed to its own storage root for security (no arbitrary file access from
Lua mods), but that root is still a plain directory inside your Proton
prefix — Proton doesn't virtualize the filesystem, so the GUI (a native Linux
process) can read and write it directly with zero IPC tricks.

```
 ┌────────────┐   writes command.json    ┌─────────────────────────┐
 │  gui/main.py│ ───────────────────────▶ │ BG3GuiBridge/ (on disk, │
 │  (PyQt6)   │ ◀─────────────────────── │ inside the Proton prefix)│
 └────────────┘   reads status.json/log   └─────────────────────────┘
                                                       ▲  ▼ Ext.IO
                                            ┌─────────────────────────┐
                                            │ BootstrapServer.lua      │
                                            │ (running inside BG3 via  │
                                            │  Script Extender)        │
                                            └─────────────────────────┘
```

## Achievements

Your `bin/ScriptExtenderSettings.json` already has `"EnableAchievements": true`.
That flag exists specifically so that using Script Extender / Lua mods doesn't
lock Steam achievements the way Larian's own "story mode"/mod flag can. Leave
it on. This bridge mod doesn't touch that setting.

## Honesty about the Lua/Osiris calls in `shared/commands.json`

I don't have a live copy of BG3 to test against, so I can't guarantee every
Osiris/Ext function name and signature in the manifest is exactly right for
your game version. Each command is tagged:

- `verified-pattern` — a widely-published BG3SE community recipe (status
  application, direct ECS component writes, `Osiris.TemplateAddTo`). Very
  likely correct, but test once.
- `needs-testing` — plausible but the exact call name/signature is a
  placeholder (e.g. gold's item-template GUID, XP function name, camp supply
  function name). **These will show an error in the status bar until you fix
  them** — that's expected, not a bug in the bridge itself.

To fix a `needs-testing` command:

1. Launch BG3 (console opens automatically — `CreateConsole: true` is already
   set in `bin/ScriptExtenderSettings.json`).
2. Try the Lua directly in the **Console tab of the GUI** (it forwards
   whatever you type straight to the game — this is the fastest feedback
   loop, faster than editing files and repacking).
3. Once it works, copy the working Lua into that command's `"lua"` field in
   `shared/commands.json`.
4. Run `python3 shared/sync_commands.py` to regenerate `Commands.lua`.
5. Repack the mod (see below) and reload.

Good places to look up exact BG3SE API/Osiris signatures: the BG3SE GitHub
wiki/docs and the `#help` channels of the BG3 modding Discord communities —
search for the specific action (e.g. "bg3se add xp lua").

## One-time setup

### 1. Install the mod

The mod source lives at `mod/Mods/BG3GuiBridge_.../`. BG3 mods normally need
to be packed into a single `.pak`. The straightforward way:

1. Install the **BG3 Modder's Multitool** (or LSLib's `Divine.exe`/ConverterApp
   under Wine) — community tools for packing a mod project folder into a
   `.pak`. Point it at `mod/` as the project root; it will produce something
   like `BG3GuiBridge.pak`.
2. Copy that `.pak` into your game's mods folder:
   ```
   /mnt/games/SteamLibrary/steamapps/compatdata/1086940/pfx/drive_c/users/steamuser/AppData/Local/Larian Studios/Baldur's Gate 3/Mods/
   ```
3. Launch BG3, open the in-game **Mods** menu, and enable "BG3 GUI Bridge" —
   let the game write it into `modsettings.lsx` itself rather than hand-editing
   that file.
4. Load into any save. The mod writes a probe file on session load.

If you'd rather iterate on the Lua without repacking every time, look into
BG3SE's documented Lua dev-mode / project-path mapping (check the current
BG3SE wiki — this has changed across versions, so I'm not baking a specific
mechanism into this README that might be stale).

### 2. Point the GUI at the bridge folder

```bash
cd ~/Documents/BG3_SE_GUI/gui
python3 main.py
```

Open the **Settings** tab and click **Auto-detect bridge folder** (it searches
your known Steam compatdata prefixes for `BG3GuiBridge/probe.txt`, which only
exists after step 1.4 above). If it doesn't find anything, use **Browse
manually…** and navigate to wherever BG3SE's `Ext.IO` sandbox root turned out
to be for your install (the probe file's containing folder).

### 3. Use it

- Category tabs (Health / Resources / Utility / Abilities) — one button per
  action from `shared/commands.json`, with inline parameter fields where
  relevant.
- **Console tab** — free-form Lua, sent straight to the game. This is your
  escape hatch for anything not yet wired up as a button.
- Status bar at the bottom shows the result of the last command; the log pane
  below it keeps a running history.

## Extending it ("anything and everything")

Add a new entry to `shared/commands.json` (id, label, category, confidence,
optional `params`, and a `lua` body — it runs as `function(params, ctx) ... end`,
where `ctx.players()` gives you the current player-character GUIDs and
`ctx.log(msg)` writes to the in-game log). Run `sync_commands.py`, repack,
reload. No GUI code changes needed — the buttons are generated from the
manifest.

## Project layout

```
BG3_SE_GUI/
├── README.md
├── shared/
│   ├── commands.json       # canonical command manifest (edit this)
│   └── sync_commands.py    # regenerates mod/.../Commands.lua from commands.json
├── mod/
│   └── Mods/BG3GuiBridge_<uuid>/
│       ├── meta.lsx
│       └── ScriptExtender/
│           ├── Config.json
│           └── Lua/
│               ├── BootstrapServer.lua   # file-bridge poll loop + dispatcher
│               └── Commands.lua          # generated, do not edit by hand
└── gui/
    ├── main.py              # PyQt6 app
    ├── bridge.py            # bridge-folder discovery + command/status I/O
    └── requirements.txt
```
