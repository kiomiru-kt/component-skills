---
name: component-generate
description: >
  spec-builderの仕様書またはFigmaノードURLからWordPressテーマのPHP+SCSSコンポーネントを生成する。
  「コンポーネントを作って」「component-generate」「{name}を実装して」「{name}.phpを生成して」と言われたときに起動。
version: 1.0.0
---

# component-generate

spec-builderが生成した仕様書、またはFigmaノードURLを元に、WordPressテーマのコンポーネントファイル（PHP + SCSS）を生成するスキル。

## 生成ファイル

| ファイル | 配置先 |
|---------|-------|
| `{name}.php` | `include/component/{name}.php` |
| `_{name}.scss` | `src/scss/object/component/_{name}.scss` |
| `_index.scss` | `@use` を自動追記 |
| `docs/components/index.md` | コンポーネント情報を自動追記 |

---

## 実行フロー

### Step 1: 既存コンポーネントの確認

`docs/components/index.md` を参照し、同一または類似のコンポーネントが存在するか確認する。

**`docs/components/index.md` が存在しない場合:**

```
docs/components/index.md が見つかりません（初回案件の場合は正常です）。
既存コンポーネントの確認をスキップして新規作成として進めます。
```

**同一コンポーネントが存在する場合 → 停止:**

```
"{BEMクラス名}" はすでに存在します。
  PHP: {既存PHPパス}
  SCSS: {既存SCSSパス}

既存コンポーネントの修正ですか？ それとも別名で新規作成しますか？
```

**部分的に再利用できる場合 → 確認:**

```
類似コンポーネント "{BEMクラス名}" が存在します。
  用途: {既存の用途}
  PHP: {既存PHPパス}

既存を拡張しますか？ それとも新規作成しますか？
```

### Step 2: 入力の判定

以下の優先順位で入力を判定する:

| 入力 | 処理 |
|------|------|
| `docs/specs/{name}/implementation.md` が指定または存在 | **仕様書モード**：ファイルを読み込んで生成 |
| Figma ノード URL / node-id が指定 | **Figmaモード**：MCPでデータ取得して生成 |
| どちらも指定なし | **対話モード**：必要情報を1問ずつ収集して生成 |

### Step 3（Figmaモード）: Figmaデータの解釈

`~/.claude/figma-properties.md` を読み込み、プロパティ規則を把握する。

`get_design_context` でノード構造を取得し、以下の優先順位で解釈する:

1. Figmaのコンポーネント名・フレーム名に `c-xxx` が明示 → そのまま採用
2. `device` / `size` / `state` / `align` / `color` プロパティ → バリアント構造を把握
3. `role` / `render` / `tag` プロパティ → HTML構造・CSS実装方法を決定
4. `data` / `lang` プロパティ → HTML属性を付与

**未知のプロパティが登場した場合 → 推測せず停止:**

```
未知のプロパティ "{key}={value}" が含まれています（ノード: {ノード名}）。
~/.claude/figma-properties.md に定義がありません。

このプロパティをどう扱うか指示してください。
```

### Step 4: utilityクラスの確認

`align` / `color` プロパティが含まれる場合のみ実行する。

`src/scss/object/utility/` を走査してutilityクラスの存在を確認する:

- 存在する → utilityクラスを使用（SCSSに独自実装しない）
- 存在しない → BEM modifierの追加案をエンジニアに提示し、**承認を得てから実装**:

```
"{align/color}" に対応するutilityクラスが src/scss/object/utility/ に見つかりません。

以下のBEM modifierとして実装することを提案します:
  .c-{name}--{value}

この方針で進めてよいですか？
```

レイアウト系（`display` / `margin` / `padding` 等）のutilityクラスは作成しない。

### Step 5: PHPファイルを生成

`include/component/{name}.php` を生成する。

**必須規約:**

```php
<?php
/**
 * Component: {BEMクラス名}
 * 用途: {1行の説明}
 */

if ( ! function_exists( 'theme_{name}' ) ) :
function theme_{name}( $args = [] ) {
    $defaults = [
        // デフォルト値
    ];
    $args = wp_parse_args( $args, $defaults );
    ?>
    <!-- コンポーネントHTML -->
    <?php
}
endif;
```

