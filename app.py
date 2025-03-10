from flask import Flask, request, render_template
import requests , string
from bs4 import BeautifulSoup
import re
import html
import time
import sqlite3
import os

app = Flask(__name__)


DB_PATH = os.path.join('instance', 'bible_titles.db')


# 创建数据库连接和表
def init_db():
    DB_PATH = os.path.join('instance', 'bible_titles.db')

    conn = sqlite3.connect(DB_PATH)
    # 打印数据库文件的绝对路径
    print(f"数据库文件位置: {os.path.abspath(DB_PATH)}")
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chapter_titles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book TEXT NOT NULL,
        version TEXT NOT NULL,
        titles_subtitles TEXT,
        UNIQUE(book, version)
    )
    ''')
    conn.commit()
    conn.close()

# 初始化数据库
init_db()

@app.route('/', methods=['GET', 'POST'])
def index():

    init_db()
    
    if request.method == 'POST':
        if 'book' in request.form and 'chapter' in request.form and 'version' in request.form:
            book = request.form['book']
            chapter = request.form['chapter']
            version = request.form['version']
            
            # 检查是否是特殊章节号
            if chapter == '0.1':
                # 爬取标题和子标题并存入数据库
                return crawl_and_save_titles(book, version)
            elif chapter == '0':
                # 从数据库读取标题和子标题
                return load_titles_from_db(book, version)
            else:
                # 正常加载章节
                return load_chapter(book, chapter, version)
        elif 'url' in request.form:
            url = request.form['url']
            return load_from_url(url)
    
    return render_template('index.html')

def crawl_and_save_titles(book, version):
    
    chapter_num = 1
            
    print(f"Scraping chapter {chapter_num}...")

    chapterTitles_subtitles = scrape_chapter_titles_subtitles(book, version, chapter_num)

    chapterTitles_subtitles = "<br><br>".join(chapterTitles_subtitles)

    conn = sqlite3.connect(DB_PATH)


    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT OR REPLACE INTO chapter_titles (book,version, titles_subtitles) VALUES (?, ?, ?)",
        (book,version, chapterTitles_subtitles)
    )
    conn.commit()
    conn.close()
        




    return render_template('index.html', title=f"{book}的所有标题和子标题爬取完成,已写入数据库", content=chapterTitles_subtitles)



def scrape_chapter_titles_subtitles(book_name, version="CSBS", start_chapter=1):
    
    all_titles_subtitles = []
    chapter_num = start_chapter
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    while True:
        # 构建URL
        url = f"https://www.biblegateway.com/passage/?search={book_name}+{chapter_num}&version={version}"
        
        try:
            # 发送请求获取内容
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # 如果请求失败，抛出异常
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 找到经文内容
            passage_content = soup.find('div', class_='passage-content')
            if not passage_content:
                print(f"章节 {chapter_num} 没有内容，可能已到达最后一章")
                break

            
            
            # 提取章节标题
            chapter_title = soup.find('div', class_='dropdown-display-text')
            chapter_title_text = clean_text(chapter_title.text) if chapter_title else f"{book_name} 第 {chapter_num} 章"
            
            chapter_title_text = "<br>" + chapter_title_text + "<br>"

            all_titles_subtitles.append(chapter_title_text)

            # 提取子标题
            subtitles = []
            subtitle_elements = passage_content.find_all(['h3'])
            
            for subtitle in subtitle_elements:
                clean_subtitle_text = clean_text(subtitle.text)
                if clean_subtitle_text:
                    all_titles_subtitles.append(clean_subtitle_text)
            

            
            print(f"成功爬取 {book_name} 第 {chapter_num} 章的标题和子标题")
            
            # 检查是否为空白章
            verses = passage_content.find_all('p')
            verse_text = ' '.join([clean_text(verse.text) for verse in verses])
            if not verse_text or verse_text.strip() == "":
                print(f"章节 {chapter_num} 内容为空，已到达最后一章")
                break
            
            # 增加章节号
            chapter_num += 1
            
            # 添加延迟，避免请求过于频繁
            time.sleep(1)
            
        except Exception as e:
            print(f"爬取 {book_name} 第 {chapter_num} 章时出错: {str(e)}")
            # 如果是404错误，可能已到达最后一章
            if hasattr(e, 'response') and e.response.status_code == 404:
                print(f"章节 {chapter_num} 不存在，已到达最后一章")
                break
            # 其他错误，尝试下一章
            chapter_num += 1
    
    return all_titles_subtitles


def load_titles_from_db(book, version):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT titles_subtitles FROM chapter_titles WHERE book = ? AND version = ?",
        (book, version)
    )
    results = cursor.fetchall()
    conn.close()
    
    if not results or not results[0][0]:
        return render_template('index.html', 
                              title=f"错误: 数据库中没有 {book} ({version}) 的标题信息",
                              content="请先使用章节号0.1爬取标题信息")
    
    # 提取实际内容（第一个结果的第一个元素）
    titles_subtitles = results[0][0]
    
    # 生成显示内容
    content_html = f"<h3>数据库中的章节标题和子标题:</h3><div>{titles_subtitles}</div>"
    
    return render_template('index.html', 
                          title=f"{book} ({version}) 标题信息",
                          content=content_html)

def load_chapter(book, chapter, version):
    # 原有的加载章节逻辑
    url = f"https://www.biblegateway.com/passage/?search={book}+{chapter}&version={version}"
    return load_from_url(url)

def load_from_url(url):
    # 原有的从URL加载内容的逻辑
    
    # 发送请求获取内容
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # 如果请求失败，抛出异常
    except Exception as e:
        return render_template('index.html', content=f"获取内容失败: {str(e)}")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 提取标题
    title_element = soup.find('h1')
    title = clean_text(title_element.text) if title_element else '无标题'
    
    # 找到经文内容
    passage_content = soup.find('div', class_='passage-content')
    if not passage_content:
        return render_template('index.html', content="无法找到经文内容")
    
    chapter_text = []
    
    # 提取章节标题
    chapter_title = soup.find('div', class_='dropdown-display-text')
    if chapter_title:
        chapter_text.append(f"<h2>{clean_text(chapter_title.text)}</h2>")
    
    # 提取经文
    verses = passage_content.find_all(['p', 'h3', 'h4'])
    
    # 用于存储已处理的脚注标记
    processed_footnotes = {}  # 使用字典存储脚注ID和对应的元素

    for verse in verses:
        # 检查是否为段落标题
        if verse.name in ['h3', 'h4']:
            clean_verse_text = clean_text(verse.text)
            if clean_verse_text:
                chapter_text.append(f"<br><strong>{clean_verse_text}</strong><br>")
        else:
            # 清理文本
            if verse.text and not verse.text.startswith('Footnotes') and not verse.text.startswith('Cross references'):
                # 查找所有脚注上标
                footnote_sups = verse.find_all('sup', class_='footnote')
                
                if footnote_sups:
                    # 创建verse的副本以便修改
                    verse_copy = BeautifulSoup(str(verse), 'html.parser')
                    
                    # 处理每个脚注上标
                    for sup in verse_copy.find_all('sup', class_='footnote'):
                        # 获取脚注ID
                        footnote_id = sup.get('data-fn')
                        if footnote_id and footnote_id.startswith('#'):
                            footnote_id = footnote_id[1:]  # 移除开头的#号
                            
                            # 为上标添加ID
                            sup['id'] = f"footnote-ref-{footnote_id}"
                            
                            # 记录脚注信息
                            processed_footnotes[footnote_id] = {
                                'ref_id': f"footnote-ref-{footnote_id}",
                                'letter': sup.text.strip('[]')  # 移除方括号
                            }
                    
                    # 添加修改后的HTML
                    chapter_text.append(str(verse_copy))
                else:
                    # 如果没有脚注，直接添加原始文本
                    clean_verse_text = clean_text(verse.text)
                    if clean_verse_text:
                        chapter_text.append(clean_verse_text)
    
    # 打印处理结果
    print(f"处理了 {len(processed_footnotes)} 个上标脚注: {', '.join(processed_footnotes.keys())}")

    # 在处理脚注上标后
    for footnote_id, info in processed_footnotes.items():
        print(f"脚注ID: {footnote_id}, 字母: {info['letter']}, 引用ID: {info['ref_id']}")

    # 处理脚注部分
    footnotes_section = soup.find('div', class_='footnotes')
    print(f"找到脚注容器: {footnotes_section is not None}")
    
    if footnotes_section:
        chapter_text.append("<br><strong>脚注</strong><br>")
        
        # 尝试多种方式获取脚注项
        footnote_items = footnotes_section.find_all('li')
        print(f"脚注项数量 (li): {len(footnote_items)}")
        
        # 在处理脚注项时
        for i, item in enumerate(footnote_items):
            print(f"脚注项 {i}:")
            print(f"  ID: {item.get('id')}")
            print(f"  文本: {item.get_text(separator=' ', strip=True)[:50]}...")  # 打印前50个字符
            print(f"  HTML: {str(item)[:100]}...")  # 打印前100个字符
        
        # 处理每个脚注项
        footnote_links_added = 0
        for i, item in enumerate(footnote_items):

            letter = string.ascii_lowercase[i % 26]
            
            # 获取脚注文本
            full_text = item.get_text(separator=' ', strip=True)
            
            
            # 尝试匹配脚注ID
            matched_id = None
            

            print(f"processed_footnotes: {processed_footnotes}")
            # 方法1：通过ID属性匹配
            item_id = item.get('id')
            if item_id and item_id in processed_footnotes:
                matched_id = item_id
            
            
            
            # 如果找到匹配的ID，添加返回链接
            if matched_id:
                ref_info = processed_footnotes[matched_id]
                footnote_html = f'<div id="{matched_id}"><a href="#{ref_info["ref_id"]}" title="返回原文" class="footnote-back">{letter}</a>{full_text}</div>'
                chapter_text.append(footnote_html)
                footnote_links_added += 1
            else:
                # 如果没有匹配，直接添加文本
                chapter_text.append(f"<div>{full_text}</div>")
        
        print(f"添加了 {footnote_links_added} 个底部脚注链接")
    
    # 调试代码
    if footnotes_section:
        print("脚注HTML结构:", str(verse))
    
    # 正确连接列表元素
    formatted_content = "<br>".join(chapter_text)
    
    # 最后一次清理，确保没有遗漏
    formatted_content = clean_text(formatted_content)
    
    # 添加CSS样式
    footnote_styles = """
    <style>
        .footnote-back {
            text-decoration: none;
            color: #0066cc;
            font-size: 0.8em;
            vertical-align: super;
            margin-left: 2px;
        }
        
        sup a {
            text-decoration: none;
            color: #0066cc;
        }
        
        sup a:hover, .footnote-back:hover {
            text-decoration: none;
        }
        
        /* 全局移除所有下划线 */
        * {
            text-decoration: none !important;
        }
        
        /* 如果只想移除链接的下划线 */
        a {
            text-decoration: none !important;
        }
    </style>
    """

    # 在返回模板前添加样式
    formatted_content = footnote_styles + formatted_content
    
    return render_template('index.html', title=title, content=formatted_content)





# 定义一个专门的清理函数
def clean_text(text):
    if not text:
        return ""
    
    # 只替换特殊空白字符，保留HTML标签
    text = text.replace('\xa0', ' ')
    
    # 去除首尾空白
    text = text.strip()
    
    # 移除所有下划线，但保留下划线上的字符
    text = text.replace('_', '')
    
    return text


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True) 