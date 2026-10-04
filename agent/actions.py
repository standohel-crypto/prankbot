import tkinter as tk
from tkinter import messagebox


def warning(root):
    messagebox.showwarning(
        "Внимание",
        "Обнаружено несанкционированное использование ПК!",
        parent=root
    )


def error(root):
    messagebox.showerror(
        "Ошибка",
        "Запущена самоликвидация системы...",
        parent=root
    )


def joke(root):
    messagebox.showinfo(
        "Шутка",
        "Ладно, расслабься, это просто розыгрыш :)",
        parent=root
    )


def prank(root):
    warning(root)
    error(root)
    joke(root)


def status(root):
    return True


def _fullscreen(root, title, bg, text, fg="white", seconds=10):
    window = tk.Toplevel(root)
    window.title(title)
    window.attributes("-fullscreen", True)
    window.attributes("-topmost", True)
    window.configure(bg=bg)

    label = tk.Label(
        window,
        text=text,
        bg=bg,
        fg=fg,
        font=("Segoe UI", 28),
        justify="center",
    )
    label.pack(expand=True)

    # Всегда есть аварийный выход.
    window.bind("<Escape>", lambda event: window.destroy())
    window.after(seconds * 1000, window.destroy)


def fake_bsod(root):
    _fullscreen(
        root,
        "Windows",
        "#0078D7",
        ": (\n\nYour PC ran into a problem.\n\n"
        "0% complete\n\n"
        "FAKE PRANK SCREEN\n\nPress ESC to exit",
        seconds=15,
    )


def fake_lock(root):
    _fullscreen(
        root,
        "System Locked",
        "black",
        "🔒 COMPUTER LOCKED\n\n"
        "Suspicious activity detected.\n\n"
        "This is a prank :)\n\n"
        "Press ESC to exit",
        seconds=15,
    )


def fake_freeze(root):
    _fullscreen(
        root,
        "Not Responding",
        "#111111",
        "Windows is not responding...\n\nPlease wait...\n\n"
        "Press ESC to exit",
        seconds=10,
    )


def fake_shutdown(root):
    _fullscreen(
        root,
        "Shutting down",
        "black",
        "Shutting down...\n\n"
        "FAKE PRANK\n\n"
        "Press ESC to exit",
        seconds=10,
    )


ACTIONS = {
    "warning": warning,
    "error": error,
    "joke": joke,
    "prank": prank,
    "fake_bsod": fake_bsod,
    "fake_lock": fake_lock,
    "fake_freeze": fake_freeze,
    "fake_shutdown": fake_shutdown,
    "status": status,
}
