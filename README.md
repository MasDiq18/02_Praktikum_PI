# UTS Praktikum Penelusuran Informasi

Kelompok 2:
1. Muhammad Fazel Mawla (2408107010074)
2. Maulana Shidqi Albadawie (2408107010047)
3. Faris Fudhaili (2408107010040)

Sistem IR berbasis Python CLI untuk **lima dataset**. Whoosh mengambil seluruh
dokumen yang memiliki setidaknya satu token query; CountVectorizer membentuk
Bag of Words; cosine similarity menentukan urutan hasil akhir. Menu pencarian
menampilkan lima hasil dengan skor tertinggi. Tidak memerlukan server/database.

## 1. Persiapan

Direkomendasikan Python **3.11 atau 3.12, 64-bit**. Versi pustaka dikunci dalam
`requirements.txt`; lingkungan pengujian dicatat dalam `results/evaluation.json`.
Gunakan lingkungan virtual agar paket terpasang pada interpreter yang benar.

Windows (PowerShell):

```powershell
cd "lokasi\UTS_IR"
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Linux/macOS:

```bash
cd /lokasi/UTS_IR
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

Perintah berikut menggunakan `python`; ganti dengan path Python virtual environment
di atas jika environment belum diaktifkan. Instalasi membutuhkan internet, tetapi
indexing dan pencarian berjalan lokal tanpa internet.

## 2. Penggunaan CLI

```text
=== INFORMATION RETRIEVAL SYSTEM ===
[1] Load & Index Dataset
[2] Search Query
[3] Exit
====================================
```

Pilih 1 untuk membangun indeks pertama kali. Pilih 2, masukkan query bahasa
Indonesia atau Inggris, kemudian baca ID dokumen, dataset, judul, skor, dan cuplikan.
Pilih 3 untuk keluar. Setelah restart, menu 1 menggunakan cache jika tidak ada
perubahan isi CSV, kode preprocessing/engine, atau versi Python/pustaka utama.

Mode perintah langsung untuk demonstrasi dan otomasi:

```bash
python main.py index
python main.py search "pembelajaran matematika"
python main.py search "lagu anime Naruto" --top-k 5
python main.py search "pesawat" --source tempo --json
python main.py stats
python main.py index --rebuild
python main.py --data-dir "D:/data/datasets" --cache-dir "D:/data/cache" index
```

Opsi global `--data-dir` dan `--cache-dir` ditempatkan **sebelum** subperintah.
Query diperlakukan sebagai teks biasa, bukan sintaks Boolean, wildcard, atau frasa.
Semua token query menggunakan OR untuk mengambil kandidat. Pengulangan kata tetap
berpengaruh pada frekuensi vektor query. Filter sumber membatasi kandidat tanpa
mengubah kosakata global. Query kosong, stopword saja, atau di luar kosakata
menghasilkan daftar kosong dengan pesan yang jelas.

## 3. Struktur proyek

```text
UTS_IR/
  main.py                    Menu interaktif dan argumen CLI
  ir_system/
    engine.py                CSV, cache, Whoosh, BoW, cosine
    preprocessing.py         Normalisasi dan daftar stopword
  datasets/
    etd-usk/etd_usk.csv
    etd-ugm/etd_ugm.csv
    kompas/kompas.csv
    tempo/tempo.csv
    mojok/mojok.csv
  tests/test_engine.py       Uji otomatis menggunakan dataset sintetis
  evaluate.py               Eksperimen pada seluruh dataset asli
  results/                  Bukti pengujian dan contoh keluaran CLI
  docs/                     Penjelasan dan sumber teks laporan
  Laporan_UTS_IR.pdf
  requirements.txt
  README.md
```

`cache/` dibuat saat program dijalankan dan sengaja tidak disertakan dalam ZIP.
CSV asli disertakan tanpa perubahan. Input wajib UTF-8 (BOM diterima), kolom
`judul,konten`, dengan quoting CSV yang benar untuk koma dan baris baru.
ID stabil berbentuk `dataset:nomor_rekaman` (header tidak dihitung; bukan nomor
baris fisik CSV). Rekaman tanpa token informatif dilewati dan dihitung. Rekaman
duplikat dihitung tetapi dipertahankan untuk menjaga keterlacakan data sumber.

## 4. Desain dan rumus

1. Case folding; hapus tag HTML; ubah entitas HTML; tokenisasi rangkaian huruf;
   buang token satu huruf dan stopword Indonesia/Inggris dari daftar eksplisit.
   Angka diabaikan. Tidak ada stemming atau pembetulan ejaan.
