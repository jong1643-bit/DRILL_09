from pathlib import Path
from time import perf_counter

import pico2d as p

CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 1024
ASSET_DIR = Path(__file__).resolve().parent
FRAME_WIDTH = 100
FRAME_HEIGHT = 100
FRAME_COUNT = 8
ANIMATION_FPS = 10
MOVE_SPEED = 200.0
ANIMATIONS = {
    "IDLE_RIGHT": 300,
    "IDLE_LEFT": 200,
    "RUN_RIGHT": 100,
    "RUN_LEFT": 0,
}


def load_asset(filename):
    return p.load_image(str(ASSET_DIR / filename))


def advance_animation(frame, elapsed, dt):
    elapsed += dt
    frame_duration = 1.0 / ANIMATION_FPS
    count = int((elapsed + 1e-12) / frame_duration)
    return (frame + count) % FRAME_COUNT, max(0.0, elapsed - count * frame_duration)


class ViewerState:
    def __init__(self):
        self.running = True
        self.pressed_keys = set()
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
    state.x += horizontal * MOVE_SPEED * dt
    state.y += vertical * MOVE_SPEED * dt
    state.motion_state = "RUN" if (state.x, state.y) != previous_position else "IDLE"
    select_animation(state, state.motion_state + "_" + state.facing)


def main():
    p.open_canvas(CANVAS_WIDTH, CANVAS_HEIGHT)
    ground = load_asset("TUK_GROUND.png")
    character = load_asset("animation_sheet.png")
    state = ViewerState()
    previous_time = perf_counter()
    while state.running:
        handle_events(state, p.get_events())
        if not state.running:
            break
        now = perf_counter()
        dt = now - previous_time
        previous_time = now
        update_movement(state, dt)
        state.frame_index, state.animation_elapsed = advance_animation(
            state.frame_index, state.animation_elapsed, dt)
        p.clear_canvas()
        ground.draw(CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2)
        character.clip_draw(state.frame_index * FRAME_WIDTH, ANIMATIONS[state.animation_name],
                            FRAME_WIDTH, FRAME_HEIGHT, state.x, state.y)
        p.update_canvas()
        p.delay(0.05)
    p.close_canvas()


if __name__ == "__main__":
    main()
