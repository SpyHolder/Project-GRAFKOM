# Kontribusi Ivone

Nama:Ivone Purba  
NIM: 2401020102

## Vehicle Animation & Interaction

Kontribusi yang dikerjakan pada project Grafika Komputer meliputi:

- Animasi kendaraan (Vehicle Animation)
- Movement Interpolation
- Delta Time
- Frame Independent Animation
- Waypoint Following
- Render Kendaraan
- Trail Effect
- Keyboard Interaction
- Mouse Interaction
- Realtime Interaction

## File yang Terkait

- car.py
- main.py

## Fungsi yang Dibahas

- update()
- draw()
- main()

---

## Implementasi Animasi Kendaraan (update)

Fungsi `update()` digunakan untuk memperbarui posisi kendaraan berdasarkan delta time sehingga pergerakan tetap konsisten pada berbagai frame rate.

```python
px_per_sec = self.speed * tile_size
dist = px_per_sec * dt

if dist >= remaining:
    dist -= remaining
    self.seg_idx += 1
    self.seg_prog = 0.0
else:
    self.seg_prog += dist / seg_len
    dist = 0
```

---

## Implementasi Trail Effect

Trail digunakan untuk menyimpan jejak lintasan kendaraan selama simulasi berlangsung.

```python
new_pos = self.get_world_pos()
self.trail.append(new_pos)

if len(self.trail) > 600:
    self.trail.pop(0)
```

---

## Implementasi Event Handling

Interaksi pengguna dilakukan melalui event keyboard dan mouse yang diproses secara realtime pada fungsi `main()`.

```python
for ev in pygame.event.get():
    if ev.type == pygame.QUIT:
        running = False
```

---

## Hasil Kontribusi

Implementasi yang dilakukan menghasilkan:

- Kendaraan dapat bergerak mengikuti jalur yang dihasilkan algoritma pathfinding.
- Pergerakan kendaraan berlangsung secara halus menggunakan delta time.
- Kendaraan memiliki orientasi yang mengikuti arah jalur.
- Jejak pergerakan (trail effect) dapat ditampilkan selama simulasi.
- Pengguna dapat berinteraksi dengan aplikasi menggunakan keyboard dan mouse secara realtime.
