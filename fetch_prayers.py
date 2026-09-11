import json
import re
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

BASE_URL = "https://www.boai.org.tw/about-us/itemlist/category/279.html"

def fetch_prayer_detail(article_url):
    """抓取單篇禱告日誌的詳細內容"""
    try:
        req = Request(article_url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urlopen(req).read().decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')

        content_div = soup.find('div', class_='itemFullText') or soup.find('div', class_='itemIntroText')
        if not content_div:
            return None

        paragraphs = [p.text.strip() for p in content_div.find_all('p') if p.text.strip()]
        return paragraphs
    except Exception as e:
        print(f"讀取文章失敗 {article_url}: {e}")
        return None

def fetch_batch_prayers(limit=20):
    """抓取前 limit 篇歷史禱告日誌"""
    all_prayers = []
    page = 0
    
    while len(all_prayers) < limit:
        # K2 組件的分頁網址格式 (每頁通常 10 篇)
        url = f"{BASE_URL}?start={page * 10}" if page > 0 else BASE_URL
        print(f"正在掃描清單頁面: {url}")
        
        try:
            req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            html = urlopen(req).read().decode('utf-8')
            soup = BeautifulSoup(html, 'html.parser')

            # 尋求文章標題與連結
            items = soup.find_all('div', class_='catItemHeader') or soup.find_all('h3', class_='catItemTitle')
            if not items:
                print("已無更多歷史文章。")
                break

            for item in items:
                if len(all_prayers) >= limit:
                    break

                link_tag = item.find('a')
                if not link_tag:
                    continue

                article_url = "https://www.boai.org.tw" + link_tag['href']
                title_text = link_tag.text.strip()

                # 解析日期與主題
                date_match = re.search(r'(\d{4}\.\d{1,2}\.\d{1,2}-\d{1,2}\.\d{1,2})', title_text)
                date_str = date_match.group(1) if date_match else "聚會紀錄"
                topic_str = title_text.replace(date_str, "").strip() if date_match else title_text
                date_id = "prayer-" + re.sub(r'\D', '', date_str.split('-')[0]) if date_match else f"prayer-hist-{len(all_prayers)}"

                # 避免重複抓取
                if any(p['id'] == date_id for p in all_prayers):
                    continue

                print(f"正在抓取 [{len(all_prayers)+1}/{limit}]: {title_text}")
                paragraphs = fetch_prayer_detail(article_url)
                if not paragraphs:
                    continue

                new_prayer = {
                    "id": date_id,
                    "date": date_str,
                    "topic": topic_str,
                    "scripture": paragraphs[0] if len(paragraphs) > 0 else "詳見官網",
                    "shareParagraphs": paragraphs[1:4] if len(paragraphs) >= 4 else paragraphs,
                    "prayerFocus": "請參閱本週聚會分享與代禱事項。",
                    "prayers": [
                        {"title": "1. 為自己禱告", "text": "請參照官網禱告手冊導引進行個人尋求與宣告。"},
                        {"title": "2. 為教會禱告", "text": "求主聖靈大能充滿教會，同心合意活出榮耀見證。"},
                        {"title": "3. 為國度禱告", "text": "為世代復興、國家平安與全國嚴肅會守望禱告。"}
                    ],
                    "churchIntercessions": [
                        "裝備課與聚會順利進行",
                        "為各區嚴肅會與代禱者訓練守望",
                        "母堂及各分堂病患經歷神醫治大能"
                    ],
                    "meditation": "本週如何將神的話語落落在日常生活中？"
                }

                all_prayers.append(new_prayer)

            page += 1
        except Exception as e:
            print(f"抓取清單頁面失敗: {e}")
            break

    return all_prayers

def update_json():
    print("開始執行批量 20 週歷史資料抓取...")
    prayers_list = fetch_batch_prayers(limit=20)
    
    if prayers_list:
        with open('prayers.json', 'w', encoding='utf-8') as f:
            json.dump(prayers_list, f, ensure_ascii=False, indent=2)
        print(f"完成！已順利寫入 {len(prayers_list)} 篇禱告日誌至 prayers.json。")
    else:
        print("未抓取到任何資料。")

if __name__ == '__main__':
    update_json()