2. Gabungkan `judul + konten` dengan bobot setara, sekali preprocessing per dokumen.
3. Simpan token dalam inverted index Whoosh dan teks asli sebagai stored fields.
4. `CountVectorizer` menghasilkan matriks sparse CSR berisi frekuensi mentah.
   Tidak ada TF-IDF, normalisasi tambahan, atau penggandaan bobot judul.
5. Whoosh mengambil **semua** kandidat dengan minimal satu token query yang ada
   dalam kosakata. BM25 Whoosh tidak digunakan untuk ranking atau cutoff kandidat.
6. `cosine_similarity(q, X[kandidat])`, urut skor menurun, lalu ID menaik jika seri.

`cos(q,d) = sum(q_i * d_i) / (sqrt(sum(q_i^2)) * sqrt(sum(d_i^2)))`

Contoh `q = [1,0]` dan `d = [2,1]` memberikan skor `2/sqrt(5) = 0.894427`.
Semua dokumen tanpa token bersama memiliki dot product nol. Karena itu mengambil
seluruh posting OR mempertahankan semua hasil dengan cosine positif dan
memberikan top-k yang sama dengan pencarian cosine ke seluruh korpus.
Jika hasil positif kurang dari lima, sistem hanya menampilkan hasil yang ada.
Skor cosine menyatakan kedekatan vektor kata, bukan probabilitas relevansi.

## 5. Kecepatan, cache, dan pemulihan

Tidak ada stemming per token, pemrosesan ulang saat tiap query, atau konversi
matriks dokumen ke bentuk dense. Indeks dan BoW disimpan setelah build berhasil.
Setiap pembukaan cache memeriksa SHA-256 isi kelima CSV untuk mendeteksi perubahan;
langkah ini tetap membutuhkan pembacaan berkas, tetapi tanpa tokenisasi/indexing.
Hasil waktu aktual ada di laporan; kecepatan di komputer lain dapat berbeda.
Sediakan ruang disk dan RAM beberapa GB; seluruh teks bersih dan matriks masih
berada di memori saat build. Ini bukan implementasi out-of-core.

Publikasi pointer cache dilakukan secara atomik. Build yang gagal tidak mengganti
cache lama. `BUILD.lock` mencegah dua proses build bersamaan. Jika program mati
paksa, pastikan tidak ada proses indexing aktif, lalu hapus **hanya** `BUILD.lock`
dan ulangi build. Generasi cache lama tidak dibersihkan otomatis; untuk menghemat
disk, tutup semua proses program lalu hapus folder `cache/` dan bangun ulang.
Cache memakai pickle: gunakan hanya cache yang dibuat sendiri, jangan unduh cache
dari pihak lain. Setelah pindah versi Python/scikit-learn, bangun ulang cache.

Jika `ModuleNotFoundError`, jalankan pip melalui interpreter yang sama dengan
program (`python -m pip ...`). Jika kolom CSV salah atau dataset kurang, pesan
menunjukkan berkas terkait. `--rebuild` memaksa pembuatan ulang. Tidak ada proses
scraping, klaim hak cipta dataset, atau pengiriman dokumen ke layanan eksternal.

## 6. Pengujian dan reproduksi

```bash
python -m unittest discover -s tests -v
python evaluate.py
python main.py search "Xiaomi kacamata pintar" --json
```

Unit test memeriksa nilai cosine manual, kesamaan ranking dengan cosine seluruh
korpus, preprocessing, query kosong/OOV, filter sumber, cache reuse/invalidation,
validasi CSV dan parameter, serta pengabaian rekaman kosong. `evaluate.py`
menjalankan sembilan query, mengukur median lima pencarian per query dan tiga
pemuatan cache, serta membandingkan enam query nonkosong dengan cosine seluruh
49 ribu dokumen. Pengukuran pencarian tidak termasuk pemuatan cache/interpreter.
Tidak ada ground truth penilaian relevansi, sehingga Precision@5, Recall, dan MAP
tidak diklaim. Contoh query spesifik digunakan sebagai sanity check dan bukan
bukti kualitas pada seluruh kemungkinan query.

## 7. Penyelesaian identitas dan pengumpulan

Identitas anggota dan nomor kelompok belum diberikan. Isi bagian identitas pada
`docs/IDENTITAS_TIM.md` dan cover laporan sebelum dikumpulkan. Pembagian peran di
berkas itu merupakan usulan, bukan pernyataan kontribusi yang sudah dilakukan.
Nama ZIP sementara memakai `NoKelompok`; ubah sesuai nomor kelompok, misalnya
`01 UTS Praktikum PI.zip`. Tinjau kode bersama tim dan sesuaikan dengan kebijakan
mata kuliah mengenai bantuan AI. Laporan PDF mengikuti cover, pendahuluan, desain
sistem, implementasi, pengujian query, dan kesimpulan.
