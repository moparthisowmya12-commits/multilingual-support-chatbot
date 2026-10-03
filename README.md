# 💬 Multilingual Sentiment & Automated Support Escalation Assistant

An end-to-end customer support automation pipeline that combines sentiment analysis, rule-based signal detection, tone adaptation, dynamic session memory, and deterministic queue-routing policies.

---

## 🌟 Key Features

- **Multilingual Sentiment Classification**: Classifies customer messages into `positive`, `neutral`, `negative`, `frustrated`, `urgent`, and `sarcastic`.
- **Dynamic Response Tone Adaptation**: Adjusts response tone (e.g., *Empathetic & De-escalating*, *Action-Oriented*, *Warm & Professional*) without altering fundamental business policies.
- **High-Risk Signal Detection**: Transparent pattern matching for high-stakes issues:
  - Account Compromise
  - Duplicate / Double Payments
  - Legal Threats
- **Deterministic Escalation Routing**:
  - **Immediate Escalation**: Triggered by high-risk flags, repeated negative sentiment, or negative conversations remaining unresolved for $>15$ minutes.
  - **After-Hours Urgent Queue**: Routes urgent/frustrated requests outside business hours to an On-Call queue.
  - **After-Hours Next-Day Queue**: Routes standard non-urgent complaints outside business hours to the next working day queue.
- **Audit Logging**: Logs all triggered escalations with timestamps, reasons, activated conditions, and conversation summaries.
- **Interactive UI**: Built with Streamlit, including custom simulated time controls to test after-hours and timer-based escalation rules easily.

---

## 🏗️ System Architecture
