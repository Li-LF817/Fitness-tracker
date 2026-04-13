import streamlit as st
import pandas as pd
import os
from datetime import date

st.set_page_config(page_title="Alpha-Tracker 营养助手", layout="wide")

# --- 1. 核心逻辑与目标计算 ---
USER_WEIGHT = 75.0 

def get_targets(weight, delta=0):
    final_coeff = 3.0 + delta
    return {
        "p_target": weight * 1.5,
        "p_range": (weight * 1.4, weight * 1.6),
        "f_max": weight * 0.6,
        "c_target": final_coeff * weight,
        "actual_coeff": final_coeff
    }

# --- 2. 侧边栏：状态判定 ---
st.sidebar.header("📊 今日状态判定")
train_level = st.sidebar.select_slider("运动强度", options=["休息/不训练", "正常训练", "高强度/冲重"], value="休息/不训练")
study_level = st.sidebar.select_slider("科研状态", options=["轻松/不科研", "正常科研", "高压科研/冲刺"], value="正常科研")

delta = 0.0
if study_level == "正常科研" and train_level == "休息/不训练": delta = 0.0
elif study_level == "正常科研" and train_level == "正常训练": delta = 0.2
elif study_level == "高压科研/冲刺" or train_level == "高强度/冲重":
    delta = 0.5 if (study_level == "高压科研/冲刺" and train_level == "高强度/冲重") else 0.3
elif study_level == "轻松/不科研" and train_level == "休息/不训练": delta = -0.3
else: delta = -0.1

targets = get_targets(USER_WEIGHT, delta)

# --- 3. 实时摄入录入 (分餐制) ---
st.title("🍎 饮食决策看板")

# 使用 Expander 折叠各餐，保持界面整洁
with st.expander("📝 点击记录各餐摄入", expanded=True):
    tabs = st.tabs(["🌅 早餐", "☀️ 午餐", "🌙 晚餐", "🍎 加餐/零食"])
    
    with tabs[0]:
        c1, c2, c3 = st.columns(3)
        b_c = c1.number_input("早餐碳水(g)", min_value=0.0, key="b_c")
        b_p = c2.number_input("早餐蛋白(g)", min_value=0.0, key="b_p")
        b_f = c3.number_input("早餐脂肪(g)", min_value=0.0, key="b_f")
    with tabs[1]:
        c1, c2, c3 = st.columns(3)
        l_c = c1.number_input("午餐碳水(g)", min_value=0.0, key="l_c")
        l_p = c2.number_input("午餐蛋白(g)", min_value=0.0, key="l_p")
        l_f = c3.number_input("午餐脂肪(g)", min_value=0.0, key="l_f")
    with tabs[2]:
        c1, c2, c3 = st.columns(3)
        d_c = c1.number_input("晚餐碳水(g)", min_value=0.0, key="d_c")
        d_p = c2.number_input("晚餐蛋白(g)", min_value=0.0, key="d_p")
        d_f = c3.number_input("晚餐脂肪(g)", min_value=0.0, key="d_f")
    with tabs[3]:
        c1, c2, c3 = st.columns(3)
        s_c = c1.number_input("加餐碳水(g)", min_value=0.0, key="s_c")
        s_p = c2.number_input("加餐蛋白(g)", min_value=0.0, key="s_p")
        s_f = c3.number_input("加餐脂肪(g)", min_value=0.0, key="s_f")

# 累计当前摄入
total_c = b_c + l_c + d_c + s_c
total_p = b_p + l_p + d_p + s_p
total_f = b_f + l_f + d_f + s_f

# --- 4. 实时决策仪表盘 ---
st.divider()
st.header("⚖️ 剩余预算与建议")

# 计算剩余量
rem_c = targets['c_target'] - total_c
rem_p = targets['p_target'] - total_p
rem_f = targets['f_max'] - total_f

col1, col2, col3 = st.columns(3)
col1.metric("剩余碳水 (g)", f"{rem_c:.1f}", delta=f"已摄入 {total_c:.1f}", delta_color="inverse")
col2.metric("剩余蛋白 (g)", f"{rem_p:.1f}", delta=f"已摄入 {total_p:.1f}", delta_color="normal")
col3.metric("剩余脂肪 (g)", f"{rem_f:.1f}", delta=f"已摄入 {total_f:.1f}", delta_color="inverse")

# --- 5. 智能教练提示系统 ---
st.subheader("💡 教练即时建议")

if total_c == 0 and total_p == 0:
    st.info("尚未开始今日记录。请在上方输入你的第一餐。")
else:
    # 蛋白提示
    if rem_p > 40:
        st.warning(f"蛋白缺口较大 ({rem_p:.1f}g)。下一餐建议增加：鸡胸肉、瘦牛肉或补剂。")
    elif rem_p <= 0:
        st.success("今日蛋白质已达标，身体修复燃料充足！")
    
    # 脂肪提示
    if rem_f < 5:
        st.error("脂肪预算即将耗尽！后续请避开油炸、坚果及肥肉，选择清蒸或水煮。")
    
    # 碳水决策
    if rem_c > 100:
        st.info("碳水余量充足。如果晚间有训练，请在练前补充复合碳水。")
    elif rem_c < 0:
        st.error(f"碳水已超标 ({abs(rem_c):.1f}g)！建议下一餐严格控制主食，以蔬菜填补饱腹感。")

# --- 6. 数据保存 ---
st.divider()
if st.button("💾 确认并保存全天总计"):
    new_data = {
        "日期": str(date.today()), "碳水": total_c, "蛋白质": total_p, "脂肪": total_f,
        "碳水目标": targets['c_target'], "动态调整系数": f"3.0x + {delta}x"
    }
    df_new = pd.DataFrame([new_data])
    file_exists = os.path.isfile('diet_log.csv')
    df_new.to_csv('diet_log.csv', mode='a', index=False, header=not file_exists)
    st.success("全天数据已汇总并存档。")

# --- 7. 历史管理 ---
st.header("📖 历史记录")
if os.path.isfile('diet_log.csv'):
    history_df = pd.read_csv('diet_log.csv')
    st.data_editor(history_df, num_rows="dynamic", use_container_width=True)
