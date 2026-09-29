import streamlit as st
import yfinance as yf
import pandas as pd
from fredapi import Fred
from datetime import datetime, timedelta

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="全球资本流雷达",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==================== 访问密码 ====================

password = st.text_input("请输入访问密码", type="password")
if password != st.secrets["APP_PASSWORD"]:
    st.stop()

# ==================== 自定义 CSS ====================
st.markdown("""
<style>
    div[data-testid="stMetric"] {
        background: #ffffff;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        border: 1px solid #f0f0f0;
        margin-bottom: 8px;
    }
    div[data-testid="stMetric"]:hover {
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        transform: translateY(-2px);
        transition: all 0.2s ease;
    }
    div[data-testid="stMetricLabel"] { font-size: 0.9rem !important; color: #555; }
    div[data-testid="stMetricValue"] { font-size: 1.3rem !important; font-weight: 700; }
    div[data-testid="stMetricDelta"] { font-size: 0.85rem !important; }
    @media (max-width: 600px) {
        div[data-testid="stMetricValue"] { font-size: 1.1rem !important; }
        div[data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
    }
    .main-title {
        background: linear-gradient(90deg, #1F4E78, #2E75B6);
        color: white;
        padding: 20px 24px;
        border-radius: 12px;
        margin-bottom: 20px;
    }
    .main-title h1 { margin: 0; font-size: 1.6rem; }
    .main-title p { margin: 6px 0 0 0; font-size: 0.85rem; opacity: 0.85; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-title">
    <h1>🌐 全球资本流雷达</h1>
    <p>Global Capital Flow Radar · 数据自动刷新</p>
</div>
""", unsafe_allow_html=True)

# ==================== FRED 初始化 ====================
try:
    FRED_API_KEY = st.secrets["FRED_API_KEY"]
except Exception:
    FRED_API_KEY = ""

@st.cache_resource
def get_fred_client():
    return Fred(api_key=FRED_API_KEY)

fred = get_fred_client()

# ==================== 数据获取函数 ====================

@st.cache_data(ttl=3600)
def get_fred_latest(series_id):
    """获取 FRED 序列的最新值和前值"""
    try:
        data = fred.get_series(series_id)
        data = data.dropna()
        if len(data) >= 2:
            return float(data.iloc[-1]), float(data.iloc[-2])
        return None, None
    except Exception as e:
        return None, None

@st.cache_data(ttl=600)
def get_yf_latest(ticker):
    """获取 yfinance 的最新收盘价和前一日收盘价"""
    try:
        data = yf.Ticker(ticker).history(period="5d")
        if len(data) >= 2:
            return float(data['Close'].iloc[-1]), float(data['Close'].iloc[-2])
        return None, None
    except Exception:
        return None, None

def calc_delta(current, previous):
    """计算变化率"""
    if current is None or previous is None or previous == 0:
        return 0.0
    return (current - previous) / previous

# ==================== 指标配置 ====================
# 每个指标: (大类图标, 名称, 数据源类型, 标识符, 单位, 信号方向)
# 信号方向: "normal" 涨=流入; "inverse" 涨=撤离(如收益率)
INDICATORS = [
    # --- 股 ---
    ("📈", "标普500", "yf", "^GSPC", "点", "normal"),
    ("📈", "纳斯达克", "yf", "^IXIC", "点", "normal"),
    ("📈", "道琼斯", "yf", "^DJI", "点", "normal"),
    ("📈", "罗素2000", "yf", "^RUT", "点", "normal"),
    ("📈", "费城半导体", "yf", "^SOX", "点", "normal"),
    ("📈", "德国DAX", "yf", "^GDAXI", "点", "normal"),
    ("📈", "英国富时100", "yf", "^FTSE", "点", "normal"),
    ("📈", "法国CAC40", "yf", "^FCHI", "点", "normal"),
    ("📈", "日经225", "yf", "^N225", "点", "normal"),
    ("📈", "韩国KOSPI", "yf", "^KS11", "点", "normal"),
    ("📈", "澳洲标普200", "yf", "^AXJO", "点", "normal"),
    ("📈", "印度Nifty50", "yf", "^NSEI", "点", "normal"),
    ("📈", "巴西IBOVESPA", "yf", "^BVSP", "点", "normal"),
    ("📈", "恒生指数", "yf", "^HSI", "点", "normal"),
    ("📈", "恒生科技", "yf", "^HSTECH", "点", "normal"),
    ("📈", "上证指数", "yf", "000001.SS", "点", "normal"),
    ("📈", "沪深300", "yf", "000300.SS", "点", "normal"),

    # --- 债 ---
    ("📊", "美债2年期", "fred", "DGS2", "%", "inverse"),
    ("📊", "美债10年期", "fred", "DGS10", "%", "inverse"),
    ("📊", "美债30年期", "fred", "DGS30", "%", "inverse"),
    ("📊", "10Y-2Y利差", "fred", "T10Y2Y", "%", "normal"),
    ("📊", "投资级债利差", "fred", "BAMLC0A0CM", "%", "inverse"),
    ("📊", "高收益债利差", "fred", "BAMLH0A0HYM2", "%", "inverse"),

    # --- 汇 ---
    ("💱", "美元指数DXY", "yf", "DX-Y.NYB", "点", "normal"),
    ("💱", "美元广义指数", "fred", "DTWEXBGS", "指数", "normal"),
    ("💱", "欧元/美元", "yf", "EURUSD=X", "汇率", "normal"),
    ("💱", "美元/日元", "yf", "JPY=X", "汇率", "normal"),
    ("💱", "英镑/美元", "yf", "GBPUSD=X", "汇率", "normal"),
    ("💱", "美元/人民币", "yf", "CNY=X", "汇率", "normal"),

    # --- 商品 ---
    ("🛢", "WTI原油", "yf", "CL=F", "美元/桶", "normal"),
    ("🛢", "布伦特原油", "yf", "BZ=F", "美元/桶", "normal"),
    ("🥇", "COMEX黄金", "yf", "GC=F", "美元/盎司", "normal"),
    ("🥈", "COMEX白银", "yf", "SI=F", "美元/盎司", "normal"),
    ("🔩", "COMEX铜", "yf", "HG=F", "美元/磅", "normal"),
    ("🌾", "CBOT大豆", "yf", "ZS=F", "美分/蒲式耳", "normal"),
    ("🌾", "CBOT玉米", "yf", "ZC=F", "美分/蒲式耳", "normal"),

    # --- 加密 ---
    ("💎", "比特币", "yf", "BTC-USD", "美元", "normal"),
    ("💎", "以太坊", "yf", "ETH-USD", "美元", "normal"),

    # --- 资本流 ---
    ("🌊", "美联储总资产", "fred", "WALCL", "百万美元", "normal"),
    ("🚢", "全球供应链压力", "fred", "GSCPI", "指数", "normal"),
]

