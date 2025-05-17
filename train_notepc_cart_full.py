import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, export_text, plot_tree
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, FunctionTransformer
import matplotlib.pyplot as plt


def main():
    df = pd.read_csv("notepc_ranking_full.csv")
    df = df.dropna(subset=["sold_or_not", "storage"])
    df["sold_or_not"] = df["sold_or_not"].astype(int)

    # 特徴量定義
    numeric_feats = ["price", "cpu_score", "memory", "storage", "weight", "size"]
    # maker と graphics を別々に処理
    maker_feat = ["maker"]
    gpu_feat   = ["graphics"]

    # 数値特徴量用パイプライン
    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
    ])

    # maker 用パイプライン: 欠損を'missing'に, One-Hot
    maker_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])

    # graphics 用パイプライン: 欠損->ブランド抽出->One-Hot
    def extract_gpu_brand(X):
        # X は ndarray shape=(n_samples,1)
        ser = pd.Series(X.ravel())
        brands = ser.str.extract(r"(NVIDIA|Intel|AMD)", expand=False).fillna("missing")
        return brands.to_frame().values

    gpu_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
        ("brand_extr", FunctionTransformer(extract_gpu_brand, validate=False)),
        ("onehot",    OneHotEncoder(handle_unknown="ignore")),
    ])

    # ColumnTransformer で列ごとに分岐
    preprocessor = ColumnTransformer([
        ("num",   numeric_pipeline, numeric_feats),
        ("maker", maker_pipeline,   maker_feat),
        ("gpu",   gpu_pipeline,     gpu_feat),
    ])

    # モデルパイプライン
    clf = Pipeline([
        ("prep", preprocessor),
        ("tree", DecisionTreeClassifier(
            criterion="gini",
            max_depth=4,
            min_samples_leaf=3,
            random_state=42
        )),
    ])

    # 学習データとテストデータに分割
    X = df[numeric_feats + maker_feat + gpu_feat]
    y = df["sold_or_not"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42
    )

    # 学習
    clf.fit(X_train, y_train)
    print(f"Train acc: {clf.score(X_train, y_train):.3f}")
    print(f" Test acc: {clf.score(X_test,  y_test):.3f}\n")

    # 決定木ルールのテキスト出力
    tree = clf.named_steps["tree"]
    # 前処理後の特徴名を集める
    ohe_maker = clf.named_steps["prep"] \
                 .named_transformers_["maker"] \
                 .named_steps["onehot"]
    maker_cols = ohe_maker.get_feature_names_out(maker_feat)

    ohe_gpu   = clf.named_steps["prep"] \
                 .named_transformers_["gpu"] \
                 .named_steps["onehot"]
    gpu_cols = ohe_gpu.get_feature_names_out(gpu_feat)

    feature_names = numeric_feats + list(maker_cols) + list(gpu_cols)
    print(export_text(tree, feature_names=feature_names))

    # 決定木描画
    plt.figure(figsize=(10, 6))
    plot_tree(tree,
              feature_names=feature_names,
              class_names=["not sold","sold"],
              filled=True, rounded=True,
              max_depth=4)
    plt.title("NotePC CART (full features, Gini)")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