| 要素 | 規約 |
|------|------|
| 文字列出力 | `esc_html()` を必ず適用 |
| 属性値出力 | `esc_attr()` を必ず適用 |
| URL出力 | `esc_url()` を必ず適用 |
| `<img>` | `loading="lazy" decoding="async"` を必ず付与 |
| `<picture>` | WebP `<source>` + フォールバック `<img>` の構成 |
| `<video>` | `playsinline` を付与、autoplayの場合は `muted` を追加 |
| `<a tag=out>` | `target="_blank" rel="noopener noreferrer"` を自動付与 |
| `lang=ja` / `lang=en` | `<html>` タグではなく**対象要素に `lang="ja"` / `lang="en"` 属性を付与**する。グローバルな言語切り替えは `<html lang="...">` で行い、コンポーネント内の部分的な言語指定にのみこの属性を使用する |
| `render=::after/::before/::bg-image` | HTMLに要素を出力しない |

### Step 6: SCSSファイルを生成

`src/scss/object/component/_{name}.scss` を生成する。

**必須規約:**

```scss
// Component: {BEMクラス名}
// 用途: {1行の説明}

.c-{name} {
    // スタイル

    &__element {
        // 要素
    }

    &--modifier {
        // 修飾
    }
}
```

| 状況 | 実装方針 |
|------|---------|
| `device=pc` と `device=sp` の両方が存在 | `fluid-font-rem` / `fluid-space-rem` で実装。メディアクエリ不使用 |
| `device=pc` または `device=sp` のみ | そのデバイスのスタイルをデフォルトとして実装。メディアクエリ不使用 |
| fluid関数で表現できない差分がある場合 | `@include mq(pc)` を使用（最小限に留める） |
| `width` / `height` / `margin` に SP・PC 差分がある | `fluid-space-rem` で実装する |
| `render=::after` / `::before` | 疑似要素で実装。HTMLに要素を出力しない |
| `render=::bg-image` | `background-image: image-set()` で実装 |
| `role=decoration,style=line` | `border-style: solid` |
| `role=decoration,style=dotted` | `border-style: dotted` |
| カラー | rem / fluid関数を使用。1pxラインなどデザイン上適切な場合のみpxを使用 |

### Step 7: `_index.scss` に追記

`src/scss/object/component/_index.scss` の末尾に `@use` を追記する:

```scss
@use '{name}';
```

**追記前に現在の内容を確認し、すでに存在する場合はスキップする。**

### Step 8: `docs/components/index.md` に追記

以下の形式で追記する:

```markdown
| .c-{name} | include/component/{name}.php | src/scss/object/component/_{name}.scss | {用途} |
```

`docs/components/index.md` が存在しない場合は新規作成する:

```markdown
# コンポーネント一覧

| BEMクラス | PHPパス | SCSSパス | 用途 |
|-----------|--------|---------|-----|
```

### Step 9: 自己検証チェック

生成完了後、以下を確認してエンジニアに報告する:

```
component-generate 完了

生成ファイル:
  ✅ include/component/{name}.php
  ✅ src/scss/object/component/_{name}.scss
  ✅ src/scss/object/component/_index.scss（@use 追記）
  ✅ docs/components/index.md（追記）

自己検証:
  [ ] PHP：全出力に esc_* が適用されているか → {結果}
  [ ] PHP：loading="lazy" decoding="async" が <img> に付与されているか → {結果}
  [ ] SCSS：pxの直書きがないか（1px除く） → {結果}
  [ ] SCSS：fluid関数が使用されているか（device が両方ある場合） → {結果}
  [ ] SCSS：render=::after/::before の要素がHTMLに出力されていないか → {結果}
  [ ] docs/components/index.md に追記されているか → {結果}

次のステップ:
  npm run lint を実行してエラーがないか確認してください。
```

---

## エッジケース一覧

| 状況 | 対応 |
|------|------|
| `docs/components/index.md` が存在しない | スキップして進める・生成完了後に新規作成 |
| 同一コンポーネントが既に存在する | Step 1 で停止・修正か新規作成かを確認 |
| `~/.claude/figma-properties.md` が存在しない | Step 3 で停止・インストール案内 |
| 未知のFigmaプロパティ | Step 3 で停止・推測禁止・エンジニアに確認 |
| `src/scss/object/utility/` が存在しない | utilityクラスなしとして扱い、BEM modifierで実装提案 |
| `_index.scss` に既に `@use` が存在する | 重複追記をスキップ |
| `include/component/` ディレクトリが存在しない | 自動作成してから出力 |

---

## トークン最適化

- `~/.claude/figma-properties.md` はFigmaモードのStep 3でのみ読み込む
- `docs/components/index.md` はStep 1（重複確認）でのみ読み込む
- `src/scss/object/utility/` はStep 4（alignやcolorが含まれる場合）でのみ走査する
- 開始時にドキュメントを一括ロードしない
