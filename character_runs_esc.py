import ctypes
import sys
from math import hypot
from pathlib import Path
from time import perf_counter

import pico2d as p
from pico2d import pico2d as backend

CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 1024
ASSET_DIR = Path(__file__).resolve().parent
FRAME_WIDTH = 100
FRAME_HEIGHT = 100
FRAME_COUNT = 8
ANIMATION_FPS = 10
MOVE_SPEED = 200.0
CURSOR_WIDTH = 50
CURSOR_HEIGHT = 52
ANIMATIONS = {
    "IDLE_RIGHT": 300,
    "IDLE_LEFT": 200,
    "RUN_RIGHT": 100,
    "RUN_LEFT": 0,
}


def load_asset(filename):
    path = ASSET_DIR / filename
    if not path.is_file():
        raise RuntimeError(f"Missing asset: {path}")
    try:
        return p.load_image(str(path))
    except Exception as exc:
        raise RuntimeError(f"Cannot load asset: {path}") from exc


def advance_animation(frame, elapsed, dt):
    elapsed += dt
    frame_duration = 1.0 / ANIMATION_FPS
    count = int((elapsed + 1e-12) / frame_duration)
    return (frame + count) % FRAME_COUNT, max(0.0, elapsed - count * frame_duration)


class ViewerState:
    def __init__(self):
        self.running = True
        self.pressed_keys = set()
        self.cursor_x = 0
        self.cursor_y = 0
        self.cursor_visible = False
        self.x = CANVAS_WIDTH / 2
        self.y = CANVAS_HEIGHT / 2
        self.frame_index = 0
        self.animation_elapsed = 0.0
        self.animation_name = "IDLE_RIGHT"
        self.facing = "RIGHT"
        self.motion_state = "IDLE"


def handle_events(state, events):
    for event in events:
        if event.type == p.SDL_QUIT or (
                event.type == p.SDL_KEYDOWN and event.key == p.SDLK_ESCAPE):
            state.running = False
            break
        if event.type == p.SDL_KEYDOWN and event.key in (
                p.SDLK_LEFT, p.SDLK_RIGHT, p.SDLK_UP, p.SDLK_DOWN):
            state.pressed_keys.add(event.key)
        elif event.type == p.SDL_KEYUP:
            state.pressed_keys.discard(event.key)
        elif event.type == p.SDL_MOUSEMOTION:
            state.cursor_x = event.x
            state.cursor_y = CANVAS_HEIGHT - 1 - event.y
            state.cursor_visible = True


def sync_window_state(state):
    # pico2d.get_events() drops SDL window events, so query live SDL flags.
    flags = backend.SDL_GetWindowFlags(backend.window)
    if not flags & backend.SDL_WINDOW_INPUT_FOCUS:
        state.pressed_keys.clear()
    if flags & backend.SDL_WINDOW_MOUSE_FOCUS:
        mouse_x, mouse_y = ctypes.c_int(), ctypes.c_int()
        backend.SDL_GetMouseState(ctypes.byref(mouse_x), ctypes.byref(mouse_y))
        state.cursor_x = mouse_x.value
        state.cursor_y = CANVAS_HEIGHT - 1 - mouse_y.value
        state.cursor_visible = True
    else:
        state.cursor_visible = False


def select_animation(state, name):
    if name != state.animation_name:
        state.animation_name = name
        state.frame_index = 0
        state.animation_elapsed = 0.0


def update_movement(state, dt):
    horizontal = int(p.SDLK_RIGHT in state.pressed_keys) - int(
        p.SDLK_LEFT in state.pressed_keys)
    vertical = int(p.SDLK_UP in state.pressed_keys) - int(
        p.SDLK_DOWN in state.pressed_keys)
    if horizontal > 0:
        state.facing = "RIGHT"
    elif horizontal < 0:
        state.facing = "LEFT"
    previous_position = (state.x, state.y)
    length = hypot(horizontal, vertical)
    if length:
        state.x += horizontal / length * MOVE_SPEED * dt
        state.y += vertical / length * MOVE_SPEED * dt
    state.x = min(CANVAS_WIDTH - FRAME_WIDTH / 2,
                  max(FRAME_WIDTH / 2, state.x))
    state.y = min(CANVAS_HEIGHT - FRAME_HEIGHT / 2,
                  max(FRAME_HEIGHT / 2, state.y))
    state.motion_state = "RUN" if (state.x, state.y) != previous_position else "IDLE"
    select_animation(state, state.motion_state + "_" + state.facing)


def render(state, ground, character, cursor):
    p.clear_canvas()
    ground.draw(CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2)
    character.clip_draw(state.frame_index * FRAME_WIDTH,
                        ANIMATIONS[state.animation_name],
                        FRAME_WIDTH, FRAME_HEIGHT, state.x, state.y)
    if state.cursor_visible:
        cursor.draw(state.cursor_x + CURSOR_WIDTH / 2,
                    state.cursor_y - CURSOR_HEIGHT / 2)
    p.update_canvas()


def main():
    canvas_open = False
    try:
        p.open_canvas(CANVAS_WIDTH, CANVAS_HEIGHT)
        canvas_open = True
        if not backend.window or not backend.renderer:
            raise RuntimeError("Cannot create pico2d canvas")
        ground = load_asset("TUK_GROUND.png")
        character = load_asset("animation_sheet.png")
        cursor = load_asset("hand_arrow.png")
        p.hide_cursor()
        state = ViewerState()
        previous_time = perf_counter()
        while state.running:
            handle_events(state, p.get_events())
            if not state.running:
                break
            sync_window_state(state)
            now = perf_counter()
            dt = now - previous_time
            previous_time = now
            update_movement(state, dt)
            state.frame_index, state.animation_elapsed = advance_animation(
                state.frame_index, state.animation_elapsed, dt)
            render(state, ground, character, cursor)
            p.delay(0.05)
        return 0
    except Exception as exc:
        print(f"Viewer error: {exc}", file=sys.stderr)
        return 1
    finally:
        if canvas_open:
            try:
                p.show_cursor()
            finally:
                p.close_canvas()


if __name__ == "__main__":
    raise SystemExit(main())
