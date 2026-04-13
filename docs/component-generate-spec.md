# component-generate スキル仕様書

**作成日**: 2026-04-09  
**ステータス**: 設計確定（スキル実装待ち）  
**関連ドキュメント**: figma-properties.md, docs/scss-guidelines.md, docs/theme-architecture.md

---

## 概要

spec-builderが生成した仕様書、またはFigmaノードURLを元に、  
WordPressテーマのコンポーネントファイル（PHP + SCSS）を生成するスキル。

---

## 入力

以下のいずれかを受け取る：

| 入力 | 処理 |
|------|------|
| Figmaノードid / URL | Figma MCPで設計データを取得し、プロパティを解釈して生成 |
| `docs/specs/{name}/implementation.md` | 仕様書を読んで生成 |
| 対話形式 | 情報を収集して生成 |

---

## 生成ファイル

| ファイル | 配置先 |
|---------|-------|
| `{name}.php` | `include/component/{name}.php` |
| `_{name}.scss` | `src/scss/object/component/_{name}.scss` |
| `_index.scss` | `@use` を自動追記 |
| `docs/components/index.md` | コンポーネント情報を自動追記 |

---

## 処理フロー

### Step 1: 既存コンポーネントの確認

実装前に必ず `docs/components/index.md` を確認する。

- 同一または類似のコンポーネントが存在する → 新規作成せず既存を使用
- 部分的に再利用できる → エンジニアに確認してから判断
- 該当なし → 新規作成へ進む

### Step 2: Figmaデータの解釈（Figma URLがある場合）

`get_design_context` でノード構造を取得し、`figma-properties.md` の規則に従って解釈する。

**解釈の優先順位：**

1. Figmaのコンポーネント名・フレーム名にBEMクラス（`c-xxx`）が明示 → そのまま採用
2. `device` / `size` / `state` / `align` / `color` プロパティを読み取り → バリアント構造を把握
3. `role` / `render` / `tag` プロパティを読み取り → HTML構造・CSS実装方法を決定
4. `data` / `lang` プロパティを読み取り → HTML属性を付与

未知のプロパティが登場した場合は推測で実装せず、エンジニアに確認する。

### Step 3: utilityクラスの確認

`align` / `color` プロパティが含まれる場合：

1. `src/scss/object/utility/` を走査してutilityクラスの存在を確認
2. 存在する → utilityクラスを使用
3. 存在しない → BEM modifierの追加案をエンジニアに提示し、承認を得てから実装

レイアウト系（`display`・`margin`・`padding`等）のutilityクラスは作成しない。

### Step 4: PHP生成

**規約（必須）：**

- ファイル先頭に以下のコメントブロックを記載する

```php
<?php
/**
 * Component: {BEMクラス名}
 * 用途: {1行の説明}
 */
```

- `wp_parse_args($args, $defaults)` パターンで引数を受け取る
- 全出力に `esc_html()` / `esc_attr()` / `esc_url()` を適用する
- `<img>` タグには `loading="lazy"` `decoding="async"` を必ず付与する
- `<picture>` タグはWebP `<source>` + フォールバック `<img>` の構成にする
- `<video>` タグには `playsinline` を付与し、autoplayの場合は `muted` を追加する
- `<a tag=out>` は `target="_blank" rel="noopener noreferrer"` を自動付与する
- `render=::after/::before/::bg-image` が指定された要素はHTMLに出力しない

### Step 5: SCSS生成

**規約（必須）：**

- ファイル先頭に以下のコメントブロックを記載する

```scss
// Component: {BEMクラス名}
// 用途: {1行の説明}
```

- BEM命名：`.c-{name}` / `.c-{name}__element` / `.c-{name}--modifier`
- `device=pc/sp` が両方存在する → fluid関数（`fluid-font-rem` / `fluid-space-rem`）で実装。メディアクエリを使用しない
- `device=pc` または `device=sp` のみ存在する → そのデバイスのスタイルをデフォルトとして実装。メディアクエリ不使用
- fluid関数で表現できない差分がある場合のみ `@include mq(pc)` を使用する
- `render=::after` / `::before` → 疑似要素で実装。HTMLには要素を出力しない
- `render=::bg-image` → `background-image: image-set()` で実装。`src-2x` がない場合は `src` のみ
- `role=decoration,style=line` → `border-style: solid`
- `role=decoration,style=dotted` → `border-style: dotted`
- カラーはCSS変数参照（`var(--c-*)`）
- サイズはrem / fluid関数を使用。1pxラインなどデザイン上適切な場合のみpxを使用

### Step 6: `_index.scss` への追記

`src/scss/object/component/_index.scss` に `@use` を追記する。

### Step 7: `docs/components/index.md` への追記

以下の形式で追記する：

```markdown
| {BEMクラス} | {PHPパス} | {SCSSパス} | {用途} |
```

---

## 自己検証チェック（生成後に必ず実行）

- [ ] `npm run lint` がエラーゼロ
- [ ] PHP：全出力に `esc_*` が適用されているか
- [ ] PHP：`loading="lazy"` `decoding="async"` が `<img>` に付与されているか
- [ ] SCSS：pxの直書きがないか（1px除く）
- [ ] SCSS：fluid関数が使用されているか（`device` が両方ある場合）
- [ ] SCSS：`render=::after/::before` の要素がHTMLに出力されていないか
- [ ] `docs/components/index.md` に追記されているか

---

## 未解決事項（実装時に検討）

- [ ] `picture` タグ生成時のWebP/フォールバックのパス規則
- [ ] `video` タグのposter画像対応
- [ ] コンポーネントの依存関係（c-btnを内包するc-card等）の扱い
