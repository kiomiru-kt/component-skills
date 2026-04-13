# Figma プロパティ命名規則

**作成日**: 2026-04-09  
**対象**: エンジニア / AI（component-generate、spec-builderスキル）  
**目的**: FigmaのフレームおよびコンポーネントプロパティをAIが正確に解釈し、実装に変換するための規則書

---

## 概要

Figmaのフレーム名・コンポーネントプロパティは、AIへの実装指示として機能する。  
すべての命名は**バリアントプロパティ**であり、`キー=値` 形式で記述する。  
複数のキーを組み合わせる場合はカンマ区切りで連結する。

```
{キー}={値}[,{キー}={値}...]

例: role=decoration,render=::after
例: device=pc,size=xl
例: role=bg,render=::bg-image,src=bg_.webp,src-2x=bg_hero_x2.webp
```

---

## キー一覧

| キー | 用途 | 値の例 |
|------|------|-------|
| `device` | 対象デバイス | `pc` / `sp` |
| `size` | サイズ区分 | `2xl` / `xl` / `lg` / `md` / `xs`（案件毎に定義） |
| `state` | インタラクション状態 | `default` / `active` / `hover` / `disabled` など |
| `align` | テキストの配置 | `left` / `center` / `right` |
| `color` | カラーバリエーション | `main` / `white`（案件毎に定義） |
| `tag` | 出力するHTMLタグ | `h1` / `h2` / `h3` / `p` / `span` / `ul` / `li` |
| `link` | リンクの種別 | `inner` / `out` / `inpage` |
| `role` | 要素の役割 | `heading-group` / `decoration` / `bg` / `heading-sub` |
| `render` | 出力形式 | `::after` / `::before` / `::bg-image` / `::img` |
| `style` | 装飾スタイル | `line` / `dotted` |
| `data` | data属性として出力 | `data-title` / `data-id` |
| `lang` | 言語属性 | `en` / `ja` |
| `src` | 画像ソース（1x） | ファイル名 |
| `src-2x` | 画像ソース（2x） | ファイル名 |

---

## キー別 AIの処理ルール

### `device`

| 値の組み合わせ | AIの処理 |
|--------------|---------|
| `pc` と `sp` の両方が存在する | fluid関数（`fluid-font-rem` / `fluid-space-rem`）で実装する。メディアクエリは使用しない |
| `pc` のみ存在する | メディアクエリなし。PCのスタイルをデフォルトとして実装 |
| `sp` のみ存在する | メディアクエリなし。SPのスタイルをデフォルトとして実装 |
| SPとPCで値が完全に異なる（fluid関数で表現できない）場合 | `@include mq(pc)` でSP基本・PC差分として実装。fluid関数が使えない場合のみ許可 |

---

### `size`

- 値は案件毎に異なる。このドキュメントでは定義しない
- BEM modifier（`--{size}`）として実装する
- デフォルト値（サイズ指定なし）は最も使用頻度が高い値をベースとする

---

### `state`

| 値 | AIの処理 |
|----|---------|
| `default` | デフォルトスタイル（修飾子なし） |
| `hover` | `&:hover` 疑似クラス |
| `active` | `&:active` または `&.is-active` |
| `disabled` | `&:disabled` または `&[disabled]` |
| `checked` | `&:checked` または `&.is-checked` |
| `error` | `&.is-error` |
| `empty` | `&.is-empty` |
| `loading` | `&.is-loading` |
| `selected` | `&.is-selected` |

---

### `align` / `color`

これらはテキストを対象とするプロパティ。

**実装前に必ず確認すること**：プロジェクトにutilityクラスが存在するかチェックする。

- 存在する場合 → utilityクラスを使用する
- 存在しない場合 → BEM modifierの追加案をエンジニアに提示し、承認を得てから実装する

なお、レイアウト系（`display`・`margin`・`padding`など）のutilityクラスは作成しない。

```html
<!-- utilityクラスが存在する場合 -->
<h2 class="c-heading-01 u-text-center u-color-white" data-title="サービス">
  <span class="c-heading-01__en">SERVICE</span>
</h2>

<!-- utilityクラスが存在せず、BEM modifierを追加した場合 -->
<h2 class="c-heading-01 c-heading-01--center c-heading-01--white" data-title="サービス">
  <span class="c-heading-01__en">SERVICE</span>
</h2>
```

---

### `role`

要素の役割を示す。`render` と組み合わせて出力形式を指定することが多い。

