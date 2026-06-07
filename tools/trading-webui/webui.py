import streamlit as st
import sys
import os
import io
import contextlib
import random
from datetime import date, timedelta

sys.path.insert(0, "/opt/TradingAgents")

from dotenv import load_dotenv
load_dotenv("/opt/TradingAgents/.env")

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

st.set_page_config(page_title="TradingAgents", page_icon="📈", layout="wide")
st.title("📈 TradingAgents AI 股票分析")
st.caption("Multi-Agents LLM Financial Trading Framework · Powered by DeepSeek")
st.divider()

MARKET_SUFFIX = {
    "🇺🇸 美股 (NASDAQ/NYSE)": "",
    "🇭🇰 港股 (HKEX)": ".HK",
    "🇨🇳 A股 上海 (SSE)": ".SS",
    "🇨🇳 A股 深圳 (SZSE)": ".SZ",
    "₿ 加密货币": "-USD",
}
MARKET_EXAMPLES = {
    "🇺🇸 美股 (NASDAQ/NYSE)": "AAPL · TSLA · NVDA · MSFT · AMZN",
    "🇭🇰 港股 (HKEX)": "0700（腾讯）· 9988（阿里）· 1810（小米）· 0005（汇丰）",
    "🇨🇳 A股 上海 (SSE)": "600519（茅台）· 601398（工行）· 600036（招行）",
    "🇨🇳 A股 深圳 (SZSE)": "000858（五粮液）· 000001（平安银行）· 300750（宁德时代）",
    "₿ 加密货币": "BTC · ETH · SOL · BNB",
}
DECISION_DISPLAY = {
    "buy": ("🟢", "买入 BUY", "green"),
    "strong buy": ("🟢", "强烈买入 STRONG BUY", "green"),
    "sell": ("🔴", "卖出 SELL", "red"),
    "strong sell": ("🔴", "强烈卖出 STRONG SELL", "red"),
    "hold": ("🟡", "持有 HOLD", "orange"),
    "underweight": ("🔴", "减持 UNDERWEIGHT", "red"),
    "overweight": ("🟢", "增持 OVERWEIGHT", "green"),
    "neutral": ("🟡", "中性 NEUTRAL", "orange"),
}

with st.sidebar:
    st.subheader("🔑 DeepSeek API Keys")
    st.caption("添加多个 Key 自动轮换，避免速率限制")
    if "api_keys" not in st.session_state:
        default_key = os.environ.get("DEEPSEEK_API_KEY", "")
        st.session_state.api_keys = [default_key] if default_key else []
    new_key = st.text_input("添加新 Key", placeholder="sk-xxxxxxxxxxxx", type="password")
    if st.button("➕ 添加", use_container_width=True):
        if new_key and new_key not in st.session_state.api_keys:
            st.session_state.api_keys.append(new_key.strip())
            st.success("添加成功")
        elif new_key in st.session_state.api_keys:
            st.warning("Key 已存在")
    if st.session_state.api_keys:
        st.markdown(f"**当前 Keys：{len(st.session_state.api_keys)} 个**")
        for i, k in enumerate(st.session_state.api_keys):
            c1, c2 = st.columns([4, 1])
            c1.text(f"...{k[-8:]}")
            if c2.button("🗑️", key=f"del_{i}"):
                st.session_state.api_keys.pop(i)
                st.rerun()
    else:
        st.warning("请至少添加一个 API Key")

col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
with col1:
    market = st.selectbox("市场", list(MARKET_SUFFIX.keys()))
with col2:
    suffix = MARKET_SUFFIX[market]
    dv = {"港股": "0700", "美股": "AAPL", "上海": "600519", "深圳": "000858", "加密": "BTC"}
    default = next((v for k, v in dv.items() if k in market), "AAPL")
    raw_ticker = st.text_input("股票代码（不需要加后缀）", value=default, help=MARKET_EXAMPLES[market])
    ticker = raw_ticker.strip().upper() + suffix
    st.caption(f"完整代码：**{ticker}**　　参考：{MARKET_EXAMPLES[market]}")
with col3:
    analysis_date = st.date_input("分析日期", value=date.today() - timedelta(days=1), max_value=date.today() - timedelta(days=1))
with col4:
    st.write(""); st.write("")
    run = st.button("🔍 开始分析", type="primary", use_container_width=True)

if run:
    if not raw_ticker.strip():
        st.error("请输入股票代码")
    elif not st.session_state.api_keys:
        st.error("请先在左侧添加 DeepSeek API Key")
    else:
        selected_key = random.choice(st.session_state.api_keys)
        os.environ["DEEPSEEK_API_KEY"] = selected_key
        key_hint = f"...{selected_key[-8:]}"
        date_str = str(analysis_date)
        st.info(f"正在分析 **{ticker}**（截止 {date_str}）· Key: `{key_hint}` · 预计 2~5 分钟...")

        log_placeholder = st.empty()
        log_lines = []

        class StreamCapture(io.StringIO):
            def write(self, text):
                if text.strip():
                    log_lines.append(text.rstrip())
                    log_placeholder.code("\n".join(log_lines[-30:]), language=None)
                return super().write(text)

        state = decision = error = None
        try:
            with contextlib.redirect_stdout(StreamCapture()):
                config = DEFAULT_CONFIG.copy()
                ta = TradingAgentsGraph(debug=True, config=config)
                state, decision = ta.propagate(ticker, date_str)
        except Exception as e:
            error = str(e)

        log_placeholder.empty()

        if error:
            if "rate" in error.lower() or "429" in error:
                st.error(f"❌ 速率限制：Key `{key_hint}` 触发限流，请稍后重试或添加更多 Key")
            else:
                st.error(f"❌ 分析失败：{error}")
            if log_lines:
                with st.expander("查看日志"):
                    st.code("\n".join(log_lines), language=None)
        else:
            st.success(f"✅ {ticker} 分析完成（Key: `{key_hint}`）")
            d_key = (decision or "").strip().lower()
            icon, label, color = DECISION_DISPLAY.get(d_key, ("📊", decision or "未知", "gray"))
            st.markdown(f"## {icon} 最终建议：:{color}[**{label}**]")
            for rk in ["final_trade_decision", "investment_plan", "trader_investment_plan", "final_report", "portfolio_decision"]:
                val = (state or {}).get(rk)
                if val and isinstance(val, str) and len(val) > 50:
                    st.subheader(f"📄 {rk.replace('_', ' ').title()}")
                    st.markdown(val)
            if state and isinstance(state, dict):
                with st.expander("📋 查看完整分析数据"):
                    for k, v in state.items():
                        if v and k != "messages":
                            st.markdown(f"**{k}**")
                            st.markdown(v[:3000] + ("..." if isinstance(v, str) and len(v) > 3000 else "") if isinstance(v, str) else str(v)[:500])
            if log_lines:
                with st.expander("🔍 查看 Agent 运行日志"):
                    st.code("\n".join(log_lines), language=None)
