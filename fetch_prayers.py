import json
import re
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

# 博愛浸信會禱告日誌分類頁面
URL = "https://www.boai.org.tw/about-us/itemlist/category/279.html"


def fetch_latest_prayer():
    req = Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    html = urlopen(req).read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")

    # 找到最新的文章連結
    latest_item = soup.select_size = soup.find(
        "div", class_="catItemHeader"
    ) or soup.find("h3", class_="catItemTitle")
    if not latest_item:
        print("未找到文章標題")
        return None

    link_tag = latest_item.find("a")
    article_url = "https://www.boai.org.tw" + link_tag["href"]
    title_text = link_tag.text.strip()

    # 抓取該篇文章詳細內容
    req_article = Request(article_url, headers={"User-Agent": "Mozilla/5.0"})
    html_article = urlopen(req_article).read().decode("utf-8")
    soup_article = BeautifulSoup(html_article, "html.parser")

    content_div = soup_article.find("div", class_="itemFullText")
    if not content_div:
        content_div = soup_article.find("div", class_="itemIntroText")

    paragraphs = [
        p.text.strip() for p in content_div.find_all("p") if p.text.strip()
    ]

    # 解析標題中的日期與主題 (例如: 2026.9.13-9.19 讓基督的平安在心裡作主)
    date_match = re.search(r"(\d{4}\.\d{1,2}\.\d{1,2}-\d{1,2}\.\d{1,2})", title_text)
    date_str = date_match.group(1) if date_match else "最新聚會"
    topic_str = (
        title_text.replace(date_str, "").strip() if date_match else title_text
    )

    # 提取 ID (用數字代表)
    date_id = (
        "prayer-" + re.sub(r"\D", "", date_str.split("-")[0])
        if date_match
        else "prayer-latest"
    )

    # 組合 JSON 結構
    new_prayer = {
        "id": date_id,
        "date": date_str,
        "topic": topic_str,
        "scripture": paragraphs[0] if len(paragraphs) > 0 else "詳見官網文章",
        "shareParagraphs": (
            paragraphs[1:4] if len(paragraphs) >= 4 else paragraphs
        ),
        "prayerFocus": "請參閱本週聚會分享與代禱事項。",
        "prayers": [
            {
                "title": "1. 為自己禱告",
                "text": "請參照官網禱告手冊導引進行個人尋求與宣告。",
            },
            {
                "title": "2. 為教會禱告",
                "text": "求主聖靈大能充滿教會，同心合意活出榮耀見證。",
            },
            {
                "title": "3. 為國度禱告",
                "text": "為世代復興、國家平安與全國嚴肅會守望禱告。",
            },
        ],
        "churchIntercessions": [
            "裝備課與聚會順利進行",
            "為各區嚴肅會與代禱者訓練守望",
            "母堂及各分堂病患經歷神醫治大能",
        ],
        "meditation": "本週如何將神的話語落實在日常生活中？",
    }

    return new_prayer


def update_json():
    new_data = fetch_latest_prayer()
    if not new_data:
        return

    try:
        with open("prayers.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []

    # 檢查是否已經存在相同 ID，若無則插入至最頂部
    if not any(item["id"] == new_data["id"] for item in data):
        data.insert(0, new_data)
        with open("prayers.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"成功更新聚會禱告：{new_data['date']} - {new_data['topic']}")
    else:
        print("最新聚會禱告已存在，無需重複更新。")


if __name__ == "__main__":
    update_json()