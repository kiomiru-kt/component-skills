# figma-tokenize.py 設計ドキュメント

**作成日**: 2026-04-13
**ステータス**: 設計確定（実装待ち）
**配置先**: `~/.claude/scripts/figma-tokenize.py`（グローバル）または `scripts/figma-tokenize.py`（プロジェクト）

---

## 概要

FigmaのComponentsページのNodeを走査してデザイントークン候補（色・font-size・line-height・border-radius・spacing）を集計し、SCSS変数定義のベースとなるJSONを生成するPythonスクリプト。

---

## アーキテクチャ

シングルファイル・`requests` のみ依存。グローバル配置との相性を優先。

### CLI

```bash
python3 figma-tokenize.py --file-id FILE_ID --output PATH [--page "Components"] [--threshold 3]
```

| 引数 | 必須 | デフォルト | 説明 |
|------|------|---------|------|
| `--file-id` | ✅ | - | FigmaファイルID |
| `--output` | ✅ | - | JSON出力パス（省略時はstdout） |
| `--page` | ❌ | `Components` | 走査対象ページ名 |
| `--threshold` | ❌ | `3` | トークン候補とみなす最小出現回数 |

**環境変数:** `FIGMA_TOKEN`（未設定時はエラー終了）

### 内部クラス構成

```
FigmaClient       REST API呼び出し（認証・リトライ）
VariableResolver  Figma Variables取得・既定義トークンのマップ生成
NodeScanner       Componentsページ走査・値の出現回数集計
TokenNamer        カテゴリ+値からSCSS変数名を推測
TokenBuilder      集計結果をJSONスキーマに整形・重複排除
main()            CLI・ファイル出力
```

---

## データフロー

```
1. FigmaClient
   GET /v1/files/{file_id}?depth=2
   → ページ一覧からComponents pageのIDを特定

2. VariableResolver
   GET /v1/files/{file_id}/variables/local
   → 既定義Variables（色・サイズ）をマップに格納
   → { "#1A1A1A" -> "color/base", "16px" -> "size/md", ... }
   ※ 403（有料プラン制限）の場合は警告を出してVariablesなしで続行

3. NodeScanner
   GET /v1/files/{file_id}/nodes?ids={components_page_id}
   → 全Nodeを再帰的に走査して値を集計

   収集するAPIフィールド:
   | カテゴリ | Figma APIフィールド |
   |---------|------------------|
   | color | fills[].color（type=SOLID） |
   | font-size | style.fontSize |
   | line-height | style.lineHeightPx |
   | border-radius | cornerRadius（0は除外） |
   | spacing | paddingLeft/Right/Top/Bottom, itemSpacing |

4. TokenBuilder
   - 出現回数 >= threshold の値のみ残す
   - VariableResolverのマップと照合
     - 定義済み → source: "figma_variable"、figma_nameをキーに使用
     - 未定義   → source: "node"、TokenNamerで名前を生成
   - JSON整形・出力
```

---

## 出力JSONスキーマ

```json
{
  "meta": {
    "file_id": "xxx",
    "page": "Components",
    "threshold": 3,
    "generated_at": "2026-04-13T11:00:00"
  },
  "colors": {
    "color-black": { "value": "#1a1a1a", "count": 8, "source": "node" },
    "color/main":  { "value": "#e60000", "count": 5, "source": "figma_variable" }
  },
  "font-size": {
    "font-size-base": { "value": "1rem", "count": 12, "source": "node" }
  },
  "line-height": {
    "line-height-normal": { "value": 1.6, "count": 6, "source": "node" }
  },
  "border-radius": {
    "radius-sm": { "value": "4px", "count": 4, "source": "node" }
  },
  "spacing": {
    "spacing-md": { "value": "1rem", "count": 9, "source": "node" }
  }
}
```

---

## TokenNamer 命名ロジック

### colors

| 条件 | 生成名 |
|------|--------|
| 明度 < 10% | `color-black` |
| 明度 > 95% | `color-white` |
| 彩度が低い（グレー系） | `color-gray-{明度0-100}` |
| 彩度が高い（色相で判定） | `color-{red/orange/yellow/green/blue/purple}` |
| 同カテゴリで名前衝突 | `-01` / `-02` サフィックスを付与 |

### font-size（px → rem 変換 ÷16）

| rem値 | 生成名 |
|-------|--------|
| < 0.75 | `font-size-xs` |
| 0.75–0.875 | `font-size-sm` |
| 0.875–1.125 | `font-size-base` |
| 1.125–1.375 | `font-size-md` |
| 1.375–1.75 | `font-size-lg` |
| 1.75–2.25 | `font-size-xl` |
| > 2.25 | `font-size-2xl` |
| 同スケールで複数値 | `font-size-lg-01` / `font-size-lg-02` |

### line-height（比率）

| 値 | 生成名 |
|----|--------|
| < 1.3 | `line-height-tight` |
| 1.3–1.5 | `line-height-snug` |
| 1.5–1.7 | `line-height-normal` |
| > 1.7 | `line-height-loose` |

### border-radius

| px値 | 生成名 |
|------|--------|
| 0 | **抽出しない**（デフォルト値のため） |
| 1–3 | `radius-xs` |
| 4–6 | `radius-sm` |
| 7–12 | `radius-md` |
| 13–20 | `radius-lg` |
| > 20 または 9999 | `radius-full` |

### spacing（px → rem 変換 ÷16）

| rem値 | 生成名 |
|-------|--------|
| ≤ 0.25 | `spacing-xs` |
| 0.25–0.625 | `spacing-sm` |
| 0.625–1.125 | `spacing-md` |
| 1.125–1.75 | `spacing-lg` |
| 1.75–2.5 | `spacing-xl` |
| > 2.5 | `spacing-2xl` |

**共通:** 同一スケール内で複数の異なる値が衝突した場合は `-01` / `-02` を付与。

---

## エラーハンドリング・終了コード

| 状況 | 挙動 | 終了コード |
|------|------|---------|
| `FIGMA_TOKEN` 未設定 | エラーメッセージ出力して即終了 | `1` |
| `--file-id` / `--output` 未指定 | argparse の usage を表示して終了 | `2` |
| Figma API 認証エラー（401） | 「FIGMA_TOKEN を確認してください」と出力 | `1` |
| Figma API レート制限（429） | 最大3回リトライ（指数バックオフ）、失敗なら終了 | `1` |
| `Components` ページが見つからない | 「--page オプションでページ名を指定してください」と出力 | `1` |
| 該当カテゴリが threshold 未満で全件除外 | 警告出力（stderr）、空カテゴリとしてJSON出力 | `0` |
| Figma Variables API が 403 | 警告出力してVariablesなしで続行 | `0` |
| 出力ディレクトリが存在しない | 自動作成して出力 | `0` |

**stderr / stdout の分離:**
- 通常ログ・警告 → `stderr`
- JSON出力（`--output` 指定時）→ ファイル
- `--output` 省略時 → `stdout`（パイプ対応）

---

## 依存ライブラリ

```
requests  # pip install requests のみ
```

Python標準ライブラリ（`argparse` / `json` / `os` / `datetime` / `colorsys`）を最大限活用。
