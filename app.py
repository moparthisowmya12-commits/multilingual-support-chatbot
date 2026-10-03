import streamlit as st
from datetime import datetime, time, timedelta
import re
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

# Set page configuration at the very top
st.set_page_config(page_title="Multilingual Support Assistant", page_icon="💬", layout="wide")

# --- DATA MODELS ---
class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    FRUSTRATED = "frustrated"
    URGENT = "urgent"
    SARCASTIC = "sarcastic"

class HighRiskCategory(str, Enum):
    ACCOUNT_COMPROMISE = "account_compromise"
    DUPLICATE_PAYMENT = "duplicate_payment"
    LEGAL_THREAT = "legal_threat"

class EscalationType(str, Enum):
    IMMEDIATE = "immediate"
    ON_CALL_QUEUE = "on_call_queue"
    NEXT_DAY_SCHEDULE = "next_day_schedule"
    NONE = "none"

class Message(BaseModel):
    message_id: str
    timestamp: datetime
    sender: str
    text: str

class EscalationRecord(BaseModel):
    escalated: bool
    escalation_type: EscalationType = EscalationType.NONE
    reason: Optional[str] = None
    activated_condition: Optional[str] = None
    conversation_summary: Optional[str] = None

class SentimentAnalysisResult(BaseModel):
    detected_sentiment: Sentiment
    confidence_score: float
    high_risk_detected: Optional[HighRiskCategory] = None
    is_sarcastic: bool = False

class ProcessedTurnOutput(BaseModel):
    original_message: str
    detected_sentiment: Sentiment
    confidence_score: float
    high_risk_flag: Optional[HighRiskCategory] = None
    applied_tone: str
    base_policy_response: str
    adjusted_response: str
    escalation: EscalationRecord

# --- PIPELINE ENGINE ---
class MultilingualSentimentEngine:
    def __init__(self, business_start: time = time(9, 0), business_end: time = time(17, 0)):
        self.business_start = business_start
        self.business_end = business_end
        self.unresolved_threshold = timedelta(minutes=15)

        self.legal_patterns = [r"\blawyer\b", r"\bsue\b", r"\blegal action\b", r"\battorney\b", r"\bcourt\b"]
        self.compromise_patterns = [r"\bhacked\b", r"\bunauthorized\b", r"\bcompromised\b", r"\bstolen\b", r"accessed my account"]
        self.duplicate_patterns = [r"\bcharged twice\b", r"\bdouble payment\b", r"\bduplicate payment\b", r"\bcharged two times\b"]
        self.sarcasm_patterns = [r"great job breaking", r"wonderful service", r"thanks for nothing", r"so helpful", r"brilliant service", r"amazing service"]
        self.urgent_patterns = [r"\burgent\b", r"\basap\b", r"\bimmediately\b", r"\bright now\b"]
        self.frustrated_patterns = [r"\bangry\b", r"\bunacceptable\b", r"\bterrible\b", r"\bworst\b", r"\bdisappointed\b"]

    def is_business_hours(self, current_time: datetime) -> bool:
        if current_time.weekday() >= 5:
            return False
        return self.business_start <= current_time.time() <= self.business_end

    def analyze_message(self, text: str) -> SentimentAnalysisResult:
        lower_text = text.lower()
        high_risk = None
        if any(re.search(p, lower_text) for p in self.legal_patterns):
            high_risk = HighRiskCategory.LEGAL_THREAT
        elif any(re.search(p, lower_text) for p in self.compromise_patterns):
            high_risk = HighRiskCategory.ACCOUNT_COMPROMISE
        elif any(re.search(p, lower_text) for p in self.duplicate_patterns):
            high_risk = HighRiskCategory.DUPLICATE_PAYMENT

        is_sarcastic = any(re.search(p, lower_text) for p in self.sarcasm_patterns) or ("great" in lower_text and "charged twice" in lower_text)

        if is_sarcastic:
            sentiment = Sentiment.SARCASTIC
            confidence = 0.89
        elif high_risk:
            sentiment = Sentiment.URGENT if "urgent" in lower_text else Sentiment.NEGATIVE
            confidence = 0.96
        elif any(re.search(p, lower_text) for p in self.urgent_patterns):
            sentiment = Sentiment.URGENT
            confidence = 0.92
        elif any(re.search(p, lower_text) for p in self.frustrated_patterns):
            sentiment = Sentiment.FRUSTRATED
            confidence = 0.90
        elif any(kw in lower_text for kw in ["bad", "wrong", "fail", "not working", "error"]):
            sentiment = Sentiment.NEGATIVE
            confidence = 0.85
        elif any(kw in lower_text for kw in ["thanks", "thank you", "great", "good", "solved", "resolved"]):
            sentiment = Sentiment.POSITIVE
            confidence = 0.94
        else:
            sentiment = Sentiment.NEUTRAL
            confidence = 0.82

        return SentimentAnalysisResult(
            detected_sentiment=sentiment,
            confidence_score=confidence,
            high_risk_detected=high_risk,
            is_sarcastic=is_sarcastic
        )

    def adjust_response_tone(self, base_policy_response: str, sentiment_res: SentimentAnalysisResult) -> Tuple[str, str]:
        if sentiment_res.high_risk_detected or sentiment_res.detected_sentiment in [Sentiment.FRUSTRATED, Sentiment.SARCASTIC]:
            tone = "Empathetic & De-escalating"
            prefix = "I understand how concerning this situation is, and I apologize for the inconvenience. "
        elif sentiment_res.detected_sentiment == Sentiment.URGENT:
            tone = "Action-Oriented & Prompt"
            prefix = "I recognize the urgency of your request and am prioritizing this immediately. "
        elif sentiment_res.detected_sentiment == Sentiment.POSITIVE:
            tone = "Warm & Professional"
            prefix = "Thank you for reaching out! "
        else:
            tone = "Standard Professional"
            prefix = ""

        return f"{prefix}{base_policy_response}", tone

    def evaluate_escalation(self, current_msg: Message, history: List[Message], sentiment_res: SentimentAnalysisResult, eval_time: datetime) -> EscalationRecord:
        in_business_hours = self.is_business_hours(eval_time)
        summary = " | ".join([f"[{m.timestamp.strftime('%H:%M')}] {m.sender.upper()}: {m.text}" for m in history + [current_msg]])

        if sentiment_res.high_risk_detected:
            return EscalationRecord(
                escalated=True,
                escalation_type=EscalationType.IMMEDIATE,
                reason=f"High-risk issue detected: {sentiment_res.high_risk_detected.value}",
                activated_condition="High-Risk Category Trigger",
                conversation_summary=summary
            )

        if history:
            first_msg_time = history[0].timestamp
            if (eval_time - first_msg_time) > self.unresolved_threshold:
                if sentiment_res.detected_sentiment in [Sentiment.NEGATIVE, Sentiment.FRUSTRATED, Sentiment.SARCASTIC]:
                    return EscalationRecord(
                        escalated=True,
                        escalation_type=EscalationType.IMMEDIATE,
                        reason=f"Unresolved for >15 mins ({int((eval_time - first_msg_time).total_seconds()/60)}m)",
                        activated_condition="Unresolved Time Limit Exceeded (>15m)",
                        conversation_summary=summary
                    )

        if sentiment_res.detected_sentiment in [Sentiment.URGENT, Sentiment.FRUSTRATED] and not in_business_hours:
            return EscalationRecord(
                escalated=True,
                escalation_type=EscalationType.ON_CALL_QUEUE,
                reason="Urgent complaint outside business hours.",
                activated_condition="After-Hours Urgent Queue",
                conversation_summary=summary
            )

        if sentiment_res.detected_sentiment == Sentiment.NEGATIVE and not in_business_hours:
            return EscalationRecord(
                escalated=True,
                escalation_type=EscalationType.NEXT_DAY_SCHEDULE,
                reason="Normal complaint outside business hours.",
                activated_condition="After-Hours Next-Day Scheduling",
                conversation_summary=summary
            )

        return EscalationRecord(escalated=False)

    def process_turn(self, current_msg: Message, history: List[Message], base_policy_response: str, eval_time: datetime) -> ProcessedTurnOutput:
        sentiment_res = self.analyze_message(current_msg.text)
        adjusted_resp, tone = self.adjust_response_tone(base_policy_response, sentiment_res)
        escalation_res = self.evaluate_escalation(current_msg, history, sentiment_res, eval_time)

        return ProcessedTurnOutput(
            original_message=current_msg.text,
            detected_sentiment=sentiment_res.detected_sentiment,
            confidence_score=sentiment_res.confidence_score,
            high_risk_flag=sentiment_res.high_risk_detected,
            applied_tone=tone,
            base_policy_response=base_policy_response,
            adjusted_response=adjusted_resp,
            escalation=escalation_res
        )

