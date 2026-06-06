import streamlit as st
import sys
import os
import io
import contextlib
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

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    ticker = st.text_input(
        "股票代码",
        value="0700.HK",
        placeholder="AAPL / 0700.HK / 600519.SS / BTC-USD",
        help="港股加 .HK，A股加 .SS（上海）或 .SZ（深圳）"
    )
with col2:
    analysis_date = st.date_input(
        "分析日期",
        value=date.today() - timedelta(days=1),
        max_value=date.today() - timedelta(days=1),
        help="选择分析截止日期，建议用昨天或更早"
    )
with col3:
    st.write("")
    st.write("")
    run = st.button("🔍 开始分析", type="primary", use_container_width=True)

if run:
    if not ticker.strip():
        st.error("请输入股票代码")
    else:
        ticker = ticker.strip().upper()
        date_str = str(analysis_date)

        st.info(f"正在分析 **{ticker}**（截止 {date_str}），多智能体协作分析中，预计需要 2~5 分钟...")

        log_placeholder = st.empty()
        log_lines = []

        class StreamCapture(io.StringIO):
            def write(self, text):
                if text.strip():
                    log_lines.append(text.rstrip())
                    log_placeholder.code("\n".join(log_lines[-30:]), language=None)
                return super().write(text)

        capture = StreamCapture()
        decision = None
        error = None

        try:
            with contextlib.redirect_stdout(capture):
                config = DEFAULT_CONFIG.copy()
                ta = TradingAgentsGraph(debug=True, config=config)
                _, decision = ta.propagate(ticker, date_str)
        except Exception as e:
            error = str(e)

        log_placeholder.empty()

        if error:
            st.error(f"❌ 分析失败：{error}")
            if log_lines:
                with st.expander("查看日志"):
                    st.code("\n".join(log_lines), language=None)
        else:
            st.success(f"✅ {ticker} 分析完成")
            st.subheader("📊 分析结论")
            st.markdown(decision if decision else "_（无输出）_")

            if log_lines:
                with st.expander("查看详细分析过程"):
                    st.code("\n".join(log_lines), language=None)

st.divider()
st.caption("常用代码：AAPL · TSLA · NVDA · 0700.HK（腾讯）· 9988.HK（阿里）· 600519.SS（茅台）· BTC-USD")
