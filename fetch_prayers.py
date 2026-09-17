import json
import re
import sys
import time

try:
    # Windows 主控台預設編碼（如 cp950）無法印出中文與 emoji，會讓腳本在寫檔成功後仍以例外結束
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

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

def parse_exact_prayer_text(full_text, title_text, pub_year):
    """根據標準範本格式精準正則拆解欄位。full_text 必須是單一週次的獨立內文（不可跨週混雜）。"""

    # 官網部分標籤前面會有 FontAwesome 圖示（例如小喇叭圖示），Selenium 的 .text
    # 會把該圖示字型的私有區域字元一併讀出來，先清掉避免殘留在擷取結果尾端。
    full_text = re.sub(r'[-]', '', full_text)

    # 1. 日期與 ID（年份取自該篇文章實際發布年份，而非寫死年份）
    date_match = re.search(r'(\d{1,2}/\d{1,2}\s*[\–\-~]\s*\d{1,2}/\d{1,2})', title_text + " " + full_text)
    date_str = date_match.group(1) if date_match else "聚會紀錄"

    clean_date_num = re.sub(r'\D', '', re.split(r'[\–\-~]', date_str)[0])
    date_id = f"prayer-{pub_year}{clean_date_num}" if clean_date_num else f"prayer-{pub_year}-{abs(hash(full_text)) % 100000}"

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
    # 注意：lookahead 不能只留「事工守望」單獨當候選條件，
    # 因為它是「為教會事工守望」的子字串，會讓擷取在標籤中間被提早截斷，
    # 留下多餘的「為教會」殘字；「為教會事工守望」前面有時還會有官網自己編的
    # 項目編號（例如「4.」），也要一併排除在擷取範圍外。
    p_kingdom_match = re.search(r'3\.\s*為國度禱告[：:]\s*(.*?)(?=\d*\.?\s*為教會事工守望|本週默想|$)', full_text, re.DOTALL)

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

    # 用 JS 強制把頁面上所有隱藏面板（Bootstrap accordion 的 .collapse）全部顯示，
    # 否則 Selenium 的 .text 只會讀到目前展開中的那一篇（預設只有最新一篇是展開的）
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

    # 每一週的禱告日誌在頁面上是獨立的 <div class="accordion-group">，
    # 直接以這個容器為單位讀取，才不會把多週內容混在一起解析
    containers = driver.find_elements(By.CSS_SELECTOR, "div.accordion-group")
    print(f"找到 {len(containers)} 個禱告日誌項目！")

    all_prayers = []

    for idx, container in enumerate(containers[:15]):
        try:
            full_text = container.text.strip()
            if "禱告專區" not in full_text or len(full_text) < 30:
                print(f"  └─ 第 {idx+1} 項內容不足（長度: {len(full_text)}），跳過記錄")
                continue

            print(f"正在讀取 [{idx+1}]: {full_text.splitlines()[0] if full_text.splitlines() else ''}")

            # 該篇文章實際發布的年份（避免把年份寫死在程式中造成隔年失效）
            pub_year = str(time.localtime().tm_year)
            try:
                date_badge_text = container.find_element(By.CSS_SELECTOR, ".event-list-item-date").text
                year_match = re.search(r'(\d{4})', date_badge_text)
                if year_match:
                    pub_year = year_match.group(1)
            except Exception:
                pass

            title_match = re.search(r'\d{1,2}/\d{1,2}\s*[\–\-~]\s*\d{1,2}/\d{1,2}\s*禱告專區', full_text)
            title_text = title_match.group(0) if title_match else full_text.splitlines()[0]

            parsed_data = parse_exact_prayer_text(full_text, title_text, pub_year)

            if parsed_data['topic']:
                if not any(p['id'] == parsed_data['id'] for p in all_prayers):
                    all_prayers.append(parsed_data)
                    print(f"  └─ 成功解析主題: {parsed_data['topic']}")
                else:
                    print(f"  └─ 與已抓取項目重複（id: {parsed_data['id']}），略過")

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
