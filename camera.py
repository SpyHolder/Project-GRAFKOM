"""
Seruni Map — Camera System

Modul ini mengatur sistem kamera pada peta generatif Seruni Map.
Fungsi utama modul meliputi:
- Viewport management (pengelolaan area tampilan)
- Zoom in dan zoom out
- Panning atau pergeseran kamera
- Konversi koordinat world space dan screen space
- Level of Detail (LOD) untuk optimasi rendering

Modul ini berperan sebagai penghubung antara data peta yang dihasilkan
algoritma dengan visualisasi yang ditampilkan kepada pengguna.
"""

import pygame
from config import (
    EMPTY,
    STRAIGHT,
    CURVE,
    TJUNCTION,
    CROSS,
    TILE_PORTS,
    get_ports
)


class Camera:
    """
    Kelas Camera digunakan untuk mengatur posisi dan tampilan kamera
    pada area peta yang dapat dijelajahi pengguna.
    """

    def __init__(self, world_w, world_h, screen_w, screen_h):
        # Posisi awal kamera berada di tengah dunia (world)
        self.x = world_w / 2
        self.y = world_h / 2

        # Nilai zoom awal
        self.zoom = 0.35

        # Batas minimum dan maksimum zoom
        self.min_zoom = 0.06
        self.max_zoom = 3.0

        # Ukuran layar aplikasi
        self.sw = screen_w
        self.sh = screen_h

        # Variabel untuk fitur drag/panning
        self.dragging = False
        self.drag_start = None
        self.drag_cam = None

    def world_to_screen(self, wx, wy):
        """
        Mengubah koordinat dunia (world coordinates)
        menjadi koordinat layar (screen coordinates).
        """
        return (
            (wx - self.x) * self.zoom + self.sw / 2,
            (wy - self.y) * self.zoom + self.sh / 2
        )

    def screen_to_world(self, sx, sy):
        """
        Mengubah koordinat layar menjadi koordinat dunia.
        Digunakan saat pengguna melakukan klik atau zoom.
        """
        return (
            (sx - self.sw / 2) / self.zoom + self.x,
            (sy - self.sh / 2) / self.zoom + self.y
        )

    def get_visible_tiles(self, tile_size, cols, rows):
        """
        Menentukan tile yang sedang terlihat pada viewport.
        Dengan cara ini sistem hanya merender area yang terlihat,
        sehingga performa menjadi lebih efisien.
        """
        lx, ty = self.screen_to_world(0, 0)
        rx, by = self.screen_to_world(self.sw, self.sh)

        c0 = max(0, int(lx / tile_size) - 1)
        c1 = min(cols, int(rx / tile_size) + 2)

        r0 = max(0, int(ty / tile_size) - 1)
        r1 = min(rows, int(by / tile_size) + 2)

        return c0, c1, r0, r1

    def get_lod(self):
        """
        Menentukan Level of Detail (LOD).

        HIGH   : zoom dekat
        MEDIUM : zoom sedang
        LOW    : zoom jauh

        Teknik ini digunakan dalam grafika komputer untuk
        mengurangi beban rendering.
        """
        if self.zoom > 0.5:
            return 2

        if self.zoom > 0.2:
            return 1

        return 0

    def zoom_at(self, mx, my, factor):
        """
        Melakukan zoom dengan titik fokus pada posisi kursor mouse.
        Teknik ini membuat pengalaman navigasi lebih nyaman.
        """
        wx, wy = self.screen_to_world(mx, my)

        self.zoom = max(
            self.min_zoom,
            min(self.max_zoom, self.zoom * factor)
        )

        nwx, nwy = self.screen_to_world(mx, my)

        self.x -= (nwx - wx)
        self.y -= (nwy - wy)

    def start_drag(self, mx, my):
        """
        Memulai proses drag atau panning kamera.
        """
        self.dragging = True
        self.drag_start = (mx, my)
        self.drag_cam = (self.x, self.y)

    def do_drag(self, mx, my):
        """
        Menggeser posisi kamera berdasarkan pergerakan mouse.
        """
        if not self.dragging:
            return

        dx = (mx - self.drag_start[0]) / self.zoom
        dy = (my - self.drag_start[1]) / self.zoom

        self.x = self.drag_cam[0] - dx
        self.y = self.drag_cam[1] - dy

    def stop_drag(self):
        """
        Menghentikan proses drag kamera.
        """
        self.dragging = False

    def center_on(self, wx, wy, lerp_t=0.08):
        """
        Memusatkan kamera ke titik tertentu menggunakan
        interpolasi linear (lerp) agar pergerakan terasa halus.
        """
        self.x += (wx - self.x) * lerp_t
        self.y += (wy - self.y) * lerp_t