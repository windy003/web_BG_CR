from flask import Flask, request, render_template
import requests , string
from bs4 import BeautifulSoup
import re
import html

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # 检查是否直接提交了URL
        if 'url' in request.form and request.form['url'].strip():
            url = request.form['url'].strip()
        # 否则，从书名、章数和版本号生成URL
        elif all(field in request.form for field in ['book', 'chapter', 'version']):
            book = request.form['book'].strip()
            chapter = request.form['chapter'].strip()
            version = request.form['version'].strip()
            
            # 构建URL
            url = f"https://www.biblegateway.com/passage/?search={book}+{chapter}&version={version}"
        else:
            return render_template('index.html', content="请提供有效的URL或书名、章数和版本号")
        
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
        
        for verse in verses:
            # 检查是否为段落标题
            if verse.name in ['h3', 'h4']:
                clean_verse_text = clean_text(verse.text)
                if clean_verse_text:
                    chapter_text.append(f"<br><strong>{clean_verse_text}</strong><br>")
            else:
                # 清理文本
                clean_verse_text = clean_text(verse.text)
                if clean_verse_text and not clean_verse_text.startswith('Footnotes') and not clean_verse_text.startswith('Cross references'):
                    chapter_text.append(clean_verse_text)
        
        # 处理脚注
        footnotes_section = soup.find('div', class_='footnotes')
        if footnotes_section:
            chapter_text.append("<br><strong>脚注</strong><br>")
            footnote_items = footnotes_section.find_all('li')
            
             # 创建小写字母列表
            footnote_markers = list(string.ascii_lowercase)
            for i, item in enumerate(footnote_items):
                if i < len(footnote_markers):
                    marker = footnote_markers[i]
                    full_text = item.get_text(separator=' ', strip=True)
                    # 确保脚注标记正确显示
                    if not full_text.startswith(marker):
                        full_text = f"{marker} {full_text}"
                    chapter_text.append(full_text)



        # 正确连接列表元素
        formatted_content = "<br>".join(chapter_text)
        
        # 最后一次清理，确保没有遗漏
        formatted_content = clean_text(formatted_content)
        
        return render_template('index.html', title=title, content=formatted_content, url=url)
    
    return render_template('index.html')

# 定义一个专门的清理函数
def clean_text(text):
    if not text:
        return ""
    
    # 使用正则表达式替换所有空白字符（包括\xa0）为单个空格
    text = re.sub(r'\s+', ' ', text)
    
    # 确保没有\xa0（虽然上面的正则应该已经处理了，但为了保险起见）
    text = text.replace('\xa0', ' ')
    
    # 去除首尾空白
    text = text.strip()
    
    return text

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True) 