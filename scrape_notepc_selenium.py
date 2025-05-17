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
        time.sleep(2)

        blocks = driver.find_elements(By.CSS_SELECTOR, "div.rkgBox")
        if not blocks:
            break

        for blk in blocks:
            try:
                # product & maker
                product = blk.find_element(By.CSS_SELECTOR, ".rkgBoxNameItem").text.strip()
                maker   = blk.find_element(By.CSS_SELECTOR, ".rkgBoxNameMaker").text.strip()
                # rank は sold_or_not を決めるのに later で使います
                rank_txt = blk.find_element(By.CSS_SELECTOR, ".rkgBoxNum .num").text
                rank     = int(rank_txt)
                # price
                price_txt = blk.find_element(By.CSS_SELECTOR, ".rkgPrice .price").text
                price     = int(re.sub(r"[^\d]", "", price_txt))
                # 発売日（例: "発売日2023年 6月 7日"）
                date_txt = blk.find_element(By.CSS_SELECTOR, ".rkgRow.rowLower .rkgDate").text
                m_date   = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", date_txt)
                if m_date:
                    date = f"{m_date.group(1)}-{int(m_date.group(2)):02d}-{int(m_date.group(3)):02d}"
                else:
                    date = None
                # detail text (スペックが凝縮されている部分)
                detail = blk.find_element(By.CSS_SELECTOR, ".rkgRow.rowDetail").text

                # — CPU スコア抽出 (PassMark)
                m_cpu = re.search(r"PassMark.*?([0-9,]+)", detail)
                cpu_score = int(m_cpu.group(1).replace(",", "")) if m_cpu else None

                # — ビデオチップ（GPU）抽出（detail テキストから一発正規表現）
                graphics = None
                # detail の先頭に、
                #   画面サイズ：… CPU：… メモリ容量：… ビデオチップ：XXX OS：…
                # と続いているので、「ビデオチップ：」〜「OS」の間を抜き出す
                m_gpu = re.search(r"ビデオチップ[:：]?\s*(.+?)\s+OS", detail)
                if m_gpu:
                    graphics = m_gpu.group(1).strip()

                # — Memory 抽出
                memory = None
                # 1) まず製品名に “XXGBメモリ” が入っていればそれを優先
                m1 = re.search(r"(\d+)\s*GBメモリ", product)
                if m1:
                    memory = int(m1.group(1))
                else:
                    # 2) なければ詳細リストから探す
                    for li in blk.find_elements(By.CSS_SELECTOR, "ul.rkgDetailList li"):
                        t = li.text
                        m2 = re.search(r"(\d+)\s*GBメモリ", t)
                        if m2:
                            memory = int(m2.group(1))
                            break

                # — ストレージ（SSD/HDD）抽出（GB/TB対応）
                storage = None
                # 1) 製品名に "512GB SSD" や "1TB SSD" があればそちらを優先
                m_store = re.search(
                    r"(\d+(?:\.\d+)?)\s*(GB|TB)\s*(?:SSD|HDD)",
                    product, re.IGNORECASE
                )
                if m_store:
                    num, unit = float(m_store.group(1)), m_store.group(2).upper()
                    storage = int(num * (1024 if unit == "TB" else 1))
                else:
                    # 2) なければ detail テキストから「ストレージ容量：…GB/TB」を探す
                    m_store2 = re.search(
                        r"ストレージ容量[:：]?\s*(?:[^:]+:)?\s*(\d+(?:\.\d+)?)\s*(GB|TB)",
                        detail, re.IGNORECASE
                    )
                    if m_store2:
                        num, unit = float(m_store2.group(1)), m_store2.group(2).upper()
                        storage = int(num * (1024 if unit == "TB" else 1))

                # — Weight 抽出
                m_w = re.search(r"([0-9\.]+)\s*kg", detail)
                weight = float(m_w.group(1)) if m_w else None

                # — Size (インチ) 抽出
                m_s = re.search(r"([0-9\.]+)(?:インチ|型)", detail)
                size = float(m_s.group(1)) if m_s else None

                # — sold_or_not ラベル付け (rank ≤ 10 → sold, 31 ≤ rank → not sold)
                if rank <= 10:
                    sold_or_not = 1
                elif rank >= 41:
                    sold_or_not = 0
                else:
                    sold_or_not = None

                products.append({
                    "product":      product,
                    "maker":        maker,
                    "price":        price,
                    "date":         date,
                    "cpu_score":    cpu_score,
                    "graphics":     graphics,
                    "memory":       memory,
                    "storage":      storage,   
                    "weight":       weight,
                    "size":         size,
                    "sold_or_not":  sold_or_not
                })
            except Exception:
                # 取得に失敗した項目がある行はスキップ
                continue

    driver.quit()
    return pd.DataFrame(products)

def main():
    df = fetch_listing(max_page=4)  # ページ数はお好みで
    if df.empty:
        print("データが取得できませんでした。CSSセレクタ／正規表現を要確認。")
        return

    # sold_or_not が None の行 (11～30位) は除外するなら
    df = df.dropna(subset=["sold_or_not"])

    # 列の順序を明示的に指定
    df = df[
        ["product", "maker", "price", "date",
         "cpu_score", "graphics", "memory", "storage",
         "weight", "size", "sold_or_not"]
    ]

    df.to_csv("notepc_ranking_full.csv", index=False, encoding="utf-8-sig")
    print(f"保存完了: notepc_ranking_full.csv （{len(df)} 件）")

if __name__ == "__main__":
    main()