# --- STREAMLIT USER INTERFACE ---
st.title("💬 Multilingual Support Escalation Assistant")

with st.sidebar:
    st.header("⚙️ Configuration & Simulation")
    use_sim = st.checkbox("Use Simulated Time", value=True)
    if use_sim:
        sim_date = st.date_input("Simulated Date", value=datetime.now().date())
        sim_time = st.time_input("Simulated Time", value=datetime.now().time().replace(second=0))
        current_dt = datetime.combine(sim_date, sim_time)
    else:
        current_dt = datetime.now()

    if st.button("🗑️ Clear Session State"):
        st.session_state.history = []
        st.session_state.escalations = []
        st.rerun()

if "history" not in st.session_state:
    st.session_state.history = []
if "escalations" not in st.session_state:
    st.session_state.escalations = []

engine = MultilingualSentimentEngine()

col1, col2 = st.columns([2, 1])

with col1:
    user_input = st.text_area("Enter Customer Message:", placeholder="Type a message...", height=120)
    if st.button("🔎 Send & Process Message", type="primary"):
        if user_input.strip():
            current_msg = Message(
                message_id=f"msg_{len(st.session_state.history)+1}",
                timestamp=current_dt,
                sender="customer",
                text=user_input.strip()
            )

            base_policy = "Our support team will process your request within standard guidelines."
            output = engine.process_turn(current_msg, st.session_state.history, base_policy, current_dt)

            st.session_state.history.append(current_msg)

            st.subheader("📊 Turn Output")
            st.write(f"**Detected Sentiment:** `{output.detected_sentiment.value.upper()}`")
            st.write(f"**Confidence Score:** `{output.confidence_score:.2f}`")
            st.write(f"**Applied Tone:** {output.applied_tone}")
            st.info(f"**Bot Response:** {output.adjusted_response}")

            if output.escalation.escalated:
                st.error(f"🚨 Escalation Activated: {output.escalation.escalation_type.value.upper()}")
                st.write(f"**Reason:** {output.escalation.reason}")
                st.session_state.escalations.append(output.escalation.model_dump())

with col2:
    st.subheader("Conversation History")
    for msg in st.session_state.history:
        st.caption(f"[{msg.timestamp.strftime('%H:%M')}] {msg.sender.upper()}: {msg.text}")

    st.subheader("🚨 Escalation Logs")
    if st.session_state.escalations:
        st.json(st.session_state.escalations)
    else:
        st.caption("No active escalations.")
