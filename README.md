# Ultimate_examer

Ultimate_examer 是一個不綁定特定考試的選擇題考試與練習 GUI。使用者可載入一個或多個 JSON 題庫，依序或隨機作答。

## 目前功能

- Practice Mode：逐題即時判定、顯示正確答案與紅／綠回饋。
- Exam Mode：設定題數，交卷前隱藏答案，交卷後統一計分與顯示結果。
- Wrong Answer Mode：持久保存錯題並再次練習；答對後從下一次錯題 session 移除。
- Sequential／Random 題目順序，多題庫可合併使用。
- Previous、Next 與題目清單跳轉，保留 session 內的作答狀態。
- 繁體中文／English 介面。
- GUI 按鈕、`Ctrl + +`、`Ctrl + -`、`Ctrl + 滑鼠滾輪`調整字體大小。
- Canonical question-bank schema 1.0 驗證與錯誤提示。

## 執行

需求：Python 3.10 以上，並包含標準庫 Tkinter。不需要安裝第三方套件。

```powershell
python app.py
```

啟動後選擇一個或多個題庫、模式與題目順序，再按「開始」。Exam Mode 另需設定題數。錯題紀錄會寫入根目錄的 `wrong_answers.json`。

## 加入新題庫

題庫必須遵循 [Bank/README.md](Bank/README.md) 定義的 canonical schema 1.0。

1. 建立 UTF-8 JSON 題庫並依規格設定穩定的 bank、section 與 question IDs。
2. 將檔案放入 `Bank/`，或保存在其他位置。
3. 從 GUI 的題庫選擇器載入；可一次選取多個檔案。

`Bank/` 內現有的 ISO 17025 題庫可作為完整實例。

## 專案結構

```text
app.py                  GUI、Practice／Exam session 與模式流程
question_bank.py        Canonical 題庫資料模型、載入與驗證
wrong_answers.py        JSON 錯題紀錄
Bank/
  README.md             題庫 schema 1.0 正式規格
  ISO17025_...json      既有題庫
test/                   automated tests
arch.md                 專案需求與設計原則
steps.md                開發階段
```

## Tests

從 repository 根目錄執行：

```powershell
python -m unittest discover -s test -v
```
