"""Regression tests; application code remains in one file."""
import contextlib
import importlib.util
import io
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace as Event
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("viewer", ROOT / "character_runs_esc.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


class MovementTests(unittest.TestCase):
    def setUp(self):
        self.state = v.ViewerState()

    def move(self, keys, dt=0.05):
        self.state.pressed_keys = set(keys)
        v.update_movement(self.state, dt)

    def test_initial_state(self):
        s = self.state
        self.assertEqual((s.x, s.y, s.animation_name), (640, 512, "IDLE_RIGHT"))
        self.assertFalse(s.cursor_visible)

    def test_speed_and_release(self):
        self.state.pressed_keys = {v.p.SDLK_RIGHT}
        for _ in range(20): v.update_movement(self.state, 0.05)
        self.assertEqual(self.state.x, 840)
        self.move([])
        self.assertEqual((self.state.x, self.state.animation_name), (840, "IDLE_RIGHT"))

    def test_four_animation_states(self):
        seen = {self.state.animation_name}
        for key in [v.p.SDLK_LEFT, v.p.SDLK_RIGHT]:
            self.move([key])
            seen.add(self.state.animation_name)
            self.move([])
            seen.add(self.state.animation_name)
        self.assertEqual(seen, set(v.ANIMATIONS))

    def test_vertical_keeps_both_facings(self):
        for facing in ["LEFT", "RIGHT"]:
            self.state.facing = facing
            for key in [v.p.SDLK_UP, v.p.SDLK_DOWN]:
                with self.subTest(facing=facing, key=key):
                    self.move([key])
                    self.assertEqual(self.state.animation_name, "RUN_" + facing)
                    self.assertEqual(self.state.x, 640)
                    self.move([])
                    self.assertEqual(self.state.animation_name, "IDLE_" + facing)

    def test_all_diagonals_have_equal_speed(self):
        for h in [v.p.SDLK_LEFT, v.p.SDLK_RIGHT]:
            for vert in [v.p.SDLK_UP, v.p.SDLK_DOWN]:
                self.state = v.ViewerState()
                self.move([h, vert])
                self.assertAlmostEqual(math.hypot(self.state.x-640, self.state.y-512), 10)

    def test_opposite_keys_and_partial_release(self):
        keys = [v.p.SDLK_LEFT, v.p.SDLK_RIGHT, v.p.SDLK_UP, v.p.SDLK_DOWN]
        self.move(keys)
        self.assertEqual((self.state.x, self.state.y), (640, 512))
        keys.remove(v.p.SDLK_LEFT)
        self.move(keys)
        self.assertEqual((self.state.x, self.state.y), (650, 512))

    def test_corners_and_blocked_idle(self):
        for h, x in [(v.p.SDLK_LEFT, 50), (v.p.SDLK_RIGHT, 1230)]:
            for vert, y in [(v.p.SDLK_DOWN, 50), (v.p.SDLK_UP, 974)]:
                self.state = v.ViewerState()
                self.state.pressed_keys = {h, vert}
                for _ in range(400): v.update_movement(self.state, 0.05)
                self.assertEqual((self.state.x, self.state.y), (x, y))
                self.assertEqual(self.state.motion_state, "IDLE")

    def test_slide_along_boundary(self):
        self.state.x = 1230
        self.move([v.p.SDLK_RIGHT, v.p.SDLK_UP])
        self.assertEqual(self.state.x, 1230)
        self.assertGreater(self.state.y, 512)
        self.assertEqual(self.state.animation_name, "RUN_RIGHT")

    def test_dt_cap_and_negative_dt(self):
        self.move([v.p.SDLK_RIGHT], 5)
        self.assertEqual(self.state.x, 650)
        self.move([v.p.SDLK_RIGHT], -1)
        self.assertEqual(self.state.x, 650)


class AnimationInputTests(unittest.TestCase):
    def test_each_animation_cycles_all_frames(self):
        for name in v.ANIMATIONS:
            with self.subTest(name=name):
                frame, elapsed = 0, 0.0
                seen = []
                for _ in range(8):
                    seen.append(frame)
                    frame, elapsed = v.advance_animation(frame, elapsed, 0.1)
                self.assertEqual(seen, list(range(8)))
                self.assertEqual(frame, 0)
                self.assertAlmostEqual(elapsed, 0)

    def test_animation_transition_and_continuity(self):
        s = v.ViewerState()
        s.frame_index, s.animation_elapsed = 5, 0.07
        v.select_animation(s, "IDLE_RIGHT")
        self.assertEqual((s.frame_index, s.animation_elapsed), (5, 0.07))
        v.select_animation(s, "RUN_LEFT")
        self.assertEqual((s.frame_index, s.animation_elapsed), (0, 0))

    def test_irregular_animation_dt(self):
        frame, elapsed = v.advance_animation(0, 0, 0.35)
        self.assertEqual(frame, 3)
        self.assertAlmostEqual(elapsed, 0.05)

    def test_repeated_keydown_and_keyup(self):
        s = v.ViewerState()
        down = Event(type=v.p.SDL_KEYDOWN, key=v.p.SDLK_LEFT)
        v.handle_events(s, [down]*5)
        self.assertEqual(s.pressed_keys, {v.p.SDLK_LEFT})
        v.handle_events(s, [Event(type=v.p.SDL_KEYUP, key=v.p.SDLK_LEFT)]*2)
        self.assertFalse(s.pressed_keys)

    def test_exit_stops_event_batch(self):
        for exit_event in [Event(type=v.p.SDL_QUIT), Event(type=v.p.SDL_KEYDOWN, key=v.p.SDLK_ESCAPE)]:
            s = v.ViewerState()
            v.handle_events(s, [exit_event, Event(type=v.p.SDL_KEYDOWN, key=v.p.SDLK_RIGHT)])
            self.assertFalse(s.running)
            self.assertFalse(s.pressed_keys)

    def test_mouse_coordinates_do_not_move_character(self):
        s = v.ViewerState()
        for x, y in [(0, 0), (1279, 1023), (640, 512)]:
            v.handle_events(s, [Event(type=v.p.SDL_MOUSEMOTION, x=x, y=y)])
            self.assertEqual((s.cursor_x, s.cursor_y), (x, 1023-y))
        self.assertEqual((s.x, s.y, s.facing), (640, 512, "RIGHT"))

    def test_focus_loss_and_mouse_reentry(self):
        s = v.ViewerState()
        s.pressed_keys = {v.p.SDLK_RIGHT}
        with patch.object(v.backend, "window", None, create=True), patch.object(v.backend, "SDL_GetWindowFlags", return_value=0):
            v.sync_window_state(s)
        self.assertFalse(s.pressed_keys)
        self.assertFalse(s.cursor_visible)
        def position(x, y):
            x._obj.value, y._obj.value = 333, 444
            return 0
        flags = v.backend.SDL_WINDOW_SHOWN | v.backend.SDL_WINDOW_INPUT_FOCUS | v.backend.SDL_WINDOW_MOUSE_FOCUS
        with patch.object(v.backend, "window", None, create=True), patch.object(v.backend, "SDL_GetWindowFlags", return_value=flags), patch.object(v.backend, "SDL_GetMouseState", side_effect=position):
            v.sync_window_state(s)
        self.assertEqual((s.cursor_visible, s.cursor_x, s.cursor_y), (True, 333, 579))


    def test_hidden_and_minimized_stale_focus(self):
        for visibility in [0, v.backend.SDL_WINDOW_SHOWN | v.backend.SDL_WINDOW_MINIMIZED]:
            s = v.ViewerState()
            s.pressed_keys = {v.p.SDLK_LEFT}
            s.cursor_visible = True
            flags = visibility | v.backend.SDL_WINDOW_INPUT_FOCUS | v.backend.SDL_WINDOW_MOUSE_FOCUS
            with patch.object(v.backend, "window", None, create=True), patch.object(v.backend, "SDL_GetWindowFlags", return_value=flags):
                v.sync_window_state(s)
            self.assertFalse(s.pressed_keys)
            self.assertFalse(s.cursor_visible)


class RenderingLifecycleTests(unittest.TestCase):
    def test_render_order_and_hotspot(self):
        calls = []
        class Image:
            def __init__(self, name): self.name = name
            def draw(self, *args): calls.append((self.name, args))
            def clip_draw(self, *args): calls.append((self.name, args))
        s = v.ViewerState()
        s.cursor_visible, s.cursor_x, s.cursor_y = True, 100, 200
        with patch.object(v.p, "clear_canvas"), patch.object(v.p, "update_canvas"):
            v.render(s, Image("ground"), Image("character"), Image("cursor"))
        self.assertEqual([name for name, _ in calls], ["ground", "character", "cursor"])
        self.assertEqual(calls[-1][1], (125, 174))

    def test_hidden_cursor_not_drawn(self):
        s = v.ViewerState()
        cursor = Mock()
        with patch.object(v.p, "clear_canvas"), patch.object(v.p, "update_canvas"):
            v.render(s, Mock(), Mock(), cursor)
        cursor.draw.assert_not_called()

    def test_asset_paths_and_failures(self):
        with patch.object(v.p, "load_image", return_value="image") as load:
            self.assertEqual(v.load_asset("animation_sheet.png"), "image")
            self.assertEqual(Path(load.call_args.args[0]), ROOT / "animation_sheet.png")
        with tempfile.TemporaryDirectory(dir=ROOT / ".venv") as directory, patch.object(v, "ASSET_DIR", Path(directory)):
            with self.assertRaisesRegex(RuntimeError, "Missing asset:.*hand_arrow.png"):
                v.load_asset("hand_arrow.png")
        with patch.object(v.p, "load_image", side_effect=IOError):
            with self.assertRaisesRegex(RuntimeError, "Cannot load asset:.*animation_sheet.png"):
                v.load_asset("animation_sheet.png")

    def run_main(self, asset_error=False, render_error=False, exit_key=False):
        calls = []
        exit_event = Event(type=v.p.SDL_KEYDOWN, key=v.p.SDLK_ESCAPE) if exit_key else Event(type=v.p.SDL_QUIT)
        events = [[]] if render_error else [[exit_event]]
        with contextlib.ExitStack() as stack:
            for name in ["open_canvas", "hide_cursor", "show_cursor", "close_canvas"]:
                stack.enter_context(patch.object(v.p, name, side_effect=lambda *args, n=name: calls.append(n)))
            for name in ["window", "renderer"]:
                stack.enter_context(patch.object(v.backend, name, object(), create=True))
            stack.enter_context(patch.object(v.p, "get_events", side_effect=events))
            stack.enter_context(patch.object(v, "load_asset", side_effect=RuntimeError("Missing asset: TUK_GROUND.png") if asset_error else None, return_value=Mock()))
            stack.enter_context(patch.object(v, "sync_window_state"))
            render = stack.enter_context(patch.object(v, "render", side_effect=RuntimeError("render failure") if render_error else None))
            error = io.StringIO()
            with contextlib.redirect_stderr(error): result = v.main()
        return result, calls, render.call_count, error.getvalue()

    def test_quit_and_escape_skip_render_and_cleanup(self):
        for exit_key in [False, True]:
            result, calls, renders, error = self.run_main(exit_key=exit_key)
            self.assertEqual(result, 0)
            self.assertEqual(calls[-2:], ["show_cursor", "close_canvas"])
            self.assertEqual(renders, 0)

    def test_asset_failure_cleanup(self):
        result, calls, renders, error = self.run_main(asset_error=True)
        self.assertEqual(result, 1)
        self.assertIn("TUK_GROUND.png", error)
        self.assertEqual(calls, ["open_canvas", "show_cursor", "close_canvas"])

    def test_render_failure_cleanup(self):
        result, calls, renders, error = self.run_main(render_error=True)
        self.assertEqual(result, 1)
        self.assertIn("render failure", error)
        self.assertEqual(calls[-2:], ["show_cursor", "close_canvas"])


if __name__ == "__main__":
    unittest.main()
