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
    """建立隱形 Chrome 瀏覽器"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def expand_and_fetch_all():
    driver = get_browser()
    print(f"正在開啟博愛浸信會官網: {BASE_URL}")
    driver.get(BASE_URL)
    time.sleep(3) # 等待網頁與動態套件載入完成

    # 尋找並點開頁面上所有的收合/摺疊區塊 (Toggle/Accordion/Collapse)
    try:
        # 尋找常見的摺疊按鈕 class (例如 accordion, toggle, collapse, catItemHeader 等)
        toggle_buttons = driver.find_elements(By.XPATH, "//a[contains(@class, 'toggle') or contains(@class, 'accordion') or contains(@class, 'toggler')] | //div[contains(@class, 'catItemHeader')]")
        print(f"找到 {len(toggle_buttons)} 個可能收合的區塊，準備全部點開...")
        
        for btn in toggle_buttons:
            try:
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.3)
            except Exception:
                pass
        time.sleep(2)
    except Exception as e:
        print(f"自動點開摺疊區塊時出現小提醒（不影響後續）: {e}")

    # 取得點開後的完整 HTML
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    
    # 搜尋所有文章的超連結
    links = soup.select('a')
    article_targets = []

    for a in links:
        href = a.get('href', '')
        title_text = a.text.strip()
        
        # 篩選出標題帶有日期格式或為文章路徑的連結
        if '279.html' not in href and ('item' in href or re.search(r'\d{4}\.\d{1,2}', title_text)):
            full_url = "https://www.boai.org.tw" + href if href.startswith('/') else href
            if full_url not in [t['url'] for t in article_targets] and len(title_text) > 5:
                article_targets.append({'url': full_url, 'title': title_text})

    print(f"成功擷取到 {len(article_targets)} 篇潛在禱告日誌連結！")

    # 開始逐一抓取每篇文章內文
    all_prayers = []
    for idx, target in enumerate(article_targets[:20]): # 限制前 20 篇
        print(f"正在抓取內文 [{idx+1}/{min(20, len(article_targets))}]: {target['title']}")
        try:
            driver.get(target['url'])
            time.sleep(1.5)
            detail_soup = BeautifulSoup(driver.page_source, 'html.parser')

            content_div = detail_soup.find('div', class_='itemFullText') or detail_soup.find('div', class_='itemIntroText') or detail_soup.find('body')
            paragraphs = [p.text.strip() for p in content_div.find_all(['p', 'div']) if len(p.text.strip()) > 5]

            # 提取日期與主題
            title_text = target['title']
            date_match = re.search(r'(\d{4}\.\d{1,2}\.\d{1,2}-\d{1,2}\.\d{1,2}|\d{4}\.\d{1,2}\.\d{1,2})', title_text)
            date_str = date_match.group(1) if date_match else "聚會紀錄"
            topic_str = title_text.replace(date_str, "").strip() if date_match else title_text
            date_id = "prayer-" + re.sub(r'\D', '', date_str.split('-')[0]) if date_match else f"prayer-hist-{idx}"

            scripture = paragraphs[0] if len(paragraphs) > 0 else "詳見官網文章"
            share_paragraphs = paragraphs[1:4] if len(paragraphs) >= 4 else paragraphs

            new_prayer = {
                "id": date_id,
                "date": date_str,
                "topic": topic_str if topic_str else "每週聚會禱告",
                "scripture": scripture,
                "shareParagraphs": share_paragraphs if share_paragraphs else ["請至官網參閱內文"],
                "prayerFocus": "請參閱本週聚會分享與同心守望代禱事項。",
                "prayers": [
                    {"title": "1. 為自己禱告", "text": "請參照官網禱告手冊進行個人尋求與宣告。"},
                    {"title": "2. 為教會禱告", "text": "求主聖靈大能充滿教會，同心合意活出榮耀見證。"},
                    {"title": "3. 為國度禱告", "text": "為世代復興、國家平安守望禱告。"}
                ],
                "churchIntercessions": [
                    "母堂及各分堂病患經歷神醫治大能",
                    "裝備課與聚會順利進行"
                ],
                "meditation": "本週如何將神的話語落實在日常生活中？"
            }
            all_prayers.append(new_prayer)
        except Exception as e:
            print(f"抓取內文失敗 ({target['url']}): {e}")

    driver.quit()
    return all_prayers

def update_json():
    prayers_list = expand_and_fetch_all()
    if prayers_list:
        with open('prayers.json', 'w', encoding='utf-8') as f:
            json.dump(prayers_list, f, ensure_ascii=False, indent=2)
        print(f"🎉 成功！已將點開後的 {len(prayers_list)} 篇歷史禱告日誌寫入 prayers.json！")
    else:
        print("未抓取到任何資料。")

if __name__ == '__main__':
    update_json()
