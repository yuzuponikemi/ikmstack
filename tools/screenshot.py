"""screenshot.py — capture the desktop so an agent can *see* GUI state.

Use when a GUI operation (an installer, a CAD app, any GUI) seems to have
stalled: a blocking modal dialog is invisible to shell tools but obvious in a
screenshot. Capture, then Read the PNG (this agent is a VLM and can read it).

Usage:
  python tools/screenshot.py [out.png]     # default: temp dir

Captures every monitor. macOS uses the built-in `screencapture` (no extra
permissions beyond the one-time Screen Recording grant for the terminal app);
Windows uses System.Windows.Forms via PowerShell; Linux tries `import` (ImageMagick),
then `gnome-screenshot`, then `spectacle`.
"""

import os
import shutil
import subprocess
import sys
import tempfile

PS = r'''
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
$b = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
$bmp.Save("{OUT}", [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Output "saved {OUT} ($($b.Width)x$($b.Height))"
'''


def _capture(out: str) -> subprocess.CompletedProcess | None:
    """Run the platform's screenshot command. None if no backend is available."""
    if sys.platform == "darwin":
        # -x = no shutter sound. Multi-display: screencapture writes one file per
        # display as <stem>.png / <stem> 2.png … so keep the caller's path first.
        return subprocess.run(["screencapture", "-x", out],
                              capture_output=True, text=True)
    if os.name == "nt":
        return subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             PS.replace("{OUT}", out.replace("\\", "\\\\"))],
            capture_output=True, text=True)
    for cmd in (["import", "-window", "root", out],
                ["gnome-screenshot", "-f", out],
                ["spectacle", "-b", "-n", "-o", out]):
        if shutil.which(cmd[0]):
            return subprocess.run(cmd, capture_output=True, text=True)
    return None


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        tempfile.gettempdir(), "agent_screen.png")
    out = os.path.abspath(out)
    r = _capture(out)
    if r is None:
        print(f"no screenshot backend found for platform {sys.platform}",
              file=sys.stderr)
        return 1
    msg = (r.stdout or "").strip() or (r.stderr or "").strip()
    if os.path.exists(out):
        print(msg or f"saved {out}")
        return 0
    print(msg or f"capture failed: {out} was not written", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
