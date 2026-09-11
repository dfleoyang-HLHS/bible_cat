import json
import re
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

BASE_URL = "https://www.boai.org.tw/about-us/itemlist/category/279.html"

def fetch_prayer_detail(article_url):
    """抓取單篇禱告日誌內文並解析特定區塊"""
    try:
        req = Request(article_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        html = urlopen(req, timeout=10).read().decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')

        # 找尋內文容器
        content_div = soup.find('div', class_='itemFullText') or soup.find('div', class_='itemIntroText') or soup.find('div', class_='itemBody')
        if not content_div:
            return None

        # 整理所有文字段落
        paragraphs = [p.text.strip() for p in content_div.find_all(['p', 'div']) if p.text.strip()]
        
        scripture = "詳見官網文章"
        share_paragraphs = []
        prayer_self = "請參照官網禱告手冊進行個人尋求與宣告。"
        prayer_church = "求主聖靈大能充滿教會，同心合意活出榮耀見證。"
        prayer_kingdom = "為世代復興、國家平安守望禱告。"
        church_intercessions = ["母堂及各分堂病患經歷神醫治大能", "裝備課與聚會順利進行"]

        # 解析文字內容
        for p in paragraphs:
            if "經文" in p or "加拉太書" in p or "「" in p:
                if scripture == "詳見官網文章":
                    scripture = p
            elif "為自己禱告" in p:
                prayer_self = p.replace("為自己禱告：", "").replace("1.", "").strip()
            elif "為教會禱告" in p:
                prayer_church = p.replace("為教會禱告：", "").replace("2.", "").strip()
            elif "為國度禱告" in p:
                prayer_kingdom = p.replace("為國度禱告：", "").replace("3.", "").strip()
            elif "為教會事工守望" in p or "事工守望" in p:
                items = p.split("；")
                church_intercessions = [it.replace("為教會事工守望：", "").strip() for it in items if it.strip()]
            else:
                if len(p) > 20 and len(share_paragraphs) < 4:
                    share_paragraphs.append(p)

        return {
            "scripture": scripture,
            "shareParagraphs": share_paragraphs if share_paragraphs else ["請至博愛浸信會官網參閱完整聚會分享。"],
            "prayers": [
                {"title": "1. 為自己禱告", "text": prayer_self},
                {"title": "2. 為教會禱告", "text": prayer_church},
                {"title": "3. 為國度禱告", "text": prayer_kingdom}
            ],
            "churchIntercessions": church_intercessions
        }
    except Exception as e:
        print(f"解析文章失敗 ({article_url}): {e}")
        return None

def fetch_batch_prayers(limit=20):
    """抓取前 limit 篇歷史禱告日誌"""
    all_prayers = []
    page = 0
    
    while len(all_prayers) < limit:
        url = f"{BASE_URL}?start={page * 10}" if page > 0 else BASE_URL
        print(f"正在讀取清單頁面: {url}")
        
        try:
            req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            html = urlopen(req, timeout=10).read().decode('utf-8')
            soup = BeautifulSoup(html, 'html.parser')

            # 抓取文章清單標題連結
            items = soup.select('.catItemHeader a, .catItemTitle a, h3.catItemTitle a')
            if not items:
                print("已無更多歷史頁面。")
                break

            for link_tag in items:
                if len(all_prayers) >= limit:
                    break

                href = link_tag.get('href', '')
                if not href:
                    continue
                
                article_url = "https://www.boai.org.tw" + href if href.startswith('/') else href
                title_text = link_tag.text.strip()

                # 提煉日期與主題
                date_match = re.search(r'(\d{4}\.\d{1,2}\.\d{1,2}-\d{1,2}\.\d{1,2}|\d{4}\.\d{1,2}\.\d{1,2})', title_text)
                date_str = date_match.group(1) if date_match else "聚會紀錄"
                topic_str = title_text.replace(date_str, "").strip() if date_match else title_text
                date_id = "prayer-" + re.sub(r'\D', '', date_str.split('-')[0]) if date_match else f"prayer-hist-{len(all_prayers)}"

                # 去重檢查
                if any(p['id'] == date_id for p in all_prayers):
                    continue

                print(f"正在抓取 [{len(all_prayers)+1}/{limit}]: {title_text}")
                detail = fetch_prayer_detail(article_url)
                if not detail:
                    continue

                new_prayer = {
                    "id": date_id,
                    "date": date_str,
                    "topic": topic_str,
                    "scripture": detail["scripture"],
                    "shareParagraphs": detail["shareParagraphs"],
                    "prayerFocus": "請參閱本週聚會分享與同心守望代禱事項。",
                    "prayers": detail["prayers"],
                    "churchIntercessions": detail["churchIntercessions"],
                    "meditation": "本週如何將神的話語落實在日常生活中？"
                }

                all_prayers.append(new_prayer)

            page += 1
        except Exception as e:
            print(f"讀取頁面失敗: {e}")
            break

    return all_prayers

def update_json():
    print("開始執行歷史資料抓取與解析...")
    prayers_list = fetch_batch_prayers(limit=20)
    
    if prayers_list:
        with open('prayers.json', 'w', encoding='utf-8') as f:
            json.dump(prayers_list, f, ensure_ascii=False, indent=2)
        print(f"成功！已將 {len(prayers_list)} 篇禱告日誌寫入 prayers.json。")
    else:
        print("未抓取到任何資料。")

if __name__ == '__main__':
    update_json()
