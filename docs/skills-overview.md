# kiomiru スキル概要

**作成日**: 2026-04-09  
**スキル配置**: `~/.claude/skills/` （グローバル）

| スキル | 配置パス |
|--------|--------|
| figma-extract | `~/.claude/skills/figma-extract/` |
| figma-tokenize | `~/.claude/skills/figma-tokenize/` |
| spec-builder | `~/.claude/skills/spec-builder/` |
| component-generate | `~/.claude/skills/component-generate/` |

---

## スキルの実行フロー（案件全体）

```
【案件着手時】
figma-extract
（Figmaコンポーネント整理・バリアント構築）
    ↓ 連続実行
figma-tokenize
（デザイントークン抽出）
    ↓ エンジニアがBEMクラス名を確認・確定

【実装時（コンポーネント毎）】
spec-builder
（仕様書・実装指示書生成）
    ↓
component-generate
（PHP + SCSS生成）
```

---

## スキル一覧

### figma-extract

**一言で言うと**: FigmaのComponentsページを走査し、コンポーネントを整理・バリアント構築するスキル

**いつ使う**: 案件着手時、Figmaのコンポーネント整理が必要なとき

**エンジニアの事前準備**:
- Figmaの `Components` ページにコンポーネント候補を配置
- コンポーネント名はBEM名（例: `heading-01`）
- バリアントフレームは `figma-properties.md` のプロパティ記法で命名
  （例: `device=sp,align=left,color=main` / `device=pc,state=hover`）

**AIがやること**:
- 同一コンポーネント名のフレームをグループ化
- Figma上にコンポーネントセット・バリアントプロパティを構築
- 完了後にfigma-tokenize（Pythonスクリプト）を連続実行してバリアブル抽出

**参照ドキュメント**: `~/.claude/figma-properties.md`（グローバル）

---

### figma-tokenize

**一言で言うと**: FigmaからデザイントークンをPythonスクリプトで抽出し、SCSS変数用のJSONを生成するスキル

**いつ使う**: figma-extract完了直後に自動実行（単体でも使用可）

**AIがやること**:
- Pythonスクリプトを実行してFigma REST APIからデータ取得
- 色・サイズ・スペーシングの重複を検出（3箇所以上が対象）
- バリアブル候補をJSONで出力
- LLMは「Pythonの実行と結果受け取り」のみ担当（解釈はスクリプトが行う）

---

### spec-builder

**一言で言うと**: ページ・コンポーネント・機能単位の実装仕様書と実装指示書を生成するスキル

**いつ使う**: 実装着手前。Claude Codeが「何を・どう作るか」を把握するための仕様書が必要なとき

**3つの対応モード**:
- Figma URLあり → Figma MCPで自動取得して生成
- Figma URLなし → 対話形式（FAQ）で情報収集して生成
- 機能単位（検索・スライダー等）→ `docs/features/{name}.md` を参照して生成

**AIがやること**:
- 機能キーワードを検出して対応するリファレンスドキュメントを自動参照
- コンポーネント選択ルールに基づき既存コンポーネントの再利用を優先
- `docs/specs/{name}/spec.md` `implementation.md` `checklist.md` を生成

**参照ドキュメント**: `~/.claude/figma-properties.md`（グローバル）/ `docs/features/*.md`（プロジェクト）/ `docs/components/index.md`（プロジェクト）

---

### component-generate

**一言で言うと**: spec-builderの仕様書またはFigmaノードURLからPHP + SCSSのコンポーネントファイルを生成するスキル

**いつ使う**: コンポーネントの実装時

**AIがやること**:
- 既存コンポーネント（`docs/components/index.md`）を確認して重複作成を防ぐ
- `figma-properties.md` の規則に従ってFigmaプロパティを解釈
- PHPテンプレートパーツ（`include/component/{name}.php`）を生成
- SCSSパーシャル（`src/scss/object/component/_{name}.scss`）を生成
- `_index.scss` に `@use` を自動追記
- `docs/components/index.md` にコンポーネント情報を自動追記

**参照ドキュメント**: `~/.claude/figma-properties.md`（グローバル）/ `docs/components/index.md`（プロジェクト）

---

## ドキュメントの配置

### グローバル（`~/.claude/`）

全案件共通の規則。ここを更新すれば全案件に即反映。

| ファイル | 内容 |
|---------|------|
| `~/.claude/figma-properties.md` | Figmaプロパティ命名規則 |

### プロジェクト（`docs/`）

案件ごとに育てるドキュメント。テンプレートからコピーして使う。

| ファイル | 内容 | 初期状態 |
|---------|------|---------|
| `docs/components/index.md` | 既存コンポーネント一覧 | 案件開始時に自動生成 |
| `docs/features/*.md` | 機能別実装リファレンス | テンプレートのみ・案件で育てる |
| `docs/scss-guidelines.md` | SCSS規約 | テンプレートにコミット済み |
| `docs/theme-architecture.md` | テーマ設計規約 | テンプレートにコミット済み |
