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
st.sidebar.header("📊 今日状态")
train_level = st.sidebar.select_slider("今日运动", options=["休息/不训练", "正常训练", "高强度/冲重"], value="休息/不训练")
study_level = st.sidebar.select_slider("今日科研", options=["轻松/不科研", "正常科研", "高压科研/冲刺"], value="正常科研")

# 你的专属逻辑：正常科研+不训练=3.0x
delta = 0.0
if study_level == "正常科研" and train_level == "休息/不训练": delta = 0.0
elif study_level == "正常科研" and train_level == "正常训练": delta = 0.2
elif study_level == "高压科研/冲刺" or train_level == "高强度/冲重":
    delta = 0.5 if (study_level == "高压科研/冲刺" and train_level == "高强度/冲重") else 0.3
elif study_level == "轻松/不科研" and train_level == "休息/不训练": delta = -0.3
else: delta = -0.1

targets = get_targets(USER_WEIGHT, delta)

# --- 3. 饮食录入区 ---
st.title("饮食摄入管理")

# 可选：分餐明细（选填）
with st.expander("可选：分餐详细记录", expanded=False):
    st.caption("如果你填写了分餐明细，可以点击下方的按钮同步到今日总量。")
    tabs = st.tabs(["🌅 早餐", "☀️ 午餐", "🌙 晚餐", "🍎 加餐"])
    
    with tabs[0]:
        c1, c2, c3, c4 = st.columns(4)
        b_k = c1.number_input("早餐热量(kcal)", min_value=0.0, key="b_k")
        b_c = c2.number_input("早餐碳水(g)", min_value=0.0, key="b_c")
        b_p = c3.number_input("早餐蛋白(g)", min_value=0.0, key="b_p")
        b_f = c4.number_input("早餐脂肪(g)", min_value=0.0, key="b_f")
    with tabs[1]:
        c1, c2, c3, c4 = st.columns(4)
        l_k = c1.number_input("午餐热量(kcal)", min_value=0.0, key="l_k")
        l_c = c2.number_input("午餐碳水(g)", min_value=0.0, key="l_c")
        l_p = c3.number_input("午餐蛋白(g)", min_value=0.0, key="l_p")
        l_f = c4.number_input("午餐脂肪(g)", min_value=0.0, key="l_f")
    with tabs[2]:
        c1, c2, c3, c4 = st.columns(4)
        d_k = c1.number_input("晚餐热量(kcal)", min_value=0.0, key="d_k")
        d_c = c2.number_input("晚餐碳水(g)", min_value=0.0, key="d_c")
        d_p = c3.number_input("晚餐蛋白(g)", min_value=0.0, key="d_p")
        d_f = c4.number_input("晚餐脂肪(g)", min_value=0.0, key="d_f")
    with tabs[3]:
        c1, c2, c3, c4 = st.columns(4)
        s_k = c1.number_input("加餐热量(kcal)", min_value=0.0, key="s_k")
        s_c = c2.number_input("加餐碳水(g)", min_value=0.0, key="s_c")
        s_p = c3.number_input("加餐蛋白(g)", min_value=0.0, key="s_p")
        s_f = c4.number_input("加餐脂肪(g)", min_value=0.0, key="s_f")

    use_meal_details = st.button("将上述分餐加总同步到下方总量")

# 核心：今日总量记录（必填）
st.subheader("今日摄入总计")
col1, col2, col3, col4 = st.columns(4)

# 逻辑：如果点击了同步，则默认值为分餐之和
init_k = (b_k + l_k + d_k + s_k) if use_meal_details else 0.0
init_c = (b_c + l_c + d_c + s_c) if use_meal_details else 0.0
init_p = (b_p + l_p + d_p + s_p) if use_meal_details else 0.0
init_f = (b_f + l_f + d_f + s_f) if use_meal_details else 0.0

total_k = col1.number_input("总热量(kcal)", min_value=0.0, value=init_k)
total_c = col2.number_input("总碳水(g)", min_value=0.0, value=init_c)
total_p = col3.number_input("总蛋白(g)", min_value=0.0, value=init_p)
total_f = col4.number_input("总脂肪(g)", min_value=0.0, value=init_f)

# --- 4. 实时预算与建议 ---
st.divider()
st.header("⚖️ 剩余饮食摄入预算")

rem_c = targets['c_target'] - total_c
rem_p = targets['p_target'] - total_p
rem_f = targets['f_max'] - total_f

m1, m2, m3 = st.columns(3)
m1.metric("剩余碳水 (g)", f"{rem_c:.1f}", delta=f"目标 {targets['c_target']:.0f}", delta_color="inverse")
m2.metric("剩余蛋白 (g)", f"{rem_p:.1f}", delta=f"目标 {targets['p_target']:.0f}")
m3.metric("剩余脂肪 (g)", f"{rem_f:.1f}", delta=f"上限 {targets['f_max']:.0f}", delta_color="inverse")

# 智能提示
if total_c > 0 or total_p > 0:
    if rem_p > 30: st.warning(f"蛋白缺口较大 ({rem_p:.1f}g)，建议增加肉蛋类摄入。")
    if rem_f < 5: st.error("脂肪预算将尽，请避开油炸及坚果。")
    if rem_c < 0: st.error(f"碳水已超标 {abs(rem_c):.1f}g，建议控制后续主食。")
    if rem_c > 80: st.info("碳水余量充足，可满足后续高强度学习或训练。")

# --- 5. 数据保存 ---
if st.button("💾 保存今日汇总数据"):
    if total_k == 0 and total_c == 0:
        st.error("请至少输入总量数据后再保存。")
    else:
        new_data = {
            "日期": str(date.today()), "总热量": total_k, "碳水": total_c, 
            "蛋白质": total_p, "脂肪": total_f, "碳水目标": targets['c_target'],
            "动态调整系数": f"3.0x {'+' if delta >= 0 else ''}{delta}x"
        }
        df_new = pd.DataFrame([new_data])
        file_exists = os.path.isfile('diet_log.csv')
        df_new.to_csv('diet_log.csv', mode='a', index=False, header=not file_exists)
        st.success(f"已存档：今日总热量 {total_k} kcal，碳水系数 {3.0+delta:.1f}x")

# --- 6. 历史记录 ---
st.divider()
st.header("📖 历史数据")
if os.path.isfile('diet_log.csv'):
    history_df = pd.read_csv('diet_log.csv')
    st.data_editor(history_df, num_rows="dynamic", use_container_width=True)
