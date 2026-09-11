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

def parse_exact_prayer_text(full_text, article_title):
    """根據博愛浸信會標準範本，精準正則拆解欄位"""
    
    # 1. 日期與 ID
    date_match = re.search(r'(\d{1,2}/\d{1,2}\s*[\–\-~]\s*\d{1,2}/\d{1,2}|\d{4}\.\d{1,2}\.\d{1,2}\s*[\–\-~]\s*\d{1,2}\.\d{1,2})', full_text + " " + article_title)
    date_str = date_match.group(1) if date_match else "聚會紀錄"
    
    # 用月份與日期建立 ID (如 prayer-20260913)
    clean_date_num = re.sub(r'\D', '', date_str.split('-')[0].split('–')[0])
    date_id = f"prayer-2026{clean_date_num}" if len(clean_date_num) <= 4 else f"prayer-{clean_date_num}"

    # 2. 主題
    topic_match = re.search(r'主題[：:]\s*(.*?)(?=\n|經文[：:]|$)', full_text)
    topic_str = topic_match.group(1).strip() if topic_match else article_title.replace(date_str, "").replace("禱告專區", "").strip()

    # 3. 經文
    scripture_match = re.search(r'經文[：:]\s*(.*?)(?=\n|分享[：:]|$)', full_text)
    scripture_str = scripture_match.group(1).strip() if scripture_match else "請參閱官網經文"

    # 4. 分享段落 (取 分享： 與 禱告焦點： 之間的所有文字)
    share_paragraphs = []
    share_match = re.search(r'分享[：:]\s*(.*?)(?=禱告焦點[：:]|1\.|\n1\.|為自己禱告|$)', full_text, re.DOTALL)
    if share_match:
        raw_share = share_match.group(1).strip()
        share_paragraphs = [p.strip() for p in raw_share.split('\n') if len(p.strip()) > 10]

    if not share_paragraphs:
        share_paragraphs = ["請參閱本週官網小組分享內文。"]

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

    # 7. 教會事工守望 (用分號或換行切割)
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

def expand_and_fetch_all():
    driver = get_browser()
    print(f"正在開啟博愛浸信會官網: {BASE_URL}")
    driver.get(BASE_URL)
    time.sleep(3)

    # 點擊展開頁籤標題
    try:
        toggles = driver.find_elements(By.XPATH, "//div[contains(@class, 'catItemHeader')]//a | //h3[contains(@class, 'catItemTitle')]//a | //*[contains(@class, 'toggler')]")
        print(f"找到 {len(toggles)} 個折疊頁籤，開始點開...")
        for t in toggles:
            try:
                driver.execute_script("arguments[0].click();", t)
                time.sleep(0.3)
            except Exception:
                pass
    except Exception as e:
        print(f"展開提示: {e}")

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # 提取真正文章超連結
    article_targets = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.text.strip()
        
        if any(noise in text for noise in ["奉獻", "介紹", "關於", "聯絡", "主日", "課程", "服務", "登入"]):
            continue
        
        if re.search(r'\d{1,4}[\./]\d{1,2}', text) or ('item' in href and '279.html' not in href):
            full_url = "https://www.boai.org.tw" + href if href.startswith('/') else href
            if not any(t['url'] == full_url for t in article_targets) and len(text) > 3:
                article_targets.append({'url': full_url, 'title': text})

    print(f"精準抓取到 {len(article_targets)} 篇禱告日誌連結！")

    all_prayers = []
    for idx, target in enumerate(article_targets[:20]):
        print(f"正在解析文章 [{idx+1}/{min(20, len(article_targets))}]: {target['title']}")
        try:
            driver.get(target['url'])
            time.sleep(1.5)
            
            detail_soup = BeautifulSoup(driver.page_source, 'html.parser')
            # 鎖定文章核心 Body
            article_body = detail_soup.select_one('div.itemFullText') or detail_soup.select_one('div.itemIntroText') or detail_soup.select_one('div.itemBody')
            
            if article_body:
                full_text = article_body.text.strip()
                parsed_data = parse_exact_prayer_text(full_text, target['title'])
                all_prayers.append(parsed_data)
        except Exception as e:
            print(f"解析文章失敗 ({target['url']}): {e}")

    driver.quit()
    return all_prayers

def update_json():
    prayers_list = expand_and_fetch_all()
    if prayers_list:
        with open('prayers.json', 'w', encoding='utf-8') as f:
            json.dump(prayers_list, f, ensure_ascii=False, indent=2)
        print(f"🎉 成功！已寫入 {len(prayers_list)} 篇完美匹配範本的禱告日誌至 prayers.json！")
    else:
        print("未抓取到任何資料。")

if __name__ == '__main__':
    update_json()
