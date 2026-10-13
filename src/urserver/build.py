"""Build keyboard.lua for the Unified Remote on-screen keyboards (atrium, 2026-10-04).

python build.py CORE_INPUT ORIG_KEYBOARD  ->  keyboard.lua (next to this script) =
    keyboard.tmpl.lua
    + the "atrium typing" block from CORE_INPUT (Core/Input/remote.lua with the atrium patch applied)
    + events.preload from ORIG_KEYBOARD (Main/Keyboards/keyboard.lua as shipped in the urserver RPM)
The urserver files are not stored in this repository (no license from the vendor): take them from
/opt/urserver/remotes/Unified on the box. Only needed to change the keyboards - the ready result is
already in patches/urserver/atrium-urserver.patch.
2026-10-13: inputs as arguments (repository atrium); before: files next to the script.
All files are ASCII with LF line ends, as on the box.
"""
import hashlib
import pathlib
import sys

HERE = pathlib.Path(__file__).parent


def read(name):
    return (HERE / name).read_text(encoding="ascii")


core = pathlib.Path(sys.argv[1]).read_text(encoding="ascii")
start = core.index("-- >>> atrium typing")
end = core.index("-- <<< atrium typing")
end = core.index("\n", end) + 1
typing = core[start:end]

orig = pathlib.Path(sys.argv[2]).read_text(encoding="ascii")
preload = orig[orig.index("events.preload = function ()"):].rstrip("\n") + "\n"

out = read("keyboard.tmpl.lua")
assert out.count("@@ATRIUM_TYPING@@\n") == 1 and out.count("@@PRELOAD@@\n") == 1
out = out.replace("@@ATRIUM_TYPING@@\n", typing).replace("@@PRELOAD@@\n", preload)
out.encode("ascii")
(HERE / "keyboard.lua").write_bytes(out.encode("ascii"))
print(hashlib.sha256((HERE / "keyboard.lua").read_bytes()).hexdigest(), "keyboard.lua")
