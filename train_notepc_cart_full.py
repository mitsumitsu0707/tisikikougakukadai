# train_notepc_cart_full.py

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, export_text, plot_tree
import matplotlib.pyplot as plt

def main():
    # 1) CSV 読み込み
    df = pd.read_csv("notepc_ranking_full.csv")

    # 2) ラベル付け：上位 10 → sold=1、それ以外は sold=0
    df["sold"] = df["rank"].apply(lambda r: 1 if r <= 10 else 0)

    # 3) price が取れている行だけ残す
    df = df.dropna(subset=["price"])

    # 4) 特徴量／ターゲット
    X = df[["price"]]
    y = df["sold"]

    # 5) 学習データ／テストデータに分割
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    # 6) 決定木モデルを定義・学習（criterion を "gini" に）
    clf = DecisionTreeClassifier(
        criterion="gini",
        max_depth=4,
        random_state=42
    )
    clf.fit(X_train, y_train)

    # 7) 精度を表示
    print(f"Train accuracy: {clf.score(X_train, y_train):.3f}")
    print(f" Test accuracy: {clf.score(X_test,  y_test):.3f}\n")

    # 8) ルールをテキストで出力
    rules = export_text(clf, feature_names=["price"])
    print("Decision tree rules:\n", rules)

    # 9) 決定木を可視化
    plt.figure(figsize=(8, 6))
    plot_tree(
        clf,
        feature_names=["price"],
        class_names=["not sold", "sold"],
        filled=True,
        rounded=True
    )
    plt.title("NotePC CART (price only, Gini)")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
