from flask import Flask, request, render_template, flash
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse
import json


app = Flask(__name__)
app.secret_key = "your_secret_key"  # Замените на ваш секретный ключ


def extract_metadata(url):
    """
    Извлекает метаданные с веб-страницы.
    """
    metadata = {}
    try:
        response = requests.get(url)
        response.raise_for_status()
        html = response.text
    except Exception as e:
        print(f"Ошибка при получении страницы: {e}")
        return {}

    soup = BeautifulSoup(html, 'html.parser')


    # 1. Заголовок
    title_tag = soup.find('meta', property='og:title')
    if title_tag and title_tag.get('content'):
        metadata['title'] = title_tag.get('content')
    elif soup.title:
        metadata['title'] = soup.title.string.strip()
    else:
        metadata['title'] = 'Неизвестное название'

    # 2. Автор (сначала пытаемся найти meta name="author")
    author_tag = soup.find('meta', attrs={'name': 'author'})
    if author_tag and author_tag.get('content'):
        metadata['author'] = author_tag.get('content')
    else:
        # Если meta name="author" нет, пробуем JSON-LD
        from_jsonld = extract_author_from_jsonld(soup)
        if from_jsonld:
            metadata['author'] = from_jsonld
        else:
            metadata['author'] = 'Неизвестный автор'

    # 3. Дата публикации (meta property="article:published_time")
    pub_date_tag = soup.find('meta', property='article:published_time')
    if pub_date_tag and pub_date_tag.get('content'):
        metadata['pub_date'] = pub_date_tag.get('content')[:10]  # формат YYYY-MM-DD
    else:
        metadata['pub_date'] = None

    # 4. Название сайта
    site_name_tag = soup.find('meta', property='og:site_name')
    if site_name_tag and site_name_tag.get('content'):
        metadata['site_name'] = site_name_tag.get('content')
    else:
        parsed_url = urlparse(url)
        metadata['site_name'] = parsed_url.netloc

    metadata['url'] = url
    metadata['access_date'] = datetime.now().strftime("%d.%m.%Y")

    return metadata

    # Извлечение заголовка
    title_tag = soup.find('meta', property='og:title')
    if title_tag and title_tag.get('content'):
        metadata['title'] = title_tag.get('content')
    elif soup.title:
        metadata['title'] = soup.title.string.strip()
    else:
        metadata['title'] = 'Неизвестное название'

    # Извлечение автора
    author_tag = soup.find('meta', attrs={'name': 'author'})
    if author_tag and author_tag.get('content'):
        metadata['author'] = author_tag.get('content')
    else:
        metadata['author'] = 'Неизвестный автор'

    # Извлечение даты публикации
    pub_date_tag = soup.find('meta', property='article:published_time')
    if pub_date_tag and pub_date_tag.get('content'):
        metadata['pub_date'] = pub_date_tag.get('content')[:10]  # формат YYYY-MM-DD
    else:
        metadata['pub_date'] = None

    # Извлечение названия сайта
    site_name_tag = soup.find('meta', property='og:site_name')
    if site_name_tag and site_name_tag.get('content'):
        metadata['site_name'] = site_name_tag.get('content')
    else:
        parsed_url = urlparse(url)
        metadata['site_name'] = parsed_url.netloc

    metadata['url'] = url
    metadata['access_date'] = datetime.now().strftime("%d.%m.%Y")

    return metadata


def extract_author_from_jsonld(soup: BeautifulSoup) -> str:
    """
    Пытается найти имя автора в JSON-LD (структурированных данных).
    Возвращает строку с именем автора или None, если не найдено.
    """
    scripts = soup.find_all('script', type='application/ld+json')
    for script_tag in scripts:
        # Содержимое тега <script type="application/ld+json"> может быть массивом JSON или объектом
        try:
            data = json.loads(script_tag.string)
        except (json.JSONDecodeError, TypeError):
            continue

        # Если data — это список, то нужно проверить каждый элемент
        if isinstance(data, list):
            for item in data:
                author_name = _parse_author_from_article(item)
                if author_name:
                    return author_name
        # Если data — это словарь
        elif isinstance(data, dict):
            author_name = _parse_author_from_article(data)
            if author_name:
                return author_name
    return None


def _parse_author_from_article(json_item) -> str:
    """
    Вспомогательная функция, которая извлекает имя автора,
    если json_item описывает статью.
    """
    if not isinstance(json_item, dict):
        return None
    # Проверяем, что это Article или NewsArticle
    if json_item.get('@type') in ('Article', 'NewsArticle', 'BlogPosting'):
        # author может быть строкой или объектом (например, {"@type": "Person", "name": "Автор"})
        author_data = json_item.get('author')
        if isinstance(author_data, dict):
            return author_data.get('name')
        elif isinstance(author_data, list):
            # Если авторов несколько
            names = []
            for author_obj in author_data:
                if isinstance(author_obj, dict):
                    names.append(author_obj.get('name', ''))
            return ', '.join(filter(None, names))
        elif isinstance(author_data, str):
            return author_data
    return None

def format_gost(metadata):
    """
    Формирует библиографическую запись по ГОСТу для электронного ресурса.
    Формат (упрощённо):

    АВТОР. НАЗВАНИЕ. – НАЗВАНИЕ САЙТА, ГОД. – [Электронный ресурс]. – URL: <ссылка> (Дата обращения: дд.мм.гггг).
    """
    author = metadata.get('author', 'Неизвестный автор')
    title = metadata.get('title', 'Неизвестное название')
    site_name = metadata.get('site_name', 'Неизвестный сайт')
    pub_date = metadata.get('pub_date')
    if pub_date:
        year = pub_date.split('-')[0]
    else:
        year = 'n.d.'  # no date
    url = metadata.get('url')
    access_date = metadata.get('access_date')

    citation = (f"{author}. {title}. – {site_name}, {year}. – [Электронный ресурс]. "
                f"– URL: {url} (Дата обращения: {access_date}).")
    return citation


@app.route('/', methods=['GET', 'POST'])
def index():
    citation = None
    if request.method == 'POST':
        url = request.form.get('url')
        if not url:
            flash("Пожалуйста, введите URL.", "error")
        else:
            metadata = extract_metadata(url)
            if not metadata:
                flash("Ошибка при извлечении метаданных. Проверьте правильность URL.", "error")
            else:
                citation = format_gost(metadata)
    return render_template('index.html', citation=citation)


if __name__ == '__main__':
    app.run(debug=True)
