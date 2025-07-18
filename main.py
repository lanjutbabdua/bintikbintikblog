import requests
import os
import re
import json
import datetime
import time
import random
import markdown
import base64 # Diperlukan untuk Basic Auth Application Password

# --- Konfigurasi Sumber WordPress Self-Hosted ---
API_BASE_URL_SELF_HOSTED = "https://sexcerita.com/wp-json/wp/v2/posts"

# --- Konfigurasi Tujuan WordPress.com ---
# Ganti dengan blog identifier WordPress.com kamu
# Contoh: "bintikbintikblog.wordpress.com" atau "yourcustomdomain.com"
WORDPRESS_COM_BLOG_IDENTIFIER = "bintikbintikblog.wordpress.com"

# Endpoint untuk publikasi ke WordPress.com. Akan dibentuk dengan WORDPRESS_COM_BLOG_IDENTIFIER
WORDPRESS_COM_PUBLISH_BASE_URL = "https://public-api.wordpress.com/rest/v1.1/sites/"

# --- Konfigurasi File State & Gambar Acak ---
STATE_FILE = 'published_posts.json' # File untuk melacak postingan yang sudah diterbitkan
RANDOM_IMAGES_FILE = 'random_images.json' # File untuk URL gambar acak
RANDOM_LINKS_FILE = 'random_links.json' # File BARU untuk URL dan teks tautan acak

# --- Penggantian Kata Khusus ---
REPLACEMENT_MAP = {
    "memek": "serambi lempit",
    "kontol": "rudal",
    "ngentot": "menggenjot",
    "vagina": "serambi lempit",
    "penis": "rudal",
    "seks": "bercinta",
    "mani": "kenikmatan",
    "sex": "bercinta"
}

# === Utilitas ===

def insert_more_tag(content_html, word_limit=100):
    """
    Menyisipkan tag <!--more--> di sekitar batas kata yang ditentukan dalam konten HTML.
    Akan mencari lokasi yang "aman" seperti setelah tag penutup paragraf atau baris baru.
    """
    words = content_html.split()
    if len(words) <= word_limit:
        return content_html # Tidak perlu menyisipkan jika konten terlalu pendek

    preview_content = " ".join(words[:word_limit])
    
    insert_pos = -1
    
    # Prioritaskan untuk menyisipkan setelah penutup tag paragraf jika ada di sekitar batas
    match = re.search(r'<\/p>', preview_content)
    if match:
        insert_pos = content_html.find(match.group(0), 0, len(preview_content)) + len(match.group(0))
    else:
        # Jika tidak ada paragraf penutup, cari spasi terdekat setelah batas kata
        space_after_limit = content_html.find(' ', len(preview_content)) 
        if space_after_limit != -1:
            insert_pos = space_after_limit
        else:
            insert_pos = len(preview_content) # Fallback: potong di akhir kata ke-100

    if insert_pos != -1:
        return content_html[:insert_pos].strip() + "\n\n<!--more-->\n\n" + content_html[insert_pos:].strip()
        
    return content_html # Fallback jika gagal menyisipkan dengan rapi

