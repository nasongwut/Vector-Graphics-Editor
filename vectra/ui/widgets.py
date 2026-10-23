"""Small themed widgets: tooltips, flat buttons, colour swatches, scroll frame, entries."""

import tkinter as tk

from vectra.config import IS_MAC
from vectra.ui.theme import T


class Tooltip:
    def __init__(self, widget, text, side="right", font=None):
        self.w, self.text, self.side, self.font = widget, text, side, font
        self.tip = None
        self.job = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")

    def _schedule(self, _e=None):
        self.hide()
        self.job = self.w.after(450, self.show)

    def show(self):
        if self.tip or not self.w.winfo_exists():
            return
        self.tip = tk.Toplevel(self.w)
        self.tip.wm_overrideredirect(True)
        try:
            self.tip.attributes("-topmost", True)
        except tk.TclError:
            pass
        tk.Label(self.tip, text=self.text, bg="#000000", fg="#ffffff",
                 padx=9, pady=5, font=self.font, justify="left").pack()
        self.tip.update_idletasks()
        if self.side == "right":
            x = self.w.winfo_rootx() + self.w.winfo_width() + 8
            y = self.w.winfo_rooty() + (self.w.winfo_height() - self.tip.winfo_height()) // 2
        else:  # below
            x = self.w.winfo_rootx() + (self.w.winfo_width() - self.tip.winfo_width()) // 2
            y = self.w.winfo_rooty() + self.w.winfo_height() + 6
        self.tip.wm_geometry(f"+{x}+{y}")

    def hide(self, _e=None):
        if self.job:
            try:
                self.w.after_cancel(self.job)
            except tk.TclError:
                pass
            self.job = None
        if self.tip:
            self.tip.destroy()
            self.tip = None


class FlatButton(tk.Label):
    """Flat button with hover + active state (Label-based so it themes everywhere)."""

    def __init__(self, master, text, command=None, font=None, bg=None, fg=None,
                 hover=None, active_bg=None, padx=10, pady=6, width=None,
                 tooltip=None, tip_side="below", tip_font=None):
        self.c_bg = bg or T["panel"]
        self.c_fg = fg or T["text"]
        self.c_hover = hover or T["hover"]
        self.c_active = active_bg or T["accent"]
        super().__init__(master, text=text, bg=self.c_bg, fg=self.c_fg, font=font,
                         padx=padx, pady=pady, cursor="hand2", bd=0)
        if width:
            self.config(width=width)
        self.command = command
        self.active = False
        self._hover = False
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<ButtonRelease-1>", self._click)
        if tooltip:
            Tooltip(self, tooltip, side=tip_side, font=tip_font)

    def _set_hover(self, h):
        self._hover = h
        self._paint()

    def _paint(self):
        if self.active:
            self.config(bg=self.c_active, fg="#ffffff")
        elif self._hover:
            self.config(bg=self.c_hover, fg="#ffffff")
        else:
            self.config(bg=self.c_bg, fg=self.c_fg)

    def set_active(self, a):
        self.active = a
        self._paint()

    def _click(self, e):
        if 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height():
            if self.command:
                self.command()


class Swatch(tk.Canvas):
    """Colour chip; ``None`` is drawn as a red diagonal (no paint)."""

    def __init__(self, master, size=30, command=None, bg=None):
        super().__init__(master, width=size, height=size, bg=bg or T["panel"],
                         highlightthickness=0, cursor="hand2")
        self.size = size
        self.color = None
        if command:
            self.bind("<Button-1>", lambda e: command())

    def set(self, color):
        self.color = color
        self.delete("all")
        s = self.size
        self.create_rectangle(2, 2, s - 2, s - 2, outline=T["border"], width=2,
                              fill=color or T["panel2"])
        if not color:
            self.create_line(5, s - 5, s - 5, 5, fill=T["danger"], width=2)


class DarkEntry(tk.Entry):
    def __init__(self, master, font=None, width=7, on_commit=None):
        super().__init__(master, font=font, width=width, bg=T["entry"], fg=T["text"],
                         insertbackground=T["text"], relief="flat", bd=0,
                         highlightthickness=1, highlightbackground=T["border"],
                         highlightcolor=T["accent"], disabledbackground=T["panel2"],
                         disabledforeground=T["muted"], justify="right")
        self._shown = ""
        self.on_commit = on_commit
        self.bind("<Return>", self._commit)
        self.bind("<KP_Enter>", self._commit)
        self.bind("<Tab>", self._commit)
        # Leaving the field without Enter discards the edit (the selection may have
        # changed by then, so committing on focus-out could hit the wrong objects).
        self.bind("<FocusOut>", lambda e: self.after_idle(self._revert))
        self.bind("<Escape>", lambda e: (self._revert(force=True), self.winfo_toplevel().focus_set()))

    def _has_focus(self):
        try:
            return self.winfo_exists() and self.focus_get() is self
        except (KeyError, tk.TclError):  # focus_get can fail while a menu is posted
            return False

    def _revert(self, force=False):
        if not self.winfo_exists():
            return
        if force or not self._has_focus():
            state = self.cget("state")
            self.config(state="normal")
            self.delete(0, "end")
            self.insert(0, self._shown)
            self.config(state=state)

    def show(self, text):
        """Update the displayed value unless the user is typing in it."""
        self._shown = text
        if self._has_focus():
            return
        state = self.cget("state")
        self.config(state="normal")
        self.delete(0, "end")
        self.insert(0, text)
        self.config(state=state)

    def _commit(self, _e=None):
        val = self.get().strip()
        if val != self._shown and self.on_commit:
            self.on_commit(val)
        return None


