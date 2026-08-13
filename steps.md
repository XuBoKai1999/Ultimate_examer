# Ultimate_examer Development Steps

## Step 1 — 理解題庫與建立基礎架構

閱讀目前 repository 與 `Bank/` 中既有的 JSON 題庫。

確認實際資料結構後，建立足以支援目前題庫的載入與內部資料模型。

完成：

* JSON 題庫讀取。
* 單一與多題庫載入。
* 基本錯誤處理。
* 將題庫資料與 GUI 邏輯分離。

不要為未出現的題庫格式過度設計。

---

## Step 2 — 建立基本 GUI 與 Practice Mode

建立可實際操作的 GUI。

完成基本流程：

```text
選擇題庫
→ 選擇模式
→ 開始
→ 顯示題目
→ 選擇答案
→ 顯示結果
→ 下一題
```

先完成 Practice Mode。

作答後立即顯示：

* 是否正確。
* 正確答案。
* 明顯的正確／錯誤視覺回饋。

同時完成基本字體縮放功能。

每次開始 session 時可選擇：

* Sequential：依題庫選取順序及 JSON 中 section／question array 順序出題。
* Random：將所有選中題庫共同形成的題目 pool 隨機排序，同一 session 不重複。

Practice Mode 支援 Previous、Next 與題目清單／Jump to Question。未作答即可導航；返回已作答題目時保留 selected answer、正確答案及正確／錯誤結果。題目清單顯示順序編號、題目文字摘要與 unanswered／correct／incorrect。第一題與最後一題的無效方向按鈕應 disabled。

---

## Step 3 — Exam Mode

加入完整考試模式。

使用者可以設定本次題數。

考試過程中不透露答案。

Exam Mode 使用與 Practice Mode 相同的 Sequential／Random 定義，並可在未作答時 Previous、Next 或 Jump。交卷前題目清單只顯示 answered／unanswered，不得顯示正確答案或正確／錯誤狀態。

完成整場後：

* 統一批改。
* 顯示分數。
* 顯示各題答題結果。
* 將答錯題目交給錯題系統。

---

## Step 4 — 錯題系統

建立持久化的錯題紀錄。

加入 Wrong Answer Mode。

此模式從錯題紀錄派題，操作方式與 Practice Mode 相同：

```text
答題
→ 立即判定
→ 顯示正確答案
→ 下一題
```

錯題紀錄應能跨程式啟動保留。

Wrong Answer Mode 從目前錯題 pool 建立 session，使用相同的 Sequential／Random 選擇，導航與狀態保留行為同 Practice Mode。

實際儲存格式由實作決定，但保持簡單且可靠。

錯題以 `(bank.id, question.id)` 識別且不得重複。Practice／Exam 答錯時加入，答對不移除；Wrong Answer Mode 答對時移除、答錯時保留。成功載入 bank 後只清理該 bank 已不存在的 stale question IDs。GUI 提供經確認後清除目前所選題庫錯題的功能，不影響其他 bank。

---

## Step 5 — 中英文介面

整理 GUI 文字，使其可以集中管理。

加入：

* 繁體中文
* English

提供合理的語言切換方式。

確認切換語言後主要 GUI 元件均能正常更新。

---

## Step 6 — 完整化與測試

檢查完整使用流程與邊界情況。

至少確認：

* 無題庫。
* 無效 JSON。
* 多題庫。
* 題數超過可用題目。
* Practice Mode。
* Exam Mode。
* Wrong Answer Mode。
* 錯題保存與再次載入。
* 中英文切換。
* GUI 字體縮放。
* `Ctrl + +`
* `Ctrl + -`
* `Ctrl + 滑鼠滾輪`

修正明顯的 UX 問題與錯誤。

完成後，Ultimate_examer 應是一個可以直接日常使用的第一版，而不是只有功能展示的 prototype。
