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

def expand_and_fetch_all():
    driver = get_browser()
    print(f"正在開啟博愛浸信會官網: {BASE_URL}")
    driver.get(BASE_URL)
    time.sleep(3) # 等待初始 DOM 載入

    # 1. 精準點擊每一個收合頁籤的標題元素
    # 針對 Joomla/K2 及常見 Accordion 頁籤標題進行多重路徑比對
    xpath_selectors = [
        "//div[contains(@class, 'catItemHeader')]//a",
        "//h3[contains(@class, 'catItemTitle')]//a",
        "//*[contains(@class, 'toggler')]",
        "//*[contains(@class, 'accordion')]",
        "//div[contains(@id, 'k2Accordion')]//h3",
        "//a[contains(@class, 'ub-header')]"
    ]

    clicked_count = 0
    for selector in xpath_selectors:
        elements = driver.find_elements(By.XPATH, selector)
        if elements:
            print(f"找到 {len(elements)} 個標題頁籤 (使用選取器: {selector})，開始逐一模擬點擊展開...")
            for el in elements:
                try:
                    # 使用 JavaScript 強制點擊頁籤標題
                    driver.execute_script("arguments[0].click();", el)
                    time.sleep(0.5) # 留給網頁展開動畫時間
                    clicked_count += 1
                except Exception:
                    pass

    print(f"完成頁籤點擊，共嘗試點開 {clicked_count} 次。")
    time.sleep(2)

    # 2. 解析點開後的 HTML 網頁
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # 3. 嚴格過濾超連結：只抓取標題含有日期（如 2026.9.13 或 9.13）或「禱告日誌」關鍵字的真正連結
    article_targets = []
    all_links = soup.find_all('a', href=True)

    for a in all_links:
        href = a['href']
        text = a.text.strip()

        # 排除非文章頁面與導覽選單（如奉獻徵信、部門介紹、分堂資訊等）
        if any(ex in text for ex in ["奉獻", "介紹", "關於", "聯絡", "主日"]):
            continue

        # 必須包含日期格式或特定路徑特徵
        has_date = re.search(r'\d{1,4}\.\d{1,2}', text) or re.search(r'\d{1,2}/\d{1,2}', text)
        is_item_link = 'item' in href and '279.html' not in href

        if has_date or is_item_link:
            full_url = "https://www.boai.org.tw" + href if href.startswith('/') else href
            
            # 去重檢查
            if not any(t['url'] == full_url for t in article_targets) and len(text) > 3:
                article_targets.append({'url': full_url, 'title': text})

    print(f"精準篩選出 {len(article_targets)} 篇真正的禱告日誌連結！")

    # 4. 逐一進入文章頁面抓取內容
    all_prayers = []
    for idx, target in enumerate(article_targets[:20]):
        print(f"正在抓取禱告日誌 [{idx+1}/{min(20, len(article_targets))}]: {target['title']}")
        try:
            driver.get(target['url'])
            time.sleep(1.5)
            detail_soup = BeautifulSoup(driver.page_source, 'html.parser')

            content_div = detail_soup.find('div', class_='itemFullText') or detail_soup.find('div', class_='itemIntroText') or detail_soup.find('body')
            paragraphs = [p.text.strip() for p in content_div.find_all(['p', 'div']) if len(p.text.strip()) > 5]

            title_text = target['title']
            date_match = re.search(r'(\d{4}\.\d{1,2}\.\d{1,2}-\d{1,2}\.\d{1,2}|\d{4}\.\d{1,2}\.\d{1,2})', title_text)
            date_str = date_match.group(1) if date_match else "聚會紀錄"
            topic_str = title_text.replace(date_str, "").strip() if date_match else title_text
            date_id = "prayer-" + re.sub(r'\D', '', date_str.split('-')[0]) if date_match else f"prayer-hist-{idx}"

            scripture = paragraphs[0] if len(paragraphs) > 0 else "詳見官網文章"
            share_paragraphs = paragraphs[1:4] if len(paragraphs) >= 4 else paragraphs

            all_prayers.append({
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
            })
        except Exception as e:
            print(f"抓取內文失敗 ({target['url']}): {e}")

    driver.quit()
    return all_prayers

def update_json():
    prayers_list = expand_and_fetch_all()
    if prayers_list:
        with open('prayers.json', 'w', encoding='utf-8') as f:
            json.dump(prayers_list, f, ensure_ascii=False, indent=2)
        print(f"🎉 成功！已寫入 {len(prayers_list)} 篇禱告日誌至 prayers.json！")
    else:
        print("未抓取到任何資料。")

if __name__ == '__main__':
    update_json()
