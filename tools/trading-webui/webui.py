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

col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
with col1:
    market = st.selectbox("市场", list(MARKET_SUFFIX.keys()))
with col2:
    suffix = MARKET_SUFFIX[market]
    raw_ticker = st.text_input(
        "股票代码（不需要加后缀）",
        value="0700" if "港股" in market else "AAPL" if "美股" in market else "600519" if "上海" in market else "000858" if "深圳" in market else "BTC",
        help=MARKET_EXAMPLES[market]
    )
    ticker = raw_ticker.strip().upper() + suffix
    st.caption(f"完整代码：**{ticker}**　　参考：{MARKET_EXAMPLES[market]}")
with col3:
    analysis_date = st.date_input(
        "分析日期",
        value=date.today() - timedelta(days=1),
        max_value=date.today() - timedelta(days=1),
    )
with col4:
    st.write("")
    st.write("")
    run = st.button("🔍 开始分析", type="primary", use_container_width=True)

if run:
    if not raw_ticker.strip():
        st.error("请输入股票代码")
    else:
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