class ScrollFrame(tk.Frame):
    """Vertically scrollable container; put children in ``.inner``.

    Mouse-wheel scrolling works while the pointer is anywhere over it.
    """

    _registry = []
    _installed = set()

    def __init__(self, master, bg):
        super().__init__(master, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.bar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview, width=8,
                                bd=0, highlightthickness=0, troughcolor=bg, bg=T["border"],
                                activebackground=T["muted"], relief="flat")
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner.bind("<Configure>", self._update_region)
        self.canvas.bind("<Configure>", self._on_resize)
        ScrollFrame._registry.append(self)
        root = self.winfo_toplevel()
        if str(root) not in ScrollFrame._installed:
            ScrollFrame._installed.add(str(root))
            root.bind_all("<MouseWheel>", ScrollFrame._dispatch_wheel, add="+")
            root.bind_all("<Button-4>", lambda e: ScrollFrame._dispatch_wheel(e, 1), add="+")
            root.bind_all("<Button-5>", lambda e: ScrollFrame._dispatch_wheel(e, -1), add="+")

    def _on_scroll(self, lo, hi):
        self.bar.set(lo, hi)
        need = float(lo) > 0.0 or float(hi) < 1.0
        if need and not self.bar.winfo_ismapped():
            self.bar.pack(side="right", fill="y")
        elif not need and self.bar.winfo_ismapped():
            self.bar.pack_forget()

    def _update_region(self, _e=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_resize(self, e):
        self.canvas.itemconfigure(self._win, width=e.width)

    def scroll_to_top(self):
        self.canvas.yview_moveto(0)

    @classmethod
    def _dispatch_wheel(cls, e, linux_dir=None):
        target = str(e.widget) if e.widget is not None else ""
        cls._registry = [sf for sf in cls._registry if sf.winfo_exists()]
        for sf in cls._registry:
            if target.startswith(str(sf)) and sf.winfo_ismapped():
                if linux_dir is not None:
                    step = -linux_dir
                else:
                    step = -e.delta if IS_MAC else -e.delta / 120
                sf.canvas.yview_scroll(int(step * (1 if IS_MAC else 2)) or (1 if step > 0 else -1), "units")
                return "break"
        return None


class IconButton(tk.Canvas):
    """Small square button whose face is drawn by ``draw(canvas, color)``."""

    def __init__(self, master, draw, command, size=22, tooltip=None, font=None, bg=None):
        self.c_bg = bg or T["panel"]
        super().__init__(master, width=size, height=size, bg=self.c_bg, highlightthickness=0, cursor="hand2")
        self.draw_fn, self.command, self.size = draw, command, size
        self.active = False
        self._hover = False
        self.bind("<Enter>", lambda e: self._set(True))
        self.bind("<Leave>", lambda e: self._set(False))
        self.bind("<ButtonRelease-1>", lambda e: self.command() if self.command else None)
        if tooltip:
            Tooltip(self, tooltip, side="below", font=font)
        self.paint()

    def _set(self, h):
        self._hover = h
        self.paint()

    def set_active(self, a):
        self.active = a
        self.paint()

    def paint(self):
        self.delete("all")
        self.config(bg=T["accent"] if self.active else (T["hover"] if self._hover else self.c_bg))
        before = set(self.find_all())
        self.draw_fn(self, "#ffffff" if (self.active or self._hover) else T["text"])
        off = (self.size - 18) / 2
        for item in set(self.find_all()) - before:
            self.move(item, off, off)


class DarkSpin(tk.Spinbox):
    """Numeric spin box; ``on_commit(value)`` on Enter, arrow click or wheel."""

    def __init__(self, master, from_, to, on_commit, font=None, width=5, increment=1):
        super().__init__(master, from_=from_, to=to, increment=increment, width=width, font=font,
                         bg=T["entry"], fg=T["text"], insertbackground=T["text"],
                         buttonbackground=T["panel2"], relief="flat", bd=0, highlightthickness=1,
                         highlightbackground=T["divider"], highlightcolor=T["accent"],
                         disabledbackground=T["panel2"], disabledforeground=T["dim"],
                         command=self._commit, justify="right")
        self.on_commit = on_commit
        self.bind("<Return>", lambda e: self._commit())
        self.bind("<KP_Enter>", lambda e: self._commit())

    def show(self, value):
        try:
            if self.focus_get() is self:
                return
        except (KeyError, tk.TclError):
            pass
        state = self.cget("state")
        self.config(state="normal")
        self.delete(0, "end")
        self.insert(0, f"{value:g}" if isinstance(value, (int, float)) else str(value))
        self.config(state=state)

    def _commit(self):
        try:
            v = float(self.get().replace(",", "."))
        except ValueError:
            return
        self.on_commit(v)


def setup_ttk_style(root, font):
    from tkinter import ttk
    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except tk.TclError:
        pass
    st.configure("Dark.TCombobox", fieldbackground=T["entry"], background=T["panel2"],
                 foreground=T["text"], arrowcolor=T["text"], bordercolor=T["divider"],
                 lightcolor=T["entry"], darkcolor=T["entry"], selectbackground=T["accent"],
                 selectforeground="#ffffff", insertcolor=T["text"])
    st.map("Dark.TCombobox", fieldbackground=[("readonly", T["entry"])],
           foreground=[("readonly", T["text"])])
    root.option_add("*TCombobox*Listbox.background", T["panel2"])
    root.option_add("*TCombobox*Listbox.foreground", T["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", T["accent"])
    root.option_add("*TCombobox*Listbox.font", font)
