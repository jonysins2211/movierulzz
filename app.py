from flask import Flask, Response
import requests
from bs4 import BeautifulSoup
import urllib.parse
import html
import re
import time

app = Flask(__name__)

# ✅ Featured Section URL
BASE_URL = "https://www.5movierulz.futbol/movies?sort=featured"

# ✅ Improved Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.5movierulz.futbol/",
    "Accept-Language": "en-US,en;q=0.9"
}

def extract_title_from_magnet(magnet_link):
    parsed_url = urllib.parse.urlparse(magnet_link)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    title = query_params.get('dn', ['Unknown Title'])[0]
    return title.replace('.', ' ')

def extract_resolution(title):
    match = re.search(r'(\d{3,4}p)', title)
    return match.group(1) if match else "Unknown Resolution"

def fetch_movie_links(movie_url):
    try:
        response = requests.get(movie_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    movie_links = []

    download_links = soup.find_all('a', class_='mv_button_css')

    for link in download_links:
        magnet_link = link.get('href')
        if not magnet_link or not magnet_link.startswith("magnet:"):
            continue

        size_tag = link.find('small')
        size_info = size_tag.text.strip() if size_tag else "Unknown Size"

        movie_title = extract_title_from_magnet(magnet_link)
        resolution = extract_resolution(movie_title)

        movie_links.append({
            "title": html.escape(movie_title),
            "magnet": html.escape(magnet_link),
            "size": html.escape(size_info),
            "resolution": html.escape(resolution)
        })

    return movie_links


@app.route("/rss", methods=["GET"])
def rss_feed():
    all_movies = []
    seen_magnets = set()

    # ✅ Fetch first 3 featured pages
    for page in range(1, 4):
        page_url = f"{BASE_URL}&page={page}"

        try:
            response = requests.get(page_url, headers=HEADERS, timeout=30)
            response.raise_for_status()
        except requests.RequestException:
            continue

        soup = BeautifulSoup(response.text, 'html.parser')
        movie_elements = soup.find_all('div', class_='boxed film')

        for movie in movie_elements:
            title_tag = movie.find('a')
            if not title_tag:
                continue

            movie_link = title_tag.get('href')
            if not movie_link:
                continue

            movie_links = fetch_movie_links(movie_link)

            for torrent in movie_links:
                if torrent["magnet"] not in seen_magnets:
                    seen_magnets.add(torrent["magnet"])
                    all_movies.append(torrent)

        # small delay to avoid blocking
        time.sleep(1)

    if not all_movies:
        return Response(
            "<?xml version='1.0' encoding='UTF-8'?><rss><channel><title>No Data</title></channel></rss>",
            mimetype="application/xml"
        )

    rss_items = ""

    for torrent in all_movies:
        rss_items += f"""
        <item>
            <title>{torrent['title']} ({torrent['resolution']})</title>
            <link>{torrent['magnet']}</link>
            <description>Size: {torrent['size']}</description>
        </item>
        """

    rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>5MovieRulz - Featured Torrents</title>
<link>{html.escape(BASE_URL)}</link>
<description>Latest Featured Movie Torrent Links</description>
{rss_items}
</channel>
</rss>"""

    return Response(rss_content, mimetype="application/xml")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
