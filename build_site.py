import os
import re
from datetime import datetime

# Configurazione percorsi
FOLDER_CONTENTS = "contents"
FOLDER_POSTS = "posts"
FOLDER_TEMPLATES = "templates"
TEMPLATE_BASE = os.path.join(FOLDER_TEMPLATES, "base.html")
TEMPLATE_NAVBAR = os.path.join(FOLDER_TEMPLATES, "navbar.html")
TEMPLATE_FOOTER = os.path.join(FOLDER_TEMPLATES, "footer.html")

SITE_NAME = "Sabbia Ponderata"

def page_title(page):
    """Compone il titolo di una pagina nel formato 'Nome Sito | Pagina'"""
    return f"{SITE_NAME} | {page}"

def parse_markdown(file_path):
    """Legge un file md con frontmatter YAML (--- ... ---) ed estrae titolo, data e contenuto HTML"""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    title = "Senza Titolo"
    date = "0000-00-00"
    tags = []
    content_lines = []
    
    # Frontmatter in stile YAML (--- ... ---) con title:/date:
    if not (lines and lines[0].strip() == "---"):
        raise ValueError(f"Frontmatter YAML mancante in {file_path}: il file deve iniziare con '---'")
    
    metadata_done = False
    for line in lines[1:]:
        if not metadata_done:
            if line.strip() == "---":
                metadata_done = True
                continue
            elif line.startswith("title:"):
                title = line.split("title:", 1)[1].strip().strip('"')
                continue
            elif line.startswith("date:"):
                date = line.split("date:", 1)[1].strip()
                continue
            elif line.startswith("tags:"):
                raw = line.split("tags:", 1)[1].strip()
                if raw.startswith("[") and raw.endswith("]"):
                    raw = raw[1:-1]
                tags = [t.strip().strip('"').strip("'") for t in raw.split(",") if t.strip()]
                continue
        content_lines.append(line)
        
    text = "".join(content_lines)

    # Conversione spartana da Markdown a HTML (Grassetto, Link, Citazioni, Highlight e Immagini)
    def inline(text):
        text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"==(.*?)==", r"<mark>\1</mark>", text)
        text = re.sub(r"!\[(.*?)\]\((.*?)\)", r'<img src="\2" alt="\1">', text)
        text = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2">\1</a>', text)
        return text

    # Divide in blocchi basandosi sulle righe vuote
    blocks = [b for b in text.split("\n\n") if b.strip()]

    def to_list(lines, ordered):
        """Converte righe markdown (- o 1.) in una lista HTML"""
        tag = "ol" if ordered else "ul"
        items = "".join(
            f"<li>{inline(re.sub(r'^\s*(?:[-*]|\d+\.)\s+', '', line))}</li>" for line in lines
        )
        return f"<{tag}>{items}</{tag}>"

    html_parts = []
    for block in blocks:
        lines = [l.strip() for l in block.split("\n") if l.strip()]

        # Titolo: riga unica che inizia con uno o più "#"
        heading = re.match(r"^(#{1,3})\s+(.*)$", lines[0])
        if heading and len(lines) == 1:
            level = len(heading.group(1))
            html_parts.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
            continue

        if all(l.startswith(">") for l in lines):
            # Citazione: righe che iniziano con ">"
            quote_text = " ".join(re.sub(r"^>\s?", "", l) for l in lines)
            html_parts.append(f"<blockquote><p>{inline(quote_text)}</p></blockquote>")
        elif all(re.match(r"^[-*]\s+", l) for l in lines):
            # Lista non ordinata: righe che iniziano con - o *
            html_parts.append(to_list(lines, ordered=False))
        elif all(re.match(r"^\d+\.\s+", l) for l in lines):
            # Lista ordinata: righe che iniziano con un numero seguito da punto
            html_parts.append(to_list(lines, ordered=True))
        else:
            html_parts.append(f"<p>{inline(block.strip())}</p>")
    html_content = "".join(html_parts)
    
    # Crea un estratto di testo pulito per le anteprime della home/blog
    raw_text = re.sub('<[^<]+?>', ' ', html_content)
    excerpt = " ".join(raw_text.split())[:300] + "..."
    
    return {
        "title": title,
        "date": date,
        "content": html_content,
        "excerpt": excerpt,
        "tags": tags,
        "filename": re.sub(r"^\d{4}-\d{2}-\d{2}-", "", os.path.basename(file_path)).replace(".md", ".html")
    }

