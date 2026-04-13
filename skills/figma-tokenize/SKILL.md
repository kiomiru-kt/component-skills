---
name: figma-tokenize
description: >
  Pythonスクリプトを実行してFigmaからデザイントークンを抽出しSCSSのJSONを生成する。
  「figma-tokenize」「デザイントークン抽出」またはfigma-extractから自動連続実行されたときに起動。
  スクリプト実行と結果受け取りのみ担当。
version: 1.0.0
---

# figma-tokenize

Pythonスクリプトを実行してFigma REST APIからデザイントークン（色・サイズ・スペーシング）を抽出し、SCSS変数用のJSONを生成するスキル。

AIはスクリプトの実行と結果受け取りのみを担当する。トークンの解釈・選定はスクリプトが行う。

## 前提条件

- `~/.claude/scripts/figma-tokenize.py`（グローバル）またはプロジェクトの `scripts/figma-tokenize.py` が存在すること
- Figma REST API にアクセスできる環境変数（`FIGMA_TOKEN`）が設定されていること
- Python 3 が実行可能であること

---

## 実行フロー

### Step 1: スクリプトの解決

以下の優先順位でスクリプトを探す:

1. `scripts/figma-tokenize.py`（プロジェクトローカル） ← **優先**
2. `~/.claude/scripts/figma-tokenize.py`（グローバル） ← フォールバック

見つかった方を `{SCRIPT_PATH}` として以降のステップで使用する。

**どちらも存在しない場合 → 停止してエンジニアに案内:**

```
figma-tokenize.py が見つかりません。

以下のいずれかに配置してください:
  グローバル: ~/.claude/scripts/figma-tokenize.py
  プロジェクト: {プロジェクトルート}/scripts/figma-tokenize.py（グローバルより優先）

スクリプトのテンプレートは component-skills リポジトリを参照してください。
```

### Step 2: 環境変数の確認

`FIGMA_TOKEN` が設定されているか確認する。

**未設定の場合 → 停止:**

```
環境変数 FIGMA_TOKEN が設定されていません。
.env または shell の設定を確認してください。
```

### Step 3: Pythonスクリプトを実行

以下のコマンドを実行する:

```bash
python3 {SCRIPT_PATH} --file-id {figma-file-id} --output docs/figma-audit/tokens-{YYYY-MM-DD}.json
```

- `figma-file-id`: figma-extract から引き継ぐ、またはエンジニアが指定した値を使用
- AIはコマンドを実行し、終了コードと標準出力・標準エラーを受け取る

**実行エラーの場合:**

```
スクリプト実行中にエラーが発生しました:
{エラー内容}

スクリプトのログを確認し、問題を修正してから再実行してください。
```

### Step 4: 結果を受け取りサマリーを表示

スクリプトが出力したJSONを読み込み、以下のサマリーをエンジニアに提示する:

```
figma-tokenize 完了

抽出されたトークン候補:
- 色: {件数} 件（うち3箇所以上に登場: {件数} 件）
- サイズ: {件数} 件（うち3箇所以上に登場: {件数} 件）
- スペーシング: {件数} 件（うち3箇所以上に登場: {件数} 件）

出力ファイル: docs/figma-audit/tokens-{YYYY-MM-DD}.json

次のステップ:
BEMクラス名を確認・確定した後、component-generate スキルで実装に進んでください。
```

### Step 5: BEMクラス名の確認依頼

エンジニアに以下を依頼して終了する:

```
figma-extract で構築したコンポーネントセットのBEMクラス名を確認・確定してください。

確定後、実装を開始する場合は:
  spec-builder → component-generate の順で進めてください。
```

---

## エッジケース一覧

| 状況 | 対応 |
|------|------|
| プロジェクト・グローバルどちらにもスクリプトが存在しない | Step 1 で停止・配置方法を案内 |
| `FIGMA_TOKEN` 未設定 | Step 2 で停止・設定方法を案内 |
| Python 3 が未インストール | Step 3 のエラーをそのまま表示して停止 |
| スクリプト実行エラー | エラー内容を表示して停止（再試行・修正はエンジニアが対応） |
| 出力JSONが空 | 「トークンが検出されませんでした」と表示しエンジニアに確認 |
| `docs/figma-audit/` が存在しない | 自動作成してから出力 |

---

## 役割分担

| 処理 | 担当 |
|------|------|
| Figma REST API からのデータ取得 | Python スクリプト |
| 重複検出（3箇所以上） | Python スクリプト |
| JSON 生成・ファイル出力 | Python スクリプト |
| スクリプトの実行・結果受け取り | AI（このスキル） |
| BEMクラス名の最終確定 | エンジニア |

## トークン最適化

- AIはスクリプトの実行と結果受け取りのみ担当し、Figma REST APIを直接呼ばない
- トークン値の解釈・選定判断はスクリプトに委ねる（AIが独自に推論しない）