def wrap_content_in_details_tag(content_html, article_url, article_title, word_limit=700, random_link_data=None):
    """
    Menyisipkan tag <details> dan <summary> untuk menyembunyikan sisa konten
    setelah batas kata yang ditentukan, dengan tautan URL dan judul artikel di summary.
    Menggunakan random_link_data jika tersedia, jika tidak, fallback ke shrinkearn.com.
    """
    words = content_html.split()
    if len(words) <= word_limit:
        return content_html # Tidak perlu menyembunyikan jika konten terlalu pendek

    # Cari posisi karakter untuk word_limit
    temp_preview_words = " ".join(words[:word_limit])
    insert_point_char = len(temp_preview_words)
    
    # Pastikan kita tidak memotong tag HTML atau kata
    safe_insert_pos = -1
    
    # Coba cari tag penutup paragraf atau div di sekitar batas kata
    # Batasi pencarian agar tidak terlalu jauh
    search_end_pos = min(len(content_html), insert_point_char + 200) # Cari dalam 200 karakter berikutnya
    match = re.search(r'(<\/\w+>)\s*(<\w+[^>]*>)?', content_html[insert_point_char:search_end_pos], re.IGNORECASE)
    
    if match:
        safe_insert_pos = content_html.find(match.group(0), insert_point_char) + len(match.group(0))
    else:
        # Jika tidak ada paragraf penutup, cari spasi terdekat setelah batas kata
        space_pos = content_html.find(' ', insert_point_char)
        if space_pos != -1:
            safe_insert_pos = space_pos
        else:
            safe_insert_pos = insert_point_char # Fallback: potong di akhir karakter ke-700
    
    if safe_insert_pos != -1:
        part_before_details = content_html[:safe_insert_pos].strip()
        part_inside_details = content_html[safe_insert_pos:].strip()
        
        # Bentuk teks summary sesuai permintaan
        # Escape HTML entities di judul untuk mencegah masalah rendering
        escaped_title = article_title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#039;')
        
        # Logika baru untuk memilih random link atau fallback
        if random_link_data and 'url' in random_link_data and 'anchor_text' in random_link_data:
            chosen_url = random_link_data['url']
            chosen_anchor_text = random_link_data['anchor_text']
            # Gabungkan anchor text dari JSON dengan judul artikel
            final_anchor_text = f"{chosen_anchor_text}: {escaped_title}"
            details_summary_html = f"<summary>Lanjut BAB 2 di situs: <a href='{chosen_url}' target='_blank'>{final_anchor_text}</a></summary>"
            print(f"🔗 Menggunakan tautan acak: {chosen_url} dengan teks '{final_anchor_text}'")
        else:
            # Fallback ke link shrinkearn.com jika tidak ada random link yang tersedia atau format salah
            print("⚠️ Tidak ada tautan acak yang tersedia atau formatnya salah. Menggunakan tautan fallback (shrinkearn.com).")
            details_summary_html = f"<summary>Lanjut bab 2: <a href='https://ceritarunplace.blogspot.com/' target='_blank'>{escaped_title}</a></summary>"
        
        # Gabungkan semua bagian
        return (
            f"{part_before_details}\n"
            f"<details>{details_summary_html}\n"
            f"<div id=\"lanjut\">\n{part_inside_details}\n</div>\n"
            f"</details>\n"
        )
    
    return content_html # Fallback jika gagal menyisipkan dengan rapi