# ==================== 渲染看板 ====================

categories = {
    "📈": "股 · 股票资金流",
    "📊": "债 · 债券资金流",
    "💱": "汇 · 外汇资金流",
    "🛢": "商品 · 能源",
    "🥇": "商品 · 贵金属",
    "🥈": "商品 · 贵金属",
    "🔩": "商品 · 工业金属",
    "🌾": "商品 · 农产品",
    "💎": "加密资产",
    "🌊": "资本流 · 美元流动性",
    "🚢": "贸易流 · 实体联通",
}

def render_card(icon, name, value_str, unit, signal, delta_pct, is_inflow):
    """渲染单个卡片"""
    color = "#1a7f37" if is_inflow else "#cf222e"  # 绿色流入 / 红色撤离
    bg = "#f0fff4" if is_inflow else "#fff0f0"
    arrow = "↑" if is_inflow else "↓"
    signal_text = "流入" if is_inflow else "撤离"

    html = f"""
    <div style="
        background: {bg};
        border-left: 4px solid {color};
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    ">
        <div style="font-size: 0.85rem; color: #555; margin-bottom: 4px;">
            {icon} {name}
        </div>
        <div style="font-size: 1.15rem; font-weight: 700; color: #222; margin-bottom: 4px;">
            {value_str} <span style="font-size: 0.8rem; color: #888;">{unit}</span>
        </div>
        <div style="font-size: 0.85rem; color: {color}; font-weight: 600;">
            {arrow} {signal_text} ({delta_pct:+.2%})
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# 按大类分组渲染
for cat_icon in ["📈", "📊", "💱", "🛢", "🥇", "🥈", "🔩", "🌾", "💎", "🌊", "🚢"]:
    cat_name = categories.get(cat_icon, cat_icon)
    items = [ind for ind in INDICATORS if ind[0] == cat_icon]
    if not items:
        continue

    st.markdown(f"#### {cat_icon} {cat_name}")

    cols = st.columns(4)
    for i, (icon, name, source, ticker, unit, direction) in enumerate(items):
        with cols[i % 4]:
            if source == "fred":
                current, previous = get_fred_latest(ticker)
            else:
                current, previous = get_yf_latest(ticker)

            if current is None or previous is None:
                st.markdown(f"""
                <div style="background:#f5f5f5; border-radius:10px; padding:14px 16px; margin-bottom:10px;">
                    <div style="font-size:0.85rem; color:#555;">{icon} {name}</div>
                    <div style="font-size:1.1rem; color:#999;">数据不可用</div>
                </div>
                """, unsafe_allow_html=True)
                continue

            delta_pct = calc_delta(current, previous)

            # 判断流入/流出
            if direction == "inverse":
                # 收益率上行 = 撤离债市
                is_inflow = delta_pct < 0
            else:
                is_inflow = delta_pct > 0

            # 格式化数值
            if current >= 1_000_000:
                value_str = f"{current:,.0f}"
            elif current >= 100:
                value_str = f"{current:,.2f}"
            elif current >= 1:
                value_str = f"{current:.4f}"
            else:
                value_str = f"{current:.6f}"

            render_card(icon, name, value_str, unit, "", delta_pct, is_inflow)

st.caption(f"数据自动刷新 · 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}")