# figma-extract スキル仕様書

**作成日**: 2026-04-09（2026-04-09 更新）
**ステータス**: 設計確定（スキル実装待ち）  
**関連ドキュメント**: figma-properties.md, component-generate-spec.md

---

## 概要

FigmaのComponentsページをAIが走査し、コンポーネントのバリアント構造を整理・構築するスキル。  
エンジニアがコンポーネント候補を配置・命名し、AIがFigmaのバリアントプロパティを設定する。

---

## 前提フロー

```
デザイナーがFigmaでコンポーネント抽出（精度低い）
    ↓
エンジニアが漏れを追加抽出・Componentsページに配置
エンジニアがコンポーネント名とプロパティを命名
    ↓
figma-extract実行
AIがフレームを走査・グループ化・Figmaバリアント構築
    ↓ 連続実行
figma-tokenize（Pythonでバリアブル抽出）
    ↓
エンジニアがBEMクラス名を確認・確定
    ↓
実装へ（component-generateに連携）
```

---

## エンジニアの命名規則

### コンポーネント名

BEM名をそのまま使用する。Figmaのコンポーネント名 = CSSのBEMクラス名（`.c-` プレフィックスを除く）。

```
heading-01  →  .c-heading-01
card-01     →  .c-card-01
btn-01      →  .c-btn-01
```

### バリアントフレームの命名

各バリアントフレームは `figma-properties.md` のプロパティ記法で命名する。

```
{キー}={値}[,{キー}={値}...]
```

**命名例（heading-01の場合）：**

```
device=sp,align=left,color=main
device=sp,align=center,color=main
device=sp,align=left,color=white
device=pc,align=left,color=main
device=pc,align=center,color=white
```

**命名例（btn-01の場合）：**

```
state=default
state=hover
state=disabled
```

**命名例（card-01の場合）：**

```
device=sp,state=default
device=sp,state=hover
device=pc,state=default
device=pc,state=hover
```

### 使用できるキー

`figma-properties.md` のキー一覧に準拠する。主に使用するキー：

| キー | 値の例 | 用途 |
|------|-------|------|
| `device` | `pc` / `sp` | レスポンシブ差分 |
| `state` | `default` / `hover` / `active` / `disabled` / `checked` / `error` / `empty` / `loading` / `selected` | インタラクション状態 |
| `align` | `left` / `center` / `right` | テキスト配置 |
| `color` | `main` / `white`（案件毎に定義） | カラーバリエーション |
| `size` | `2xl` / `xl` / `lg` / `md` / `xs`（案件毎に定義） | サイズ |

**`role` / `render` / `tag` / `data` / `lang` / `src` はバリアントプロパティではなく内部要素の命名に使用する。**
これらはフレーム内の子要素名に記述し、バリアント命名には使用しない。

---

## Figmaページ構成

- コンポーネント専用ページ（ページ名: `Components`）を設ける
- エンジニアはこのページにコンポーネント候補を配置・命名する
- figma-extractはこのページのみを走査する（他ページは対象外）

---

## AIの処理フロー

### Step 1: Componentsページを走査

Figma MCPで `Components` ページを走査し、以下を取得：
- フレーム名一覧（コンポーネント名とプロパティ）
- 各フレームの子要素構造

### Step 2: コンポーネントのグループ化

同一コンポーネント名のフレームをグループ化する。

```
heading-01 配下:
  device=sp,align=left,color=main
  device=sp,align=center,color=white
  device=pc,align=left,color=main
  device=pc,align=center,color=white
→ heading-01 コンポーネントセット（4バリアント）

btn-01 配下:
  state=default
  state=hover
  state=disabled
→ btn-01 コンポーネントセット（3バリアント）
```

### Step 3: バリアントプロパティの設定

グループ化したコンポーネントセットに対し、use_figmaでFigmaのバリアントプロパティを設定する。

- プロパティ名：キー名をそのまま使用（`device` / `state` / `align` / `color` / `size`）
- プロパティ値：各バリアントフレームの値を設定

### Step 4: 構造が大きく異なる場合の対応

同一コンポーネント名でもフレーム構造が大きく異なる場合は、
同一コンポーネントとして統合すべきか別コンポーネントにすべきかをエンジニアに確認する。
推測で判断しない。

### Step 5: 整理レポート出力

`docs/figma-audit/components-{date}.md` に出力：

```markdown
## figma-extract 整理レポート {date}

### 構築したコンポーネントセット
| コンポーネント名 | BEMクラス | バリアント数 | プロパティ |
|----------------|---------|------------|---------|
| heading-01 | .c-heading-01 | 4 | device / align / color |
| btn-01 | .c-btn-01 | 3 | state |

### 要確認事項（エンジニア判断が必要）
- {コンポーネント名}: {理由}

### 未処理フレーム
- {フレーム名}: {除外理由}
```

---

## 役割分担

| 処理 | 担当 | 理由 |
|------|------|------|
| デザイン作成 | デザイナー | - |
| 漏れコンポーネントの抽出・配置 | エンジニア | 意味的判断が必要 |
| コンポーネント名・プロパティ命名 | エンジニア | BEM体系・figma-properties.mdの理解が必要 |
| グループ化・バリアントプロパティ構築 | AI（figma-extract） | プロパティ記法を機械的に解釈できる |
| BEMクラス名の最終確定 | エンジニア | プロジェクト固有の判断 |
| バリアブル抽出（色・サイズ） | Pythonスクリプト（figma-tokenize） | 数値処理は機械的に可能 |

---

## 連携スキル・実行順序

figma-extractセッション内で以下を**連続実行**する：

```
figma-extract（コンポーネント整理・バリアント構築）
    ↓
figma-tokenize（Pythonスクリプトでバリアブル抽出・JSON出力）
    ↓
整理レポート出力（docs/figma-audit/）
```

| スキル | タイミング | 内容 |
|--------|-----------|------|
| figma-extract | メイン | グループ化・バリアントプロパティ構築 |
| figma-tokenize | 直後に連続実行 | Pythonで色・サイズのバリアブル抽出 |
| component-generate | 実装時（別セッション） | PHP + SCSS生成 |

---

## トークン消費の最適化

- 走査対象は `Components` ページのみ（全ページ走査禁止）
- コンポーネント整理とページ実装はセッションを分割する
- Pythonスクリプトで処理できるもの（バリアブル抽出）はAIに任せない

---

## figma-lintについて

現在の運用（エンジニアがComponentsページに配置・命名する）では、
人間の目が入る時点でFigmaの品質は担保されるため **figma-lintは不要**。
将来的にデザイナーが直接AIに渡す運用になった場合は復活させる。

---

## SKILL.md実装時の注意点

- Figma MCPが接続済みであることを前提条件として明記
- 走査対象のFigma URLまたはframe-idをトリガー時に受け取る
- プロパティ規則は `docs/figma-properties.md` を参照する（SKILL.mdにハードコードしない）
- 出力レポートは必ず `docs/figma-audit/` に保存する

---

## 未解決事項（実装時に検討）

- [ ] use_figmaのバリアント書き込みAPIの安定性確認
- [ ] プロパティ記法以外の命名（日本語・スペース含む）が混在した場合の対応
- [ ] 既存コンポーネントとの重複チェック方法
