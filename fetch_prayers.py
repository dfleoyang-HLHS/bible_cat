import json
import re
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://www.boai.org.tw/about-us/itemlist/category/279.html"

def get_browser():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def parse_exact_prayer_text(full_text, title_text):
    """根據標準範本格式精準正則拆解欄位"""
    
    # 1. 日期與 ID
    date_match = re.search(r'(\d{1,2}/\d{1,2}\s*[\–\-~]\s*\d{1,2}/\d{1,2}|\d{4}\.\d{1,2}\.\d{1,2}\s*[\–\-~]\s*\d{1,2}\.\d{1,2})', title_text + " " + full_text)
    date_str = date_match.group(1) if date_match else "聚會紀錄"
    
    clean_date_num = re.sub(r'\D', '', date_str.split('-')[0].split('–')[0])
    date_id = f"prayer-2026{clean_date_num}" if len(clean_date_num) <= 4 else f"prayer-{clean_date_num}"

    # 2. 主題解析
    topic_match = re.search(r'主題[：:]\s*(.*?)(?=\n|經文[：:]|$)', full_text)
    if topic_match and topic_match.group(1).strip():
        topic_str = topic_match.group(1).strip()
    else:
        topic_str = title_text.replace(date_str, "").replace("禱告專區", "").strip()
        if not topic_str or len(topic_str) < 2:
            lines = [line.strip() for line in full_text.split('\n') if len(line.strip()) > 4 and not any(k in line for k in ["禱告專區", "經文", "分享"])]
            topic_str = lines[0] if lines else "讓基督的平安在心裡作主"

    # 3. 經文
    scripture_match = re.search(r'經文[：:]\s*(.*?)(?=\n|分享[：:]|$)', full_text)
    scripture_str = scripture_match.group(1).strip() if scripture_match else "請參閱官網經文"

    # 4. 分享段落
    share_paragraphs = []
    share_match = re.search(r'分享[：:]\s*(.*?)(?=禱告焦點[：:]|1\.|\n1\.|為自己禱告|$)', full_text, re.DOTALL)
    if share_match:
        raw_share = share_match.group(1).strip()
        share_paragraphs = [p.strip() for p in raw_share.split('\n') if len(p.strip()) > 10]

    if not share_paragraphs:
        raw_lines = [line.strip() for line in full_text.split('\n') if len(line.strip()) > 20 and not any(k in line for k in ["禱告焦點", "為自己禱告", "為教會禱告", "為國度禱告"])]
        share_paragraphs = raw_lines[:3] if raw_lines else ["請參閱本週官網小組分享內文。"]

    # 5. 禱告焦點
    focus_match = re.search(r'禱告焦點[：:]\s*(.*?)(?=\n|1\.|\n1\.|為自己禱告|$)', full_text)
    focus_str = focus_match.group(1).strip() if focus_match else "求聖靈引導我們經歷神的恩典。"

    # 6. 三大禱告項目
    p_self_match = re.search(r'1\.\s*為自己禱告[：:]\s*(.*?)(?=\n2\.|2\.|為教會禱告|$)', full_text, re.DOTALL)
    p_church_match = re.search(r'2\.\s*為教會禱告[：:]\s*(.*?)(?=\n3\.|3\.|為國度禱告|$)', full_text, re.DOTALL)
    p_kingdom_match = re.search(r'3\.\s*為國度禱告[：:]\s*(.*?)(?=\n為教會事工守望|事工守望|本週默想|$)', full_text, re.DOTALL)

    p_self = p_self_match.group(1).strip() if p_self_match else "宣告主的平安充滿我的心。"
    p_church = p_church_match.group(1).strip() if p_church_match else "求主聖靈大能運行在教會中。"
    p_kingdom = p_kingdom_match.group(1).strip() if p_kingdom_match else "為國度復興與世代平安守望。"

    # 7. 教會事工守望
    intercessions = []
    intercessions_match = re.search(r'為教會事工守望[：:]\s*(.*?)(?=\n本週默想|本週默想[：:]|$)', full_text, re.DOTALL)
    if intercessions_match:
        raw_inter = intercessions_match.group(1).strip()
        raw_items = re.split(r'[；;\n]', raw_inter)
        intercessions = [it.strip() for it in raw_items if len(it.strip()) > 2]

    if not intercessions:
        intercessions = ["裝備課程與小組聚會順利進行", "母堂及各分堂弟兄姊妹身心靈健壯"]

    # 8. 本週默想
    meditation_match = re.search(r'本週默想[：:]\s*(.*?)(?=\n|$)', full_text)
    meditation_str = meditation_match.group(1).strip() if meditation_match else "本週如何將神的話語落實在日常生活中？"

    return {
        "id": date_id,
        "date": date_str,
        "topic": topic_str,
        "scripture": scripture_str,
        "shareParagraphs": share_paragraphs,
        "prayerFocus": focus_str,
        "prayers": [
            {"title": "1. 為自己禱告", "text": p_self},
            {"title": "2. 為教會禱告", "text": p_church},
            {"title": "3. 為國度禱告", "text": p_kingdom}
        ],
        "churchIntercessions": intercessions,
        "meditation": meditation_str
    }

