name: Otomatisasi Publikasi Postingan WordPress

on:
  workflow_dispatch: # Memungkinkan Anda menjalankan workflow secara manual dari GitHub UI
  schedule:
    # Menjalankan setiap hari pada pukul 00:00 UTC (07:00 WIB)
    # Anda bisa mengubah jadwal ini sesuai kebutuhan dengan format cron:
    # menit (0-59) | jam (0-23) | hari-dalam-bulan (1-31) | bulan (1-12) | hari-dalam-minggu (0-6, Minggu=0 atau 7)
    - cron: '0 0 * * *' 

jobs:
  publish:
    runs-on: ubuntu-latest # Menggunakan runner Ubuntu terbaru

    steps:
    - name: Checkout Repository
      uses: actions/checkout@v4 # Mengambil kode dari repository Anda

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.x' # Menggunakan versi Python 3 terbaru

    - name: Create empty random_images.json if not exists
      run: |
        if [ ! -f random_images.json ]; then
          echo '[]' > random_images.json
          echo "random_images.json created as empty array."
        else
          echo "random_images.json already exists."
        fi
      # Penjelasan: Script Anda membutuhkan file ini. Ini akan membuat file kosong jika belum ada.
      # Anda disarankan mengisi file ini dengan daftar URL gambar untuk fitur gambar acak.

    - name: Create empty random_links.json if not exists
      run: |
        if [ ! -f random_links.json ]; then
          echo '[]' > random_links.json
          echo "random_links.json created as empty array."
        else
          echo "random_links.json already exists."
        fi
      # Penjelasan: Script Anda membutuhkan file ini. Ini akan membuat file kosong jika belum ada.
      # Anda disarankan mengisi file ini dengan daftar objek { "url": "...", "anchor_text": "..." } untuk tautan acak.

    - name: Cache Published Posts State
      uses: actions/cache@v4
      with:
        path: published_posts.json
        key: ${{ runner.os }}-published-posts-${{ github.run_id }} # Kunci unik untuk setiap run workflow
        restore-keys: |
          ${{ runner.os }}-published-posts- # Mencoba restore dari kunci sebelumnya

    - name: Install Dependencies
      run: pip install -r requirements.txt # Menginstal library Python yang diperlukan

    - name: Run Python Script
      env:
        WP_USERNAME: ${{ secrets.WP_USERNAME }} # Mengambil username dari GitHub Secrets
        WP_APP_PASSWORD: ${{ secrets.WP_APP_PASSWORD }} # Mengambil app password dari GitHub Secrets
      run: python main.py # Menjalankan skrip Python Anda

    - name: Save Published Posts State
      uses: actions/cache/save@v4
      with:
        path: published_posts.json
        key: ${{ runner.os }}-published-posts-${{ github.run_id }}
      # Penjelasan: Ini akan menyimpan kembali file 'published_posts.json'
      # agar status postingan yang sudah diterbitkan tetap tersimpan untuk run berikutnya.
      # File ini penting untuk melacak postingan yang sudah dipublikasi.
      # Pastikan ini hanya dijalankan jika ada perubahan pada file state.
      if: success() || failure() # Selalu coba simpan cache terlepas dari hasil langkah sebelumnya
