from pathlib import Path

import pico2d as p

CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 1024
ASSET_DIR = Path(__file__).resolve().parent
FRAME_WIDTH = 100
FRAME_HEIGHT = 100
FRAME_COUNT = 8
ANIMATIONS = {
    "IDLE_RIGHT": 300,
    "IDLE_LEFT": 200,
    "RUN_RIGHT": 100,
    "RUN_LEFT": 0,
}


def load_asset(filename):
    return p.load_image(str(ASSET_DIR / filename))


def main():
    p.open_canvas(CANVAS_WIDTH, CANVAS_HEIGHT)
    ground = load_asset("TUK_GROUND.png")
    character = load_asset("animation_sheet.png")
    frame = 0
    animation_name = "IDLE_RIGHT"
    x, y = CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2
    while True:
        p.clear_canvas()
        ground.draw(CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2)
        character.clip_draw(frame * FRAME_WIDTH, ANIMATIONS[animation_name],
                            FRAME_WIDTH, FRAME_HEIGHT, x, y)
        p.update_canvas()
        if any(event.type == p.SDL_QUIT or
               (event.type == p.SDL_KEYDOWN and event.key == p.SDLK_ESCAPE)
               for event in p.get_events()):
            break
        p.delay(0.05)
    p.close_canvas()


if __name__ == "__main__":
    main()
