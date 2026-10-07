"""Opt-in real SDL integration check: py tests/verify_sdl.py."""
import ctypes
import hashlib
import importlib.util
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("viewer", ROOT / "character_runs_esc.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
b = v.backend
OUTPUT = ROOT / ".venv" / "previews"
OUTPUT.mkdir(parents=True, exist_ok=True)


def capture(path=None):
    width, height = v.CANVAS_WIDTH, v.CANVAS_HEIGHT
    pixels = (ctypes.c_ubyte * (width * height * 4))()
    result = b.SDL_RenderReadPixels(b.renderer, None, b.SDL_PIXELFORMAT_RGBA32,
                                    pixels, width * 4)
    if result != 0:
        raise RuntimeError("SDL_RenderReadPixels failed")
    raw = bytes(pixels)
    if path:
        def chunk(tag, data):
            return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
        rows = b"".join(b"\0" + raw[y*width*4:(y+1)*width*4] for y in range(height))
        png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")
        path.write_bytes(png)
    return hashlib.sha256(raw).hexdigest()


def push_key(event_type, key):
    event = b.SDL_Event()
    event.type = event_type
    event.key.type = event_type
    event.key.keysym.sym = key
    event.key.repeat = 0
    assert b.SDL_PushEvent(ctypes.byref(event)) == 1


opened = False
try:
    v.p.open_canvas(v.CANVAS_WIDTH, v.CANVAS_HEIGHT)
    opened = True
    assert b.window and b.renderer
    ground = v.load_asset("TUK_GROUND.png")
    character = v.load_asset("animation_sheet.png")
    cursor = v.load_asset("hand_arrow.png")
    v.p.hide_cursor()
    assert b.SDL_ShowCursor(-1) == b.SDL_DISABLE
    state = v.ViewerState()
    v.p.get_events()
    push_key(b.SDL_KEYDOWN, b.SDLK_LEFT)
    v.handle_events(state, v.p.get_events())
    v.update_movement(state, 0.05)
    assert state.x == 630 and state.animation_name == "RUN_LEFT"
    push_key(b.SDL_KEYUP, b.SDLK_LEFT)
    v.handle_events(state, v.p.get_events())
    v.update_movement(state, 0.05)
    assert state.animation_name == "IDLE_LEFT"
    hashes = {}
    real_present = v.p.update_canvas
    for name in v.ANIMATIONS:
        state.animation_name = name
        state.x, state.y = 640, 512
        state.cursor_visible = True
        state.cursor_x, state.cursor_y = 1000, 500
        row_hashes = set()
        for frame in range(8):
            state.frame_index = frame
            path = OUTPUT / (name + ".png") if frame == 3 else None
            def present(path=path):
                row_hashes.add(capture(path))
                real_present()
            v.p.update_canvas = present
            v.render(state, ground, character, cursor)
        assert len(row_hashes) > 1, name
        hashes[name] = len(row_hashes)
    v.p.update_canvas = real_present
    # SDL window state query is real; hide guarantees both focus flags are absent.
    state.pressed_keys = {b.SDLK_RIGHT}
    b.SDL_HideWindow(b.window)
    v.p.get_events()
    v.sync_window_state(state)
    assert not state.pressed_keys and not state.cursor_visible
    b.SDL_ShowWindow(b.window)
    v.p.get_events()
    v.sync_window_state(state)
    flags = b.SDL_GetWindowFlags(b.window)
    assert state.cursor_visible == bool(flags & b.SDL_WINDOW_SHOWN and not flags & b.SDL_WINDOW_MINIMIZED and flags & b.SDL_WINDOW_MOUSE_FOCUS)
    for key in [None, b.SDLK_ESCAPE]:
        state = v.ViewerState()
        if key is None:
            event = b.SDL_Event()
            event.type = b.SDL_QUIT
            assert b.SDL_PushEvent(ctypes.byref(event)) == 1
        else:
            push_key(b.SDL_KEYDOWN, key)
        v.handle_events(state, v.p.get_events())
        assert not state.running
    print("Real SDL: 32 frames rendered; distinct frame counts:", hashes)
    print("Real SDL: key down/up, window focus loss, cursor visibility, quit and ESC passed")
    print("Preview PNGs:", OUTPUT)
finally:
    if opened:
        v.p.show_cursor()
        assert b.SDL_ShowCursor(-1) == b.SDL_ENABLE
        v.p.close_canvas()

# Exercise the complete main loop from a different working directory.
import contextlib
import io
import os
import tempfile
from unittest.mock import patch

real_poll = v.p.get_events
real_render = v.render
count = 0
seen = set()
positions = []
def events_for_main():
    global count
    count += 1
    schedule = {
        10: (b.SDL_KEYDOWN, b.SDLK_RIGHT),
        40: (b.SDL_KEYUP, b.SDLK_RIGHT),
        50: (b.SDL_KEYDOWN, b.SDLK_LEFT),
        80: (b.SDL_KEYUP, b.SDLK_LEFT),
        100: (b.SDL_KEYDOWN, b.SDLK_ESCAPE),
    }
    if count in schedule:
        push_key(*schedule[count])
    return real_poll()

def observe_render(state, *assets):
    seen.add(state.animation_name)
    positions.append((state.x, state.y))
    real_render(state, *assets)

old_cwd = Path.cwd()
try:
    with tempfile.TemporaryDirectory(dir=ROOT / ".venv") as directory:
        os.chdir(directory)
        with patch.object(v.p, "get_events", side_effect=events_for_main), patch.object(v, "render", side_effect=observe_render):
            assert v.main() == 0
        assert count == 100 and len(positions) == 99
        assert seen == set(v.ANIMATIONS), seen
        assert len(set(positions)) > 1
        error = io.StringIO()
        with patch.object(v, "ASSET_DIR", Path(directory)), contextlib.redirect_stderr(error):
            assert v.main() == 1
        assert "TUK_GROUND.png" in error.getvalue()
        assert b.SDL_ShowCursor(-1) == b.SDL_ENABLE
        print("Full main loop: 99 renders, four states, external cwd, ESC cleanup, real missing-asset cleanup passed")
        os.chdir(old_cwd)
finally:
    os.chdir(old_cwd)
