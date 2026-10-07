from pathlib import Path

import pico2d as p

CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 1024
ASSET_DIR = Path(__file__).resolve().parent


def load_asset(filename):
    return p.load_image(str(ASSET_DIR / filename))


def main():
    p.open_canvas(CANVAS_WIDTH, CANVAS_HEIGHT)
    ground = load_asset("TUK_GROUND.png")
    character = load_asset("animation_sheet.png")
    frame = 0
    for x in range(0, 800, 5):
        p.clear_canvas()
        ground.draw(CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2)
        character.clip_draw(frame * 100, 100, 100, 100, x, 90)
        p.update_canvas()
        if any(event.type == p.SDL_QUIT or
               (event.type == p.SDL_KEYDOWN and event.key == p.SDLK_ESCAPE)
               for event in p.get_events()):
            break
        frame = (frame + 1) % 8
        p.delay(0.05)
    p.close_canvas()


if __name__ == "__main__":
    main()
