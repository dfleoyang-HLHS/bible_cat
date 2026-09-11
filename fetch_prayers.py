def fetch_latest_9_prayers():
    driver = get_browser()
    print(f"正在開啟博愛浸信會官網: {BASE_URL}")
    driver.get(BASE_URL)
    time.sleep(3) # 首頁載入等待

    prayer_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '禱告專區')]")
    print(f"尋找到 {len(prayer_elements)} 個「禱告專區」相關標題！")

    all_prayers = []
    
    for idx, el in enumerate(prayer_elements[:12]):
        title_text = el.text.strip()
        if not title_text or "禱告專區" not in title_text:
            continue

        print(f"正在讀取 [{idx+1}]: {title_text}")

        try:
            # 第一篇預設已展開，不需要點擊（避免反而把第一篇關掉）；第二篇以後才點擊展開
            if idx > 0:
                driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", el)
                time.sleep(2.0)
            else:
                time.sleep(1.0) # 第一篇稍微停頓確保 DOM 穩定

            parent_container = el.find_element(By.XPATH, "./ancestor::*[contains(@class, 'catItem') or contains(@class, 'accordion') or contains(@class, 'toggle') or contains(@class, 'itemBody') or position()=2]")
            full_text = parent_container.text.strip()

            parsed_data = parse_exact_prayer_text(full_text, title_text)
            
            # 驗證資料品質
            if parsed_data['topic'] and len(full_text) > 50:
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
