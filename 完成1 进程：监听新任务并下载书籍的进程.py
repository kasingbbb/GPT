
import threading
import requests
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub
import urllib.parse
import redis
import re

# 任务队列
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def check_for_new_task():
    try:
        # 从 Redis 获取任务
        task = redis_client.rpop('task_queue')
        if task:
            return task.decode('utf-8')  # 如果任务是字节字符串，需要解码
    except redis.RedisError as e:
        print(f"Redis 错误: {e}")
        return None

def main():
    while True:
        task = check_for_new_task()
        if task:
            process_task(task)


def process_task(task):
    book_name = task
    handle_book_download(book_name)


# 获取链接的内容
def get_link(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup
    except requests.RequestException as e:
        print("请求错误:", e)
        return None


# 从搜索结果页面提取 EPUB 下载链接的函数
def extract_epub_links(search_url):
    try:
        response = requests.get(search_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        epub_links = []
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) > 9 and 'epub' in cells[8].text.lower():
                mirrors = cells[9].find_all('a')
                for mirror in mirrors:
                    if 'library.lol' in mirror['href'] or 'libgen.li' in mirror['href']:
                        epub_links.append(mirror['href'])
                        break
        return epub_links
    except requests.RequestException as e:
        print(f"请求出错: {e}")
        return []


# 将 EPUB 转换为文本的函数
def epub_to_text(file_path):
    book = epub.read_epub(file_path)
    text = []
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.content, 'html.parser')
            text.append(soup.get_text())
    return '\n'.join(text)


def sanitize_filename(name):
    """清理文件名，移除不合法字符"""
    return re.sub(r'[\\/*?:"<>|]', '', name)

def handle_book_download(book_name):
    # 清理书籍名称以创建安全的文件名
    safe_book_name = sanitize_filename(book_name)
    epub_file_name = f"{safe_book_name}.epub"
    txt_file_name = f"{safe_book_name}.txt"

    encoded_book_name = urllib.parse.quote(book_name)
    url = f"https://www.libgen.is/search.php?req={encoded_book_name}&open=0&res=25&view=simple&phrase=1&column=def"

    epub_links = extract_epub_links(url)
    download_successful = False

    for book_url in epub_links:
        if download_successful:
            break

        try:
            soup = get_link(book_url)
            if soup:
                download_div = soup.find('div', id='download')
                download_links = download_div.find_all('a') if download_div else []
                hrefs = [link.get('href') for link in download_links]

                for download_url in hrefs:
                    try:
                        response = requests.get(download_url)
                        response.raise_for_status()

                        with open(epub_file_name, 'wb') as file:
                            file.write(response.content)
                        print(f"电子书已保存到 '{epub_file_name}'，来源：{download_url}")

                        text_content = epub_to_text(epub_file_name)
                        with open(txt_file_name, 'w', encoding='utf-8') as text_file:
                            text_file.write(text_content)
                        print(f"EPUB文件已转换为文本并保存到 '{txt_file_name}'")

                        download_successful = True
                        break
                    except requests.RequestException as e:
                        print(f"从 {download_url} 下载失败:", e)
                        continue
        except Exception as e:
            print(f"处理链接 {book_url} 时出错: {e}")
            continue

    if not download_successful:
        print("所有链接都已尝试，但均未成功下载和处理。")



if __name__ == '__main__':
    main()