def fetch_latest_9_prayers():
    driver = get_browser()
    print(f"正在開啟博愛浸信會官網: {BASE_URL}")
    driver.get(BASE_URL)
    time.sleep(3)

    # 用 JS 強制把頁面上所有隱藏面板（Accordion/Toggle/Collapse）全部顯示
    try:
        driver.execute_script("""
            var elements = document.querySelectorAll('*');
            for (var i = 0; i < elements.length; i++) {
                var style = window.getComputedStyle(elements[i]);
                if (style.display === 'none') {
                    elements[i].style.setProperty('display', 'block', 'important');
                }
            }
        """)
        time.sleep(1.5)
    except Exception as e:
        print(f"JS 展平網頁提示: {e}")

    prayer_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '禱告專區')]")
    print(f"尋找到 {len(prayer_elements)} 個「禱告專區」相關標題！")

    all_prayers = []
    
    for idx, el in enumerate(prayer_elements[:15]):
        title_text = el.text.strip()
        if not title_text or "禱告專區" not in title_text:
            continue

        print(f"正在讀取 [{idx+1}]: {title_text}")

        try:
            # 安全獲取包含標題與內文的祖先容器
            parent_container = el.find_element(By.XPATH, "./ancestor::*[contains(@class, 'catItem') or contains(@class, 'accordion') or contains(@class, 'toggle') or contains(@class, 'itemBody') or position()=2]")
            full_text = parent_container.text.strip()

            # 若容器文字過少，嘗試點擊展開並重試讀取
            if len(full_text) < 50:
                driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", el)
                time.sleep(2.0)
                full_text = parent_container.text.strip()

            parsed_data = parse_exact_prayer_text(full_text, title_text)
            
            if parsed_data['topic'] and len(full_text) > 30:
                if not any(p['id'] == parsed_data['id'] for p in all_prayers):
                    all_prayers.append(parsed_data)
                    print(f"  └─ 成功解析主題: {parsed_data['topic']}")
            else:
                print(f"  └─ 內容載入不足（長度: {len(full_text)}），跳過記錄")

            if len(all_prayers) >= 9:
                break

        except Exception as e:
            print(f"  └─ 讀取解析失敗: {e}")

    driver.quit()
    return all_prayers

def update_json():
    prayers_list = fetch_latest_9_prayers()
    if prayers_list:
        with open('prayers.json', 'w', encoding='utf-8') as f:
            json.dump(prayers_list, f, ensure_ascii=False, indent=2)
        print(f"🎉 成功！已精準抓取最新 {len(prayers_list)} 篇禱告日誌並寫入 prayers.json！")
    else:
        print("未抓取到任何資料。")

if __name__ == '__main__':
    update_json()
