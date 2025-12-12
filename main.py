import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

class WhiteboardArea(Gtk.DrawingArea):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.set_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK
        )
        self.strokes = []           # [(x, y), ...] — in world coordinates
        self.current_stroke = None
        self.brush_size = 3

        # panning: shifting the "camera"
        self.offset_x = 0
        self.offset_y = 0
        self.is_panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0

        self.connect("draw", self.on_draw)
        self.connect("button-press-event", self.on_button_press)
        self.connect("motion-notify-event", self.on_motion)
        self.connect("button-release-event", self.on_button_release)

        ### IMPORTANT: do not set set_size_request — let it stretch across the window.
        self.set_hexpand(True)
        self.set_vexpand(True)

    def clear(self):
        self.strokes = []
        self.current_stroke = None
        self.queue_draw()

    def screen_to_world(self, sx, sy):
        """Преобразует экранные координаты в мировые (с учётом смещения камеры)."""
        return sx - self.offset_x, sy - self.offset_y

    def on_draw(self, widget, cr):
        # background
        cr.set_source_rgb(*self.app.bg_color)
        cr.paint()

        # brush
        cr.set_source_rgb(*self.app.brush_color)
        cr.set_line_width(self.brush_size)
        cr.set_line_cap(1)
        cr.set_line_join(1)

        # draw all the strokes (in world coordinates → screen coordinates = world coordinates + offset)
        for stroke in self.strokes:
            if len(stroke) < 2:
                if stroke:
                    # single point
                    x, y = stroke[0]
                    cr.arc(x + self.offset_x, y + self.offset_y, self.brush_size / 2, 0, 2 * 3.14159)
                    cr.fill()
                continue
            cr.move_to(stroke[0][0] + self.offset_x, stroke[0][1] + self.offset_y)
            for x, y in stroke[1:]:
                cr.line_to(x + self.offset_x, y + self.offset_y)
            cr.stroke()

        # The current stroke
        if self.current_stroke and len(self.current_stroke) >= 2:
            cr.move_to(self.current_stroke[0][0] + self.offset_x, self.current_stroke[0][1] + self.offset_y)
            for x, y in self.current_stroke[1:]:
                cr.line_to(x + self.offset_x, y + self.offset_y)
            cr.stroke()
        elif self.current_stroke and len(self.current_stroke) == 1:
            x, y = self.current_stroke[0]
            cr.arc(x + self.offset_x, y + self.offset_y, self.brush_size / 2, 0, 2 * 3.14159)
            cr.fill()

    def on_button_press(self, widget, event):
        if event.button == 3:
            self.is_panning = True
            self.pan_start_x = event.x
            self.pan_start_y = event.y
            self.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.FLEUR))
            return Gdk.EVENT_STOP

        elif event.button == 1 and not self.is_panning:
            wx, wy = self.screen_to_world(event.x, event.y)
            self.current_stroke = [(wx, wy)]
            self.queue_draw()
            return Gdk.EVENT_STOP

        return Gdk.EVENT_PROPAGATE

    def on_motion(self, widget, event):
        if self.is_panning:
            dx = event.x - self.pan_start_x
            dy = event.y - self.pan_start_y
            self.offset_x += dx
            self.offset_y += dy
            self.pan_start_x = event.x
            self.pan_start_y = event.y
            self.queue_draw()
            return Gdk.EVENT_STOP

        elif event.state & Gdk.ModifierType.BUTTON1_MASK and not self.is_panning:
            if self.current_stroke is not None:
                wx, wy = self.screen_to_world(event.x, event.y)
                self.current_stroke.append((wx, wy))
                self.queue_draw()
            return Gdk.EVENT_STOP

        return Gdk.EVENT_PROPAGATE

    def on_button_release(self, widget, event):
        if event.button == 3:
            self.is_panning = False
            self.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.LEFT_PTR))
            return Gdk.EVENT_STOP

        elif event.button == 1 and self.current_stroke is not None:
            if len(self.current_stroke) > 0:
                self.strokes.append(self.current_stroke)
            self.current_stroke = None
            self.queue_draw()
            return Gdk.EVENT_STOP

        return Gdk.EVENT_PROPAGATE


class WhiteboardApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.example.whiteboard")
        self.connect("activate", self.on_activate)
        self.bg_color = (1.0, 1.0, 1.0)      
        self.brush_color = (0.0, 0.0, 0.0)   
        self.board = None

    def on_activate(self, app):
        win = Gtk.ApplicationWindow(application=app, title="aboard")
        win.set_default_size(1000, 700)

        
        overlay = Gtk.Overlay()
        win.add(overlay)

        
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        overlay.add(main_box)

        
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        sidebar.set_size_request(120, -1)
        sidebar.set_margin_top(10)
        sidebar.set_margin_bottom(10)

        def btn(label, cb=None):
            b = Gtk.Button(label=label)
            if cb:
                b.connect("clicked", cb)
            return b

        sidebar.pack_start(btn("Clear", self.on_clear), False, False, 0)
        sidebar.pack_start(btn("Инструмент 1"), False, False, 0)
        sidebar.pack_start(btn("Инструмент 2"), False, False, 0)

        main_box.pack_start(sidebar, False, False, 0)

        
        self.board = WhiteboardArea(self)
        main_box.pack_start(self.board, True, True, 0)

        
        options_btn = Gtk.MenuButton()
        options_btn.set_direction(Gtk.ArrowType.NONE)
        options_btn.set_halign(Gtk.Align.START)
        options_btn.set_valign(Gtk.Align.START)
        options_btn.set_margin_start(10)
        options_btn.set_margin_top(10)

        menu = Gtk.Menu()
        dark_item = Gtk.MenuItem(label="Чёрный фон (ночной режим)")
        dark_item.connect("activate", self.on_dark_theme)
        menu.append(dark_item)
        menu.show_all()
        options_btn.set_popup(menu)

        overlay.add_overlay(options_btn)

        win.show_all()

    def on_clear(self, button):
        if self.board:
            self.board.clear()

    def on_dark_theme(self, item):
        self.bg_color = (0.0, 0.0, 0.0)
        self.brush_color = (1.0, 1.0, 1.0)
        if self.board:
            self.board.clear()


if __name__ == "__main__":
    app = WhiteboardApp()
    app.run()
