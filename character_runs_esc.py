from pico2d import *


def main():
    open_canvas()
    grass = load_image("grass.png")
    character = load_image("animation_sheet.png")
    frame = 0
    for x in range(0, 800, 5):
        clear_canvas()
        grass.draw(400, 30)
        character.clip_draw(frame * 100, 100, 100, 100, x, 90)
        update_canvas()
        if any(event.type == SDL_QUIT or
               (event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE)
               for event in get_events()):
            break
        frame = (frame + 1) % 8
        delay(0.05)
    close_canvas()


if __name__ == "__main__":
    main()