def format_date(date_str):
    """Converte una data ISO (YYYY-MM-DD) nel formato italiano leggibile"""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return date_str
    months = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
              "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]
    return f"{d.day} {months[d.month - 1]} {d.year}"

def time_tag(date_str):
    """Rende una data conforme allo standard HTML usando il tag <time>"""
    return f'<time datetime="{date_str}">{format_date(date_str)}</time>'

def render_tags(tags):
    """Rende i tag di un post come testo minimale sotto la data"""
    if not tags:
        return ""
    label = "; ".join(f'<span class="tag">{tag}</span>' for tag in tags)
    return f'<p class="post-tags"><small>{label}</small></p>'

def fix_links_for_home(text):
    """
    Se l'utente scrive un link nel markdown pensato per stare dentro /posts/ (es. ../about.html),
    lo corregge rimuovendo il '../' perché nella Home/Blog ci troviamo nella radice.
    """
    return text.replace('href="../', 'href="')

def fix_links_for_post(text):
    """
    Se l'utente scrive un link o un'immagine nel markdown pensati per la radice
    (es. images/foto.png o about.html), li corregge aggiungendo '../' perché le
    singole pagine dei post sono dentro la cartella /posts/.
    """
    # Aggiunge ../ solo se il riferimento non inizia già con http, https, ../ o mailto
    def replacer(match):
        attr, url = match.group(1), match.group(2)
        if url.startswith(('http://', 'https://', '../', 'mailto:')):
            return match.group(0)
        return f'{attr}="../{url}"'

    return re.sub(r'(href|src)="([^"]+)"', replacer, text)

def main():
    # 1. Carica template base e partials (navbar, footer)
    if not os.path.exists(TEMPLATE_BASE):
        print(f"Errore: Manca il file {TEMPLATE_BASE}")
        return
    with open(TEMPLATE_BASE, "r", encoding="utf-8") as f:
        template = f.read()
    with open(TEMPLATE_NAVBAR, "r", encoding="utf-8") as f:
        navbar = f.read().format(site_name=SITE_NAME)
    with open(TEMPLATE_FOOTER, "r", encoding="utf-8") as f:
        footer = f.read().format(site_name=SITE_NAME, year=datetime.now().year, privacy_link="privacy.html")

    def render_page(title, content, navbar_html, css_path, footer_html=None):
        """Compone una pagina completa dagli elementi condivisi"""
        return template.format(title=title, content=content,
                               navbar=navbar_html, footer=footer_html or footer,
                               css_path=css_path)

    # Navbar adattata per i file dentro la cartella /posts
    posts_navbar = navbar.replace('href="index.html"', 'href="../index.html"')
    posts_navbar = posts_navbar.replace('href="blog.html"', 'href="../blog.html"')
    posts_navbar = posts_navbar.replace('href="about.html"', 'href="../about.html"')
    posts_navbar = posts_navbar.replace('src="logo.png"', 'src="../logo.png"')

    # Footer adattato per i file dentro la cartella /posts
    posts_footer = footer.replace('href="privacy.html"', 'href="../privacy.html"')

    # 2. Elabora tutti i file Markdown nella cartella contents (escluso about.md)
    posts = []
    if os.path.exists(FOLDER_CONTENTS):
        for file in os.listdir(FOLDER_CONTENTS):
            if file in ("about.md", "privacy.md") or not file.endswith(".md"):
                continue
            file_path = os.path.join(FOLDER_CONTENTS, file)
            post_data = parse_markdown(file_path)
            posts.append(post_data)
                
    # Ordina i post dal più recente al più vecchio
    posts.sort(key=lambda x: x["date"], reverse=True)

