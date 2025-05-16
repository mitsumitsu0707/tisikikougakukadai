# scrape_notepc_selenium.py

import re, time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# ページ番号を受け取るテンプレートURL
URL_TEMPLATE = "https://kakaku.com/pc/note-pc/ranking_0020/?page={}"

def fetch_listing(max_page=4):
    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opts
    )

    products = []
    for page in range(1, max_page+1):
        driver.get(URL_TEMPLATE.format(page))
        time.sleep(2)  # ページ切り替え後の読み込み待ち

        blocks = driver.find_elements(By.CSS_SELECTOR, "div.rkgBox")
        # ページにアイテムがなければそこまでで打ち切り
        if not blocks:
            break
        for blk in blocks:
            try:
                rank_txt  = blk.find_element(By.CSS_SELECTOR, ".rkgBoxNum .num").text
                rank      = int(rank_txt)
                name      = blk.find_element(By.CSS_SELECTOR, ".rkgBoxNameItem").text.strip()
                price_txt = blk.find_element(By.CSS_SELECTOR, ".rkgPrice .price").text
                price     = int(re.sub(r"[^\d]", "", price_txt))
            except:
                continue
            products.append({"rank": rank, "name": name, "price": price})

    driver.quit()
    return pd.DataFrame(products)

def main():
    # たとえば max_page=4 とすれば約40件取得
    df = fetch_listing(max_page=4)
    if df.empty:
        print("データが取得できませんでした。CSSセレクタを要確認。")
    else:
        df.to_csv("notepc_ranking_full.csv", index=False, encoding="utf-8-sig")
        print(f"保存完了: notepc_ranking_full.csv （{len(df)} 件）")

if __name__ == "__main__":
    main()
