# Ultimate_examer 題庫 JSON 格式

本文件定義 Ultimate_examer 所有題庫共用的 canonical JSON schema，也是人工或 AI 建立新題庫時應遵守的格式。第一版只支援純文字單選題；題庫內容可以來自語言、自然科學、數學、程式設計、法規或其他領域。

## 完整結構

```text
Question Bank
├─ schema_version
├─ id
├─ title
├─ description?       (optional)
├─ language
├─ source?            (optional)
└─ sections[]
   ├─ id
   ├─ title
   └─ questions[]
      ├─ id
      ├─ number?      (optional)
      ├─ text
      ├─ options[]
      │  ├─ id
      │  └─ text
      ├─ answer
      ├─ source?      (optional)
      ├─ tags?        (optional)
      └─ note?        (optional)
```

所有未標示 optional 的欄位都是 required。不得加入本文件未定義的欄位；格式若需擴充，應先更新 schema version 與本文件。

## 欄位規格

### Question Bank

| 欄位 | 型別 | 必要性 | 語意與限制 |
|---|---|---|---|
| `schema_version` | string | Required | 格式版本。第一版固定為 `"1.0"`。 |
| `id` | string | Required | 題庫的穩定識別碼。須符合下方 ID 規則。 |
| `title` | string | Required | 題庫顯示名稱；必須是非空字串，不作為 identity。 |
| `description` | string | Optional | 題庫用途、涵蓋範圍或編輯說明；若提供，必須是非空字串。 |
| `language` | string | Required | 題庫主要內容語言，使用 BCP 47 language tag，例如 `zh-Hant`、`en`、`en-US`；刻意混合多種語言時可使用 `mul`。 |
| `source` | string | Optional | 題庫整體來源，例如書名、法規、檔名或 URL；若提供，必須是非空字串。 |
| `sections` | array | Required | 有序 section 陣列，至少包含一個 section。 |

### Section

| 欄位 | 型別 | 必要性 | 語意與限制 |
|---|---|---|---|
| `id` | string | Required | Section 的穩定識別碼；在同一 bank 內唯一。 |
| `title` | string | Required | Section 顯示名稱；必須是非空字串。 |
| `questions` | array | Required | 有序 question 陣列，至少包含一題。 |

Section 是必要的邏輯分組，但不一定等於來源教材的正式章節。它可以代表 Chapter、Unit、Topic、Part、Domain 或其他合理分類。來源沒有章節時，仍須建立一個 section，例如 ID 為 `general`、title 為 `General`。

### Question

| 欄位 | 型別 | 必要性 | 語意與限制 |
|---|---|---|---|
| `id` | string | Required | 題目的穩定識別碼；必須在整個 bank 內唯一，而不只是 section 內唯一。 |
| `number` | string | Optional | 原始題號或顯示標籤，例如 `"12"`、`"12A"`。只供顯示，不是 identity，也不決定排序。 |
| `text` | string | Required | 題目文字；必須是非空字串。 |
| `options` | array | Required | 有序 option 陣列，至少包含兩個選項。 |
| `answer` | string | Required | 正確答案，值必須等於本題其中一個 `option.id`。單選題只能有一個值。 |
| `source` | string | Optional | 題目特定來源或位置，例如頁碼、條文或 URL；若提供，必須是非空字串。 |
| `tags` | array of strings | Optional | 題目標籤。每個值須為非空字串，同一題內不得重複。 |
| `note` | string | Optional | 轉錄、校訂或其他編輯備註；若提供，必須是非空字串。 |

### Option

| 欄位 | 型別 | 必要性 | 語意與限制 |
|---|---|---|---|
| `id` | string | Required | 選項識別碼；在單一 question 內唯一，例如 `a`、`b`、`c`。 |
| `text` | string | Required | 選項文字；必須是非空字串。 |

## Identifier 規則

Bank、section、question 與 option ID 均須符合：

```text
^[a-z0-9][a-z0-9._-]*$
```

ID 使用小寫 ASCII 字母、數字、句點、底線或連字號，且第一個字元必須是字母或數字。使用簡短、可讀、由題庫作者指定的 ID；不需要 UUID。

- `bank.id` 應能在使用者可能同時載入的題庫中保持唯一。
- `section.id` 在該 bank 內唯一。
- `question.id` 在整個 bank 內唯一，即使題號在不同 section 重複。
- `option.id` 只需在所屬 question 內唯一。
- ID 一旦發布或被進度、錯題紀錄引用，不得因顯示名稱、題目文字修訂、重新排序或 question 移至其他 section 而任意改變。
- Question 的持久 identity 是 `bank.id` 與 `question.id` 的組合；`section.id` 和 `number` 不屬於該 identity。

## 順序、選項與答案

- Sections、questions 與 options 的順序一律以各自 JSON array 中的順序為準。
- `number` 只是 optional display metadata，不作為 identity 或排序依據。
- 每題至少有兩個 options。
- 同一題的所有 `option.id` 必須唯一。
- `answer` 必須精確指向該題已存在的 `option.id`。
- `answer` 是單一 string，不得使用 array；目前不支援多個正確答案。
- 不得儲存 `total_questions`、section 題數或其他可由 arrays 直接推導的計數欄位。

## 新增題庫規則

建立新題庫時：

1. 以 UTF-8 編碼儲存合法 JSON；JSON 內不可使用註解。
2. 完整提供所有 required fields，且只使用本文件定義的欄位。
3. 固定使用 `"schema_version": "1.0"`。
4. 先決定穩定的 bank、section 與 question IDs，不得使用 title、題目全文或 array index 代替 ID。
5. 所有題目都必須放入合理的 section；來源沒有正式章節時建立通用 section。
6. 使用 array 表達 section、question 與 option 的顯示順序。
7. 逐題確認 `answer` 對應到存在且唯一的 `option.id`。
8. 不確定的來源或轉錄資訊放在 `source` 或 `note`，不要新增臨時欄位。
9. 完成後驗證 ID 唯一性、必填欄位、非空文字、選項數量與答案引用。

## 最小完整範例

```json
{
  "schema_version": "1.0",
  "id": "physics-mechanics-basics",
  "title": "基礎力學題庫",
  "language": "zh-Hant",
  "sections": [
    {
      "id": "kinematics",
      "title": "運動學",
      "questions": [
        {
          "id": "constant-speed-001",
          "text": "物體以固定速度運動時，下列何者正確？",
          "options": [
            {
              "id": "a",
              "text": "加速度為零"
            },
            {
              "id": "b",
              "text": "速度必定增加"
            }
          ],
          "answer": "a"
        }
      ]
    }
  ]
}
```

此範例是 schema `1.0` loader 應接受的最小完整輸入。Repository 內既有 loader 與題庫在遷移至 schema `1.0` 前可能尚未接受此格式；建立新題庫時仍應以本文件為準，不應從舊 Python implementation 反推格式。

## 支援範圍

Schema `1.0` 支援：

- 純文字題幹。
- 純文字、有固定順序的選項。
- 每題恰有一個正確答案的單選題。
- 一層必要的 section 邏輯分組。
- 題庫、題目來源與簡單標籤、編輯備註。

Schema `1.0` 不支援：

- 複選題、是非題專用型別、填充題、配對題、簡答題或作文題。
- 圖片、公式專用格式、音訊、影片或其他附件。
- HTML、Markdown 或其他 rich-text rendering contract。
- 部分給分、加權、評分規則或多個正確答案。
- 巢狀 sections、題組共用材料、自適應測驗或條件分支。

若未來出現上述真實需求，應先設計並發布新的 schema version，不得在 `1.0` 題庫中自行加入未定義欄位。
