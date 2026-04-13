# component-skills

Claude Code 向けスキル集。Figma MCP・WordPress テーマ開発に特化した 4 つのスキルと、デザイントークン抽出スクリプトを提供します。

---

## スキル一覧

| スキル | 起動トリガー | 概要 |
|--------|------------|------|
| `figma-extract` | 「figma-extract」「Figmaバリアント構築」 | Figma の Components ページを走査し、フレーム名の `{key}={value}` 構文を解析してバリアントを整理 |
| `figma-tokenize` | 「figma-tokenize」「デザイントークン抽出」 | `scripts/figma-tokenize.py` を実行し、色・フォントサイズ・スペーシング等のトークン候補を JSON で出力 |
| `spec-builder` | 「仕様書を作って」「{名前}の仕様書」 | Figma URL または対話形式でページ・コンポーネントの実装仕様書（spec.md / implementation.md / checklist.md）を生成 |
| `component-generate` | 「コンポーネントを作って」「{名前}を実装して」 | 仕様書または Figma URL から WordPress テーマの PHP + SCSS コンポーネントを生成 |

---

## インストール

### 1. リポジトリをクローン

```bash
git clone https://github.com/kiomiru-kt/component-skills.git ~/.claude/component-skills
```

### 2. スキルをシンボリックリンクで登録

```bash
mkdir -p ~/.claude/skills ~/.claude/scripts

for skill in figma-extract figma-tokenize spec-builder component-generate; do
    ln -sf ~/.claude/component-skills/skills/$skill ~/.claude/skills/$skill
done

ln -sf ~/.claude/component-skills/scripts/figma-tokenize.py ~/.claude/scripts/figma-tokenize.py
```

### 3. figma-properties.md をグローバルに配置

```bash
cp ~/.claude/component-skills/docs/figma-properties.md ~/.claude/figma-properties.md
```

### 4. Python 依存パッケージをインストール（figma-tokenize 使用時のみ）

```bash
cd ~/.claude/component-skills
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

---

## 使い方

### figma-extract

Figma MCP が接続済みの状態で、Components ページの URL またはファイル ID を伝えるだけで起動します。

```
figma-extractで https://www.figma.com/design/XXXXX を解析して
```

- フレーム名の `device=pc` / `device=sp` / `state=hover` 等を解析してバリアント構造を把握
- 完了後に `figma-tokenize` を自動で呼び出してトークン抽出へ連携
- 監査レポートを `docs/figma-audit/components-{date}.md` に出力

### figma-tokenize

```bash
# スクリプトを直接実行
FIGMA_TOKEN=your_token python3 scripts/figma-tokenize.py \
  --file-id FILE_ID \
  --output tokens.json \
  --page "Components" \
  --threshold 3
```

Claude Code 上では「figma-tokenize を実行して」と伝えるとスキルが起動し、プロジェクトの `scripts/figma-tokenize.py` を優先して実行します（なければグローバルの `~/.claude/scripts/figma-tokenize.py` を使用）。

**出力 JSON の構造:**

```json
{
  "meta": { "file_id": "...", "page": "Components", "threshold": 3, "generated_at": "..." },
  "colors": {
    "color-black":  { "value": "#0a0a0a", "count": 8, "source": "node" },
    "color/main":   { "value": "#e60000", "count": 5, "source": "figma_variable" }
  },
  "font-size":      { "font-size-base": { "value": "1rem",  "count": 12, "source": "node" } },
  "line-height":    { "line-height-normal": { "value": 1.6, "count": 6,  "source": "node" } },
  "letter-spacing": { "letter-spacing-wide": { "value": "5.0%", "count": 4, "source": "node" } },
  "border-radius":  { "radius-sm": { "value": "4px", "count": 4, "source": "node" } },
  "spacing":        { "spacing-md": { "value": "1rem", "count": 9, "source": "node" } }
}
```

**環境変数:** `FIGMA_TOKEN` を設定してください（Figma の Personal Access Token）。

### spec-builder

Figma URL があれば Mode A（自動取得）、なければ Mode B（対話形式）で動作します。

```
このFigmaを元に仕様書を作って: https://www.figma.com/design/XXXXX?node-id=1:23
```

`docs/specs/{feature-name}/` に以下の 3 ファイルを生成します:

- `spec.md` — レスポンシブ仕様・データ設計・コンポーネント一覧を含む仕様書
- `implementation.md` — ファイルパスと具体的な実装手順を記載した実装指示書
- `checklist.md` — 実装・品質・ドキュメントの完了チェックリスト

### component-generate

```
c-card コンポーネントを実装して
```

`docs/specs/c-card/implementation.md` がある場合は仕様書モードで、なければ Figma URL または対話形式で情報を収集して以下のファイルを生成します:

- `include/component/card.php`
- `src/scss/object/component/_card.scss`
- `src/scss/object/component/_index.scss`（`@use` 自動追記）
- `docs/components/index.md`（コンポーネント一覧に追記）

---

## 前提条件

- Claude Code（MCP が利用可能な環境）
- Figma MCP（`figma-extract` / `figma-tokenize` / `component-generate` の Figma モード使用時）
- Python 3.9+（`figma-tokenize.py` 使用時）
- `FIGMA_TOKEN` 環境変数（Figma REST API を直接叩く場合）

---

## テスト（figma-tokenize.py）

```bash
cd ~/.claude/component-skills
.venv/bin/python -m pytest tests/ -v
```

---

## ドキュメント

- `docs/figma-properties.md` — Figma フレームプロパティの命名規則
- `docs/figma-extract-spec.md` — figma-extract スキルの設計仕様
- `docs/spec-builder-spec.md` — spec-builder スキルの設計仕様
- `docs/component-generate-spec.md` — component-generate スキルの設計仕様
- `docs/skills-overview.md` — スキル全体の関係図と連携フロー