# 3. Genera le pagine singole degli articoli (dentro la cartella posts/)
    os.makedirs(FOLDER_POSTS, exist_ok=True)
    for post in posts:
        # Corregge i link interni presenti nel testo del post
        post_content_fixed = fix_links_for_post(post['content'])

        article_html = f"<article><h1>{post['title']}</h1><p><small>Pubblicato il: {time_tag(post['date'])}</small></p>{render_tags(post['tags'])}{post_content_fixed}</article>"
        full_page = render_page(page_title(post["title"]), article_html, posts_navbar, "../style.css", posts_footer)

        output_path = os.path.join(FOLDER_POSTS, post["filename"])
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_page)
        print(f"Generato articolo: {output_path}")

# 4. Genera la HOMEPAGE (index.html) con gli ultimi 5 post
    home_content = '<section aria-labelledby="latest-posts-title"><h1 id="latest-posts-title">Post più recenti</h1>'
    for post in posts[:5]:
        excerpt_clean = fix_links_for_home(post['excerpt'])

        home_content += f"""
        <article>
            <h2>{post['title']}</h2>
            <p><small>Pubblicato il: {time_tag(post['date'])}</small></p>
            {render_tags(post['tags'])}
            <p>{excerpt_clean}</p>
            <a href="{FOLDER_POSTS}/{post['filename']}">Leggi di più</a>
        </article>"""
    home_content += '</section>'
    
    home_page = render_page(page_title("Home"), home_content, navbar, "style.css")
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(home_page)
    print("Generata Homepage: index.html")

# 5. Genera la pagina BLOG (blog.html) con tutti i post
    blog_content = '<section aria-labelledby="blog-title"><h1 id="blog-title">Tutti i Post</h1>'
    for post in posts:
        excerpt_clean = fix_links_for_home(post['excerpt'])

        blog_content += f"""
        <article>
            <h2>{post['title']}</h2>
            <p><small>Pubblicato il: {time_tag(post['date'])}</small></p>
            {render_tags(post['tags'])}
            <p>{excerpt_clean}</p>
            <a href="{FOLDER_POSTS}/{post['filename']}">Leggi di più</a>
        </article>"""
    blog_content += '</section>'
    
    blog_page = render_page(page_title("Blog"), blog_content, navbar, "style.css")
    with open("blog.html", "w", encoding="utf-8") as f:
        f.write(blog_page)
    print("Generata pagina Blog: blog.html")

    # 6. Genera la pagina ABOUT (about.html) dal sorgente contents/about.md
    about_file = os.path.join(FOLDER_CONTENTS, "about.md")
    if os.path.exists(about_file):
        about_data = parse_markdown(about_file)
        about_body = re.sub(r"^<h1>.*?</h1>", "", about_data["content"], count=1)
        about_content = f'<section aria-labelledby="about-title"><h1 id="about-title">{about_data["title"]}</h1><article>{about_body}</article></section>'
        about_page = render_page(page_title(about_data["title"]), about_content, navbar, "style.css")
        with open("about.html", "w", encoding="utf-8") as f:
            f.write(about_page)
        print("Generata pagina About: about.html")

    # 7. Genera la pagina PRIVACY (privacy.html) dal sorgente contents/privacy.md
    privacy_file = os.path.join(FOLDER_CONTENTS, "privacy.md")
    if os.path.exists(privacy_file):
        privacy_data = parse_markdown(privacy_file)
        privacy_body = re.sub(r"^<h1>.*?</h1>", "", privacy_data["content"], count=1)
        privacy_meta = f'<p class="page-meta"><small>Ultimo aggiornamento: {time_tag(privacy_data["date"])}</small></p>'
        privacy_content = f'<section aria-labelledby="privacy-title"><h1 id="privacy-title">{privacy_data["title"]}</h1><article>{privacy_meta}{privacy_body}</article></section>'
        privacy_page = render_page(page_title(privacy_data["title"]), privacy_content, navbar, "style.css")
        with open("privacy.html", "w", encoding="utf-8") as f:
            f.write(privacy_page)
        print("Generata pagina Privacy: privacy.html")

if __name__ == "__main__":
    main()
