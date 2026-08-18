# tools/

`pack.sh` (in the project root) expects `divine.exe` here — that's the packer
CLI from **LSLib** (Norbyte/lslib on GitHub), the standard community tool for
building Larian's `.pak` archive format.

Get it yourself (this repo doesn't vendor third-party binaries):

1. Open https://github.com/Norbyte/lslib/releases in a browser and grab the
   latest `ExportTool-vX.Y.Z.zip` (a few tens of MB).
2. Unzip it, and copy `Tools/divine.exe` (path may vary slightly by release)
   into this folder, so you end up with `tools/divine.exe`.

## Runtime setup (one-time)

Divine.dll targets .NET 8. Running it natively via Linux `dotnet` hits a
confirmed upstream bug in Divine's own path validation
(https://github.com/Norbyte/lslib/issues/220) — its `Uri`-based path check
assumes Windows-style paths and crashes on absolute Linux paths. So `pack.sh`
runs `Divine.exe` through Wine instead, using a **dedicated Wine prefix**
(separate from your actual BG3 Proton prefix, so this can't affect your game
install).

One-time setup:

```bash
WINEPREFIX="$HOME/Documents/BG3_SE_GUI/.wineprefix" winetricks -q dotnet8
```

That downloads and installs the real Windows .NET 8 runtime into that
isolated prefix (a few tens of MB from Microsoft, via winetricks' normal
mechanism). After that, `./pack.sh` (in the project root) just works.
