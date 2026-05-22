# Seruni Map — Penjelasan Algoritma

Dokumen ini menjelaskan setiap algoritma yang digunakan dalam project Seruni Map secara mendetail, termasuk **bagaimana** dan **mengapa** setiap algoritma bekerja.

---

## Daftar Isi

1. [Generasi Peta (gen.py)](#1-generasi-peta)
2. [Pathfinding A* (pathfinding.py)](#2-pathfinding-a)
3. [Kurva Bézier (pathfinding.py & renderer.py)](#3-kurva-bézier)
4. [Sistem Kamera (camera.py)](#4-sistem-kamera)
5. [Penempatan Aset (assets.py)](#5-penempatan-aset)
6. [Pergerakan Mobil (car.py)](#6-pergerakan-mobil)
7. [Rendering & LOD (renderer.py & camera.py)](#7-rendering--lod)

---

## 1. Generasi Peta

### Konsep Utama: Corridor Snake Growth

Peta jalan tidak dibuat secara grid biasa, melainkan menggunakan teknik **"ular yang merambat"** (snake growth). Bayangkan seekor ular yang berjalan di grid, meninggalkan jejak berupa jalan.

### Cara Kerja (Langkah demi Langkah)

#### Langkah 1 — Titik Awal (Seed Point)
```
Pilih satu titik random di dekat tengah peta sebagai awal "ular"
```
Titik ini menjadi tile jalan pertama. Mengapa di tengah? Agar jalan bisa menyebar ke segala arah secara merata.

#### Langkah 2 — Pertumbuhan Koridor
```
Untuk setiap koridor baru:
  1. Pilih arah random (atas/bawah/kiri/kanan)
  2. Tentukan panjang random (3 sampai setengah ukuran peta)
  3. "Jalan lurus" ke arah itu selama panjang tersebut
  4. Di setiap langkah, ada kemungkinan kecil untuk belok
```

Ini menghasilkan jalan yang **berkelok-kelok organik**, bukan grid kaku. Setiap koridor seperti ular yang berjalan dengan sedikit goyangan.

#### Langkah 3 — Penentuan Tipe Tile (CSP - Constraint Satisfaction)

Setelah menentukan posisi jalan, setiap tile perlu ditentukan tipenya:

| Tipe | Bentuk | Kapan Digunakan |
|------|--------|-----------------|
| **Straight** | ─ atau │ | Jalan lurus, koneksi 2 arah berlawanan |
| **Curve** | ╮╯╰╭ | Belokan, koneksi 2 arah bersebelahan |
| **T-Junction** | ┬┤┴├ | Persimpangan 3 arah |
| **Cross** | ┼ | Perempatan 4 arah |

Sistem **port** menentukan arah mana yang terbuka:
```
Port 0 = Atas    Port 1 = Kanan
Port 2 = Bawah   Port 3 = Kiri
```

Setiap tile harus memenuhi **constraint**: jika tile A punya port mengarah ke tile B, maka tile B HARUS punya port mengarah balik ke A. Ini disebut **Constraint Satisfaction Problem (CSP)**.

```
Contoh valid:        Contoh INVALID:
  ┌──────┐              ┌──────┐
  │ A ──→│ ←── B │      │ A ──→│  B  │  (B tidak punya port kiri!)
  └──────┘              └──────┘
```

#### Langkah 4 — Penyembuhan Jalan Buntu (Dead-End Healing)

Setelah semua koridor dibuat, ada beberapa "jalan buntu" (tile yang hanya terhubung ke 1 arah). Algoritma healing menangani ini:

```
Ulangi sampai tidak ada lagi jalan buntu:
  1. Temukan semua tile dengan hanya 1 koneksi (degree = 1)
  2. Untuk yang di tepi peta → biarkan (pintu masuk/keluar)
  3. Untuk yang di interior:
     a. Coba perpanjang ke tetangga yang sudah ada jalan
     b. Jika tidak bisa → hapus tile tersebut
```

#### Langkah 5 — Downgrade Tile Berlebihan

Langkah terakhir: jika ada T-Junction yang sebenarnya hanya punya 2 koneksi aktif, dia di-downgrade jadi Curve atau Straight.

```
Sebelum:  ┬ (T-Junction, tapi arah atas tidak terhubung ke apapun)
Sesudah:  ─ (Straight, lebih akurat)
```

#### Konektivitas (BFS Verification)
Setelah semua proses, dilakukan pengecekan BFS (Breadth-First Search) untuk memastikan **semua tile jalan terhubung satu sama lain**. Jika ada pulau terpisah, mereka dihubungkan atau dihapus.

---

## 2. Pathfinding A*

### Apa itu A*?

A* (dibaca "A-star") adalah algoritma pencarian jalan terpendek. Bayangkan kamu di sebuah labirin dan ingin menemukan jalan tercepat ke pintu keluar. A* melakukan hal itu, tapi secara cerdas — tidak memeriksa semua jalan, hanya yang **kemungkinan besar** mengarah ke tujuan.

### Cara Kerja

```
1. Mulai dari titik awal, masukkan ke "daftar terbuka" (open set)
2. Ambil tile dengan skor F terkecil dari daftar
3. Jika tile ini adalah tujuan → selesai! Telusuri balik untuk dapatkan jalur
4. Jika bukan, periksa semua tetangga yang terhubung via port
5. Untuk setiap tetangga:
   - Hitung G = jarak dari awal ke tetangga ini
   - Hitung H = estimasi jarak ke tujuan (Manhattan distance)
   - F = G + H
   - Masukkan ke daftar terbuka jika belum pernah dikunjungi
6. Ulangi dari langkah 2
```

### Rumus Manhattan Distance

```
H = |x_sekarang - x_tujuan| + |y_sekarang - y_tujuan|
```

Ini adalah estimasi "seberapa jauh" tanpa memperhitungkan rintangan. Contoh:
```
Posisi sekarang: (3, 5)
Tujuan:          (7, 2)
H = |3-7| + |5-2| = 4 + 3 = 7
```

### Mengapa A* Cepat?

Tanpa heuristic (Dijkstra), algoritma memeriksa tile secara melingkar ke segala arah. Dengan heuristic Manhattan, A* **memprioritaskan tile yang mengarah ke tujuan**, sehingga jauh lebih sedikit tile yang perlu diperiksa.

```
Dijkstra (tanpa H):        A* (dengan H):
  ○ ○ ○ ○ ○                    ○
  ○ ○ ○ ○ ○                  ○ ○ ○
  ○ ○ S ○ ○      vs        ○ ○ S → → E
  ○ ○ ○ ○ ○                  ○ ○
  ○ ○ ○ ○ E                    ○
  (semua diperiksa)         (hanya arah tujuan)
```

### Integrasi dengan Aset

Ketika user memilih aset (rumah/gerobak/basecamp) sebagai tujuan, tile aset bukan jalan. Maka:
1. Cari tile jalan terdekat dari aset (`find_nearest_road` via BFS)
2. Jalankan A* ke tile jalan tersebut

---

## 3. Kurva Bézier

### Apa itu Kurva Bézier?

Kurva Bézier adalah kurva halus yang dibentuk oleh titik kontrol. Project ini menggunakan **Quadratic Bézier** (3 titik kontrol).

### Rumus Quadratic Bézier

```
B(t) = (1-t)² × P0 + 2(1-t)t × P1 + t² × P2

dimana:
  P0 = titik awal
  P1 = titik kontrol (menentukan kelengkungan)
  P2 = titik akhir
  t  = parameter dari 0 sampai 1
```

Ketika t = 0, hasilnya P0 (titik awal). Ketika t = 1, hasilnya P2 (titik akhir). Nilai di antaranya menghasilkan kurva halus yang "ditarik" ke arah P1.

### Penggunaan dalam Project

#### 1. Rendering Jalan Belokan (renderer.py)
```
Untuk tile CURVE dengan port 0 (atas) dan port 1 (kanan):
  P0 = titik tengah tepi atas tile
  P1 = titik tengah tile (kontrol)
  P2 = titik tengah tepi kanan tile

Hasilnya: belokan halus dari atas ke kanan
```

#### 2. Jalur Dunia (pathfinding.py — build_world_path)
```
Untuk setiap tile yang membelok dalam jalur A*:
  - Masuk dari port entry → keluar dari port exit
  - Jika berlawanan (lurus) → garis lurus
  - Jika bersebelahan (belok) → kurva Bézier
```

#### 3. Band Rendering (renderer.py — _fband)
Untuk menggambar jalan dengan lebar tertentu, bukan hanya garis:
```
1. Hitung kurva pusat (Bézier)
2. Buat kurva offset ke KIRI sepanjang setengah lebar jalan
3. Buat kurva offset ke KANAN sepanjang setengah lebar jalan
4. Gabungkan jadi polygon (band)
```

Offset dihitung dengan mencari **vektor normal** di setiap titik kurva:
```
Normal = tegak lurus terhadap arah kurva di titik tersebut
```

---

## 4. Sistem Kamera

### Zoom at Cursor

Saat user melakukan zoom, titik di bawah kursor mouse tetap di posisi yang sama di layar. Ini memberikan pengalaman zoom yang intuitif.

```
Cara kerja:
1. Simpan posisi dunia di bawah kursor SEBELUM zoom
   (world_before = screen_to_world(mouse_x, mouse_y))
2. Ubah level zoom
3. Hitung ulang posisi dunia di bawah kursor SESUDAH zoom
   (world_after = screen_to_world(mouse_x, mouse_y))
4. Koreksi posisi kamera:
   camera.x -= (world_after.x - world_before.x)
   camera.y -= (world_after.y - world_before.y)
```

### Transformasi Koordinat

Setiap objek memiliki posisi "dunia" (world) dan perlu dikonversi ke posisi "layar" (screen):

```
World → Screen:
  screen_x = (world_x - camera_x) × zoom + layar_lebar/2
  screen_y = (world_y - camera_y) × zoom + layar_tinggi/2

Screen → World (kebalikannya):
  world_x = (screen_x - layar_lebar/2) / zoom + camera_x
```

### LOD (Level of Detail)

Tergantung zoom level, kualitas rendering berubah:

| Zoom Level | LOD | Rendering |
|-----------|-----|-----------|
| > 0.5 | HIGH | Bézier curves, dash lines, sidewalks |
| 0.2 – 0.5 | MEDIUM | Simplified rectangles per port |
| < 0.2 | LOW | Single colored rectangle per tile |

Ini **menghemat performa** saat zoom jauh karena detail halus tidak terlihat.

---

## 5. Penempatan Aset

### Algoritma Penempatan

Aset ditempatkan dalam 4 fase setelah peta jalan selesai:

#### Fase 1 — Basecamp (unik, 1 per peta)
```
1. Temukan semua tile kosong yang bersebelahan dengan jalan
2. Urutkan berdasarkan: banyak sisi jalan + kedekatan ke pusat peta
3. Pilih yang terbaik → letakkan Basecamp
```
Basecamp selalu di lokasi strategis (banyak akses, dekat pusat).

#### Fase 2 — Gerobak (5-6 per peta, tersebar)
```
1. Acak urutan tile pinggir jalan
2. Untuk setiap gerobak yang akan ditempatkan:
   - Pastikan jaraknya ≥ grid_size/8 dari gerobak lain
   - Jika cukup jauh → letakkan
   - Jika terlalu dekat → lewati, coba tile berikutnya
```
Jarak minimum menjamin gerobak **tersebar merata**, bukan menumpuk.

#### Fase 3 — Rumah & Pohon (pinggir jalan)
```
Untuk setiap tile pinggir jalan yang tersisa:
  - 40% kemungkinan → Rumah
  - 60% kemungkinan → Pohon
```

#### Fase 4 — Pohon Pengisi (~60% tile kosong)
```
Untuk setiap tile kosong yang TIDAK bersebelahan dengan jalan:
  - 60% kemungkinan → letakkan Pohon
  - 40% → biarkan kosong (rumput)
```
Tidak 100% diisi agar peta tidak terlalu padat.

### Rotasi Aset

Aset bangunan (gerobak, basecamp, rumah) **menghadap ke jalan** terdekat:
```
Jika jalan ada di sebelah kanan aset → rotasi = 1 (menghadap kanan)
Jika jalan ada di atas → rotasi = 0 (menghadap atas)
```

### Pencarian Aset Terdekat (BFS)

Ketika user menekan [G] atau [B], sistem mencari gerobak/basecamp terdekat menggunakan **Breadth-First Search**:

```
1. Mulai dari posisi start
2. Periksa semua tetangga (jarak 1)
3. Jika ada gerobak/basecamp → selesai!
4. Jika tidak, periksa tetangga dari tetangga (jarak 2)
5. Terus sampai ditemukan
```

BFS menjamin hasil **selalu yang terdekat** karena memeriksa dari jarak terkecil ke terbesar.

---

## 6. Pergerakan Mobil

### Interpolasi Polyline

Mobil mengikuti jalur yang sudah di-smooth oleh Bézier. Jalur ini berupa rangkaian titik-titik dunia (polyline).

```
world_path = [(x0,y0), (x1,y1), (x2,y2), ...]

Mobil berada di segmen ke-N dengan progress 0.0 sampai 1.0:
  posisi = P_n + (P_{n+1} - P_n) × progress
```

### Update Tiap Frame

```
Setiap frame:
  1. Hitung jarak tempuh = kecepatan × delta_time
  2. Maju sepanjang segmen saat ini
  3. Jika sampai ujung segmen → pindah ke segmen berikutnya
  4. Hitung sudut baru berdasarkan arah segmen
  5. Simpan posisi ke trail (jejak)
```

### Rotasi Sprite

Sudut mobil dihitung dari arah segmen saat ini:
```
angle = atan2(y_selanjutnya - y_sekarang, x_selanjutnya - x_sekarang)
```
Sprite dirotasi sesuai sudut ini, lalu di-cache agar tidak perlu dirotasi ulang setiap frame.

---

## 7. Rendering & LOD

### Tile Caching (TileCache)

Menggambar Bézier setiap frame untuk setiap tile akan sangat lambat. Solusinya: **pre-render** semua kemungkinan tile ke Surface terpisah.

```
Saat inisialisasi:
  Untuk setiap tipe tile × setiap rotasi:
    1. Buat Surface kosong ukuran tile
    2. Gambar jalan dengan Bézier di atasnya
    3. Simpan ke dictionary cache

Saat rendering:
  Untuk setiap tile di layar:
    1. Ambil Surface dari cache berdasarkan (tipe, rotasi)
    2. Blit ke layar (operasi sangat cepat)
```

### Dashed Line pada Kurva

Garis putus-putus di tengah jalan mengikuti kurva. Ini dicapai dengan:

```
1. Ambil titik-titik kurva Bézier
2. Untuk setiap segmen antar titik:
   a. Hitung panjang segmen
   b. Jika sedang "menggambar" → gambar garis sepanjang DASH_ON
   c. Jika sedang "gap" → lewati sepanjang DASH_OFF
   d. Akumulasi sisa dari segmen sebelumnya
```

Hasilnya: garis putus-putus yang mengikuti kelengkungan jalan dengan jarak yang konsisten.

### Minimap

Peta mini di pojok kanan bawah menampilkan seluruh peta dalam skala kecil:

```
Skala = 180 pixel / max(kolom, baris)

Setiap tile digambar sebagai 1 pixel persegi:
  - Jalan → abu-abu
  - Gerobak → kuning-oranye
  - Basecamp → kuning terang
  - Rumah → abu-abu gelap
  - Pohon → hijau sangat gelap

Viewport kamera ditampilkan sebagai kotak putih.
```

---

## Ringkasan Algoritma

| Algoritma | File | Kompleksitas | Tujuan |
|-----------|------|-------------|--------|
| Snake Growth | gen.py | O(n) per koridor | Generasi jalan organik |
| CSP | gen.py | O(n) | Penentuan tipe & rotasi tile |
| BFS Connectivity | gen.py | O(V+E) | Verifikasi konektivitas |
| Dead-End Healing | gen.py | O(n × iterasi) | Eliminasi jalan buntu |
| A* | pathfinding.py | O(E log V) | Pencarian jalan terpendek |
| Quadratic Bézier | pathfinding.py, renderer.py | O(steps) | Smoothing jalur & jalan |
| BFS Nearest | main.py | O(V+E) | Pencarian aset terdekat |
| Distance Interpolation | car.py | O(1) per frame | Pergerakan mobil halus |
| LOD Selection | camera.py | O(1) | Optimasi performa rendering |
| Tile Caching | camera.py | O(1) lookup | Percepatan rendering |

> **V** = jumlah tile, **E** = jumlah koneksi, **n** = jumlah tile jalan