def extract_first_image_url(html_content):
    """
    Mencari URL gambar pertama di dalam konten HTML.
    """
    match = re.search(r'<img[^>]+src="([^"]+)"', html_content, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def strip_html_and_divs(html):
    """
    Menghapus sebagian besar tag HTML, kecuali yang esensial,
    dan mengganti </p> dengan dua newline untuk pemisahan paragraf.
    """
    html_with_newlines = re.sub(r'</p>', r'\n\n', html, flags=re.IGNORECASE)
    html_no_images = re.sub(r'<img[^>]*>', '', html_with_newlines)
    html_no_divs = re.sub(r'</?div[^>]*>', '', html_no_images, flags=re.IGNORECASE)
    clean_text = re.sub('<[^<]+?>', '', html_no_divs)
    clean_text = re.sub(r'\n{3,}', r'\n\n', clean_text).strip()
    return clean_text

def remove_anchor_tags(html_content):
    """Menghapus tag <a> tapi mempertahankan teks di dalamnya."""
    return re.sub(r'<a[^>]*>(.*?)<\/a>', r'\1', html_content)

def sanitize_filename(title):
    """Membersihkan judul agar cocok untuk nama file."""
    clean_title = re.sub(r'[^\w\s-]', '', title).strip().lower()
    return re.sub(r'[-\s]+', '-', clean_title)

def replace_custom_words(text):
    """Menerapkan penggantian kata khusus pada teks."""
    processed_text = text
    sorted_replacements = sorted(REPLACEMENT_MAP.items(), key=lambda item: len(item[0]), reverse=True)
    for old_word, new_word in sorted_replacements:
        pattern = re.compile(re.escape(old_word), re.IGNORECASE)
        processed_text = pattern.sub(new_word, processed_text)
    return processed_text

# --- Fungsi untuk memuat dan menyimpan status postingan yang sudah diterbitkan ---
def load_published_posts_state():
    """Memuat ID postingan yang sudah diterbitkan dari file state."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            try:
                return set(json.load(f))
            except json.JSONDecodeError:
                print(f"Warning: {STATE_FILE} is corrupted or empty. Starting with an empty published posts list.")
                return set()
    return set()

def save_published_posts_state(published_ids):
    """Menyimpan ID postingan yang sudah diterbitkan ke file state."""
    with open(STATE_FILE, 'w') as f:
        json.dump(list(published_ids), f)

def load_image_urls(file_path):
    """
    Memuat daftar URL gambar dari file JSON.
    """
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                urls = json.load(f)
                if isinstance(urls, list) and all(isinstance(url, str) for url in urls):
                    print(f"✅ Berhasil memuat {len(urls)} URL gambar dari '{file_path}'.")
                    return urls
                else:
                    print(f"❌ Error: Konten '{file_path}' bukan daftar string URL yang valid.")
                    return []
            except json.JSONDecodeError:
                print(f"❌ Error: Gagal mengurai JSON dari '{file_path}'. Pastikan formatnya benar.")
                return []
    else:
        print(f"⚠️ Peringatan: File '{file_path}' tidak ditemukan. Tidak ada gambar acak yang akan ditambahkan.")
        return []

def get_random_image_url(image_urls):
    """
    Memilih URL gambar secara acak dari daftar.
    """
    if image_urls:
        return random.choice(image_urls)
    return None

def load_random_links(file_path):
    """
    Memuat daftar objek tautan (url, anchor_text) dari file JSON.
    """
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                links = json.load(f)
                if isinstance(links, list) and all(isinstance(item, dict) and 'url' in item and 'anchor_text' in item for item in links):
                    print(f"✅ Berhasil memuat {len(links)} URL dan teks tautan acak dari '{file_path}'.")
                    return links
                else:
                    print(f"❌ Error: Konten '{file_path}' bukan daftar kamus URL/anchor_text yang valid.")
                    return []
            except json.JSONDecodeError:
                print(f"❌ Error: Gagal mengurai JSON dari '{file_path}'. Pastikan formatnya benar.")
                return []
    else:
        print(f"⚠️ Peringatan: File '{file_path}' tidak ditemukan. Tidak ada tautan acak yang akan ditambahkan.")
        return []

def get_random_link_data(link_list):
    """
    Memilih satu objek tautan (url dan anchor_text) secara acak dari daftar.
    """
    if link_list:
        return random.choice(link_list)
    return None

# --- Penerbitan Artikel ke WordPress.com (Menggunakan Application Password) ---

def publish_post_to_wordpress_com(blog_identifier, title, content_html, categories=None, tags=None, random_image_url=None, article_url_for_details=None, article_title_for_details=None, selected_random_link_data=None):
    """
    Menerbitkan postingan ke WordPress.com menggunakan Application Password.
    Username dan Application Password diambil dari environment variables.
    """
    print(f"🚀 Menerbitkan '{title}' ke WordPress.com menggunakan Application Password...")

    # Ambil username dan Application Password dari environment variables
    wp_username = os.getenv('WP_USERNAME')
    wp_app_password = os.getenv('WP_APP_PASSWORD')

    if not wp_username or not wp_app_password:
        print("❌ Error: WP_USERNAME atau WP_APP_PASSWORD tidak ditemukan di environment variables.")
        print("Pastikan Anda sudah menyetelnya sebagai GitHub Secrets.")
        return None

    # Bentuk string untuk Basic Authentication: 'username:application_password'
    auth_string = f"{wp_username}:{wp_app_password}"
    # Encode ke Base64
    encoded_auth_string = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')

    publish_url = f"{WORDPRESS_COM_PUBLISH_BASE_URL}{blog_identifier}/posts/new"

    headers = {
        'Authorization': f'Basic {encoded_auth_string}',
        'Content-Type': 'application/json',
        'User-Agent': 'WordPress-to-WPcom-Migrator/1.0'
    }

    # Inisialisasi bagian konten tambahan
    additional_content_parts = []

    # Tambahkan gambar acak di awal konten jika ada
    if random_image_url:
        image_html = f'<p style="text-align: center;"><img src="{random_image_url}" alt="{title}" style="max-width: 100%; height: auto; display: block; margin: 0 auto; border-radius: 8px;"></p>'
        additional_content_parts.append(image_html)
        print(f"🖼️ Gambar acak '{random_image_url}' ditambahkan.")

    # Tambahkan teks "Bintikbintikblog - judul artikel"
    blog_title_header = f'<p><strong>Bintikbintikblog</strong> - {title}</p>'
    additional_content_parts.append(blog_title_header)
    print(f"📝 Header 'Bintikbintikblog - {title}' ditambahkan.")

    # Gabungkan semua bagian tambahan dengan konten utama
    full_content = "\n".join(additional_content_parts) + "\n" + content_html
    
    # SISIPKAN <!--more--> TAG
    content_after_more_tag = insert_more_tag(full_content, word_limit=100)
    
    # SISIPKAN <details> dengan potensi random link
    final_content_for_publish = wrap_content_in_details_tag(
        content_after_more_tag, 
        article_url=article_url_for_details, 
        article_title=article_title_for_details, 
        word_limit=700,
        random_link_data=selected_random_link_data # Meneruskan data link acak
    )
    
    payload = {
        'title': title,
        'content': final_content_for_publish, 
        'status': 'publish'
    }

    if categories:
        payload['categories'] = categories 
    if tags:
        payload['tags'] = tags

    try:
        response = requests.post(publish_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        response_data = response.json()
        print(f"✅ Artikel '{title}' berhasil diterbitkan ke WordPress.com! URL: {response_data.get('URL')}")
        return response_data
    except requests.exceptions.RequestException as e:
        print(f"❌ Gagal menerbitkan artikel '{title}' ke WordPress.com: {e}")
        if response.status_code == 409:
            print("Peringatan: Mungkin artikel ini sudah ada di WordPress.com (konflik slug). Coba cek secara manual.")
        elif response.status_code == 401:
            print("Kesalahan 401 Unauthorized: Application Password atau Username mungkin salah. Pastikan GitHub Secrets sudah benar dan Application Password tidak mengandung spasi.")
        print(f"Respons Error Lengkap: {response.text}")
        return None

# --- Pengambilan Artikel dari WordPress Self-Hosted (Sumber) ---

def fetch_all_and_process_posts_from_self_hosted():
    """
    Mengambil semua postingan dari WordPress self-hosted REST API, membersihkan HTML,
    dan menerapkan penggantian kata khusus.
    """
    all_posts_raw = []
    page = 1
    per_page_limit = 100

    print("📥 Mengambil semua artikel dari WordPress self-hosted REST API...")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    while True:
        params = {
            'per_page': per_page_limit,
            'page': page,
            'status': 'publish',
            '_fields': 'id,title,content,excerpt,categories,tags,date,featured_media,link' # Tambahkan 'link' untuk URL sumber
        }
        try:
            res = requests.get(API_BASE_URL_SELF_HOSTED, params=params, headers=headers, timeout=30)
            
            if res.status_code == 400:
                if "rest_post_invalid_page_number" in res.text:
                    print(f"Reached end of posts from WordPress self-hosted API (page {page} does not exist). Stopping fetch.")
                    break
                else:
                    raise Exception(f"Error: Gagal mengambil data dari WordPress self-hosted REST API: {res.status_code} - {res.text}. "
                                     f"Pastikan URL API Anda benar dan dapat diakses.")
            elif res.status_code != 200:
                raise Exception(f"Error: Gagal mengambil data dari WordPress self-hosted REST API: {res.status_code} - {res.text}. "
                                   f"Pastikan URL API Anda benar dan dapat diakses.")

            posts_batch = res.json()

            if not posts_batch:
                print(f"Fetched empty batch on page {page}. Stopping fetch.")
                break

            all_posts_raw.extend(posts_batch)
            page += 1
            time.sleep(0.5)

        except requests.exceptions.Timeout:
            print(f"Timeout: Permintaan ke WordPress self-hosted API di halaman {page} habis waktu. Mungkin ada masalah jaringan atau server lambat.")
            break
        except requests.exceptions.RequestException as e:
            print(f"Network Error: Gagal terhubung ke WordPress self-hosted API di halaman {page}: {e}. Cek koneksi atau URL.")
            break

    processed_posts = []
    for post in all_posts_raw:
        original_title = post.get('title', {}).get('rendered', '')
        processed_title = replace_custom_words(original_title)
        post['processed_title'] = processed_title

        raw_content = post.get('content', {}).get('rendered', '')
        content_image_url = extract_first_image_url(raw_content)
        post['content_image_url'] = content_image_url

        content_no_anchors = remove_anchor_tags(raw_content)
        # Konten ini sudah dibersihkan dan diproses kata khusus
        cleaned_and_processed_content = replace_custom_words(strip_html_and_divs(content_no_anchors))

        post['raw_cleaned_content'] = cleaned_and_processed_content # Ini adalah konten yang akan digunakan
        post['id'] = post.get('id')
        post['source_link'] = post.get('link')

        # Dapatkan nama kategori dan tag
        category_names = [cat.get('name') for cat in post.get('categories', []) if isinstance(cat, dict) and 'name' in cat]
        tag_names = [tag.get('name') for tag in post.get('tags', []) if isinstance(tag, dict) and 'name' in tag]

        post['category_names'] = category_names
        post['tag_names'] = tag_names

        processed_posts.append(post)

    return processed_posts

# --- Eksekusi Utama ---

if __name__ == '__main__':
    print(f"[{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] Starting WordPress self-hosted to WordPress.com publishing process (One Article Per Day, Oldest Unpublished First).")
    print("🚀 Mengambil semua artikel WordPress self-hosted.")
    print("🤖 Fitur Pengeditan AI DINONAKTIFKAN.")
    print("🖼️ Mencoba mengambil gambar pertama dari konten artikel (untuk info).")
    print("📝 Menyisipkan <!--more--> tag di sekitar 100 kata pertama setiap artikel.") 
    print("🔽 Menyisipkan <details> dengan link judul artikel sumber (atau random link) setelah 700 kata pertama setiap artikel.") # Diperbarui di sini
    print("\n⚠️ HANYA SATU ARTIKEL TERLAMA YANG BELUM DITERBITKAN AKAN DIPROSES PER HARI.")

    # Pastikan semua variabel lingkungan penting sudah disetel
    wp_username = os.getenv('WP_USERNAME')
    wp_app_password = os.getenv('WP_APP_PASSWORD')

    if not all([wp_username, wp_app_password, WORDPRESS_COM_BLOG_IDENTIFIER]):
        print("❌ Error: Pastikan semua variabel lingkungan (WP_USERNAME, WP_APP_PASSWORD, WORDPRESS_COM_BLOG_IDENTIFIER) disetel di GitHub Secrets atau lingkungan lokal Anda.")
        exit(1)

    try:
        published_ids = load_published_posts_state()
        print(f"Ditemukan {len(published_ids)} postingan yang sudah diterbitkan sebelumnya.")

        random_image_urls = load_image_urls(RANDOM_IMAGES_FILE)
        selected_random_image = get_random_image_url(random_image_urls)
        if not selected_random_image:
            print("⚠️ Tidak ada URL gambar acak yang tersedia. Artikel akan diterbitkan tanpa gambar acak.")

        # Muat daftar link acak
        random_links_data_list = load_random_links(RANDOM_LINKS_FILE)
        selected_random_link_data = get_random_link_data(random_links_data_list)
        if not selected_random_link_data:
            print("⚠️ Tidak ada data tautan acak yang tersedia atau format file salah. Tautan fallback akan digunakan untuk <details>.")


        all_posts_preprocessed = fetch_all_and_process_posts_from_self_hosted()
        print(f"Total {len(all_posts_preprocessed)} artikel ditemukan dan diproses awal dari WordPress self-hosted API.")

        unpublished_posts = [post for post in all_posts_preprocessed if str(post['id']) not in published_ids]
        print(f"Ditemukan {len(unpublished_posts)} artikel yang belum diterbitkan.")

        if not unpublished_posts:
            print("\n🎉 Tidak ada artikel baru yang tersedia untuk diterbitkan hari ini. Proses selesai.")
            exit(0)

        # Urutkan dari yang TERLAMA ke TERBARU berdasarkan tanggal
        # Ini akan memastikan artikel yang paling tua (yang belum diterbitkan) diproses duluan
        unpublished_posts.sort(key=lambda x: datetime.datetime.fromisoformat(x['date'].replace('Z', '+00:00')), reverse=False)

        # Pilih satu postingan untuk diterbitkan hari ini (yang paling lama belum diterbitkan)
        post_to_publish = unpublished_posts[0]
        
        original_post_id = post_to_publish.get('id')
        processed_title = post_to_publish.get('processed_title')
        source_article_url = post_to_publish.get('link', '#') # Mengambil URL asli dari post

        # --- TANPA PENGEDITAN AI ---
        # Langsung gunakan konten yang sudah dibersihkan dan diproses dari self-hosted
        final_content_for_publish_markdown = post_to_publish['raw_cleaned_content']
        
        # Konversi konten Markdown ke HTML sebelum menyisipkan tag khusus dan publikasi
        final_content_for_publish_html = markdown.markdown(final_content_for_publish_markdown)

        print(f"\n🌟 Memproses dan menerbitkan artikel TERLAMA yang belum diterbitkan: '{processed_title}' (ID Sumber: {original_post_id})")

        published_response = publish_post_to_wordpress_com(
            WORDPRESS_COM_BLOG_IDENTIFIER,
            processed_title,
            final_content_for_publish_html, # Pastikan ini HTML
            categories=post_to_publish['category_names'], 
            tags=post_to_publish['tag_names'],           
            random_image_url=selected_random_image,
            article_url_for_details=source_article_url, 
            article_title_for_details=processed_title,
            selected_random_link_data=selected_random_link_data # Meneruskan data link acak
        )

        if published_response:
            print(f"✅ Artikel ID Sumber: {original_post_id} berhasil diterbitkan.")
            published_ids.add(str(original_post_id))
            save_published_posts_state(published_ids)
            print(f"✅ State file '{STATE_FILE}' diperbarui dengan ID: {original_post_id}.")
        else:
            print(f"❌ Gagal menerbitkan artikel ID Sumber: {original_post_id}. Tidak ditambahkan ke state file.")
            exit(1) # Keluar dengan error jika satu-satunya artikel gagal dipublikasikan

        print("\n--- Proses Satu Artikel Selesai ---")
        print("🎉 Proses berhasil memublikasikan 1 artikel baru (dari backlog).")

    except Exception as e:
        print(f"❌ Terjadi kesalahan fatal: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
