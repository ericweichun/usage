# 安全政策

> English version: [SECURITY.en.md](SECURITY.en.md)

## 回報安全漏洞

如果你發現 usage 的安全漏洞，**請勿開公開 Issue**。請改用私下管道回報：

📧 **aqua5230@gmail.com**

回報時請盡量包含：

- 受影響的版本（或 commit）
- 重現步驟，或概念驗證（PoC）
- 你評估的影響範圍

本專案為單人維護，我會盡力在合理時間內回覆並處理。修復釋出後會在 release notes 中致謝（除非你希望匿名）。

## 支援版本

usage 採滾動發布，安全修復只針對**最新發布版**。回報前請先確認你使用的是 [最新 release](https://github.com/aqua5230/usage/releases/latest)。

## 安全設計

usage **不呼叫任何 Anthropic / OpenAI 網路 API**——所有數字都來自你本機磁碟上既有的檔案（Claude Code 寫的狀態檔，以及 Codex 的 session log）。它不上傳、不追蹤、不把你的用量資料外送。這是本專案的核心設計原則。
