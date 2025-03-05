from flask import Flask, request, render_template
import requests
from bs4 import BeautifulSoup
import string
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']


        headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }   


        
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print(f"Failed to retrieve chapter {chapter_num}: Status code {response.status_code}")
            return None
    
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the passage content
        passage_content = soup.find('div', class_='passage-content')
        if not passage_content:
            print(f"Could not find passage content for chapter {chapter_num}")
            return None

        chapter_text = []
        
        # Extract chapter title
        chapter_title = soup.find('div', class_='dropdown-display-text')
        title_text = chapter_title.text.strip() if chapter_title else f"第{chapter_num}章"
        
        # Extract verses
        verses = passage_content.find_all(['p', 'h3', 'h4'])
        

        for verse in verses:
            
            # Check if it's a section heading
            if verse.name in ['h3']:
                chapter_text.append(f"<br>{verse.text.strip()}<br>")
            else:
                # Clean up the text
                text = verse.text.strip()
                if text and not text.startswith('Footnotes') and not text.startswith('Cross references'):
                    chapter_text.append(text)
        
        # 专门处理页面底部的脚注部分
        footnotes_section = soup.find('div', class_='footnotes')
        if footnotes_section:
            chapter_text.append("\n脚注\n")
            # 获取所有脚注项
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
        
        formatted_content = "\n".join(chapter_text)


        
        return render_template('index.html', title=title_text, content=formatted_content, url=url)
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True,port=5001) 