| 値 | 意味 |
|----|------|
| `heading-group` | 見出しグループのコンテナ |
| `heading-sub` | サブ見出し要素 |
| `decoration` | 装飾要素（罫線・アンダーラインなど） |
| `bg` | 背景要素 |

---

### `tag`

出力するHTMLタグを明示する。指定がない場合はAIがコンテキストから判断する。

| 値 | 出力されるHTML要素 | AIの自動付与属性 |
|----|-----------------|---------------|
| `h1`〜`h6` | 見出し要素 | - |
| `p` | 段落 | - |
| `span` | インライン要素 | - |
| `ul` / `ol` / `li` | リスト要素 | - |
| `button` | ボタン要素 | `type="button"` |
| `div` | 汎用ブロック要素 | - |
| `img` | 画像要素 | `loading="lazy"` `decoding="async"` |
| `picture` | レスポンシブ画像要素 | WebP `<source>` + フォールバック `<img>`（`loading="lazy"` `decoding="async"`） |
| `video` | 動画要素 | `playsinline` `muted`（autoplayの場合） |

---

### `render`

CSS上の出力形式を示す。**`render` が指定された要素はHTMLに要素を出力しない。**  
画像・動画の出力には `tag` を使用すること。

| 値 | AIの処理 |
|----|---------|
| `::after` | CSS `::after` 疑似要素として実装 |
| `::before` | CSS `::before` 疑似要素として実装 |
### `link`

リンクの種別を示す。指定された場合はAIが `<a>` タグの属性を自動で設定する。

| 値 | 意味 | AIの処理 |
|----|------|---------|
| `inner` | サイト内遷移 | `<a href="...">` のみ |
| `out` | 外部サイト遷移 | `<a href="..." target="_blank" rel="noopener noreferrer">` |
| `inpage` | ページ内アンカー | `<a href="#...">` |

---

### `render`

CSS上の出力形式を示す。**`render` が指定された要素はHTMLに要素を出力しない。**  
画像・動画の出力には `tag` を使用すること。

| 値 | AIの処理 |
|----|---------|
| `::after` | CSS `::after` 疑似要素として実装 |
| `::before` | CSS `::before` 疑似要素として実装 |
| `::bg-image` | `background-image` として実装（`src` / `src-2x` と組み合わせる） |

---

### `style`

`role=decoration` と組み合わせて使用する。

| 値 | AIの処理 |
|----|---------|
| `line` | `border-style: solid` |
| `dotted` | `border-style: dotted` |

---

### `data`

HTML の `data-*` 属性として出力する。

| 例 | AIの処理 |
|----|---------|
| `data=data-title` | 要素に `data-title="{値}"` 属性を付与 |

---

### `lang`

HTML の `lang` 属性として出力する。`role=heading-sub` などと組み合わせて使用。

| 例 | AIの処理 |
|----|---------|
| `lang=en` | 要素に `lang="en"` 属性を付与 |

---

### `src` / `src-2x`

`render=::bg-image` と組み合わせて使用。

| キー | AIの処理 |
|-----|---------|
| `src` | 通常解像度の背景画像ファイル名 |
| `src-2x` | Retina（2倍）解像度の背景画像ファイル名 |

`src-2x` が存在しない場合は `src` のみで実装する。

---

## 使用例

| Figmaの命名 | AIの解釈 |
|------------|---------|
| `device=pc,size=2xl` | PCサイズのみ・2xlバリアント。メディアクエリなし |
| `device=pc,size=xl` | PCサイズのみ・xlバリアント。メディアクエリなし |
| `role=decoration,style=line,render=::after` | HTMLに出力しない。`::after` 疑似要素で実線を描画 |
| `role=decoration,style=dotted,render=::before` | HTMLに出力しない。`::before` 疑似要素で点線を描画 |
| `role=bg,render=::bg-image,src=bg_.webp,src-2x=bg_hero_x2.webp` | HTMLに出力しない。`background-image` で2x対応して描画 |
| `role=heading-sub,lang=en,data=data-title` | `lang="en"` と `data-title="{値}"` 属性を付与して出力 |

---

## 未知のプロパティへの対応

このドキュメントに定義されていないキーまたは値が登場した場合、AIは推測で実装しない。  
エンジニアに確認を求め、このドキュメントへの追記と承認を得てから実装する。

---

## 新プロパティ追加手順

1. このドキュメントの「キー一覧」と該当セクションに追記
2. 値・AIの処理・使用例を記載する
3. `docs/figma-properties.md` をコミットする
