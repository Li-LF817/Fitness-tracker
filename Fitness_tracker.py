import streamlit as st
import pandas as pd
import os
from datetime import date

st.set_page_config(page_title="Alpha-Tracker 营养助手", layout="wide")

# --- 核心逻辑 ---
USER_WEIGHT = 75.0 

def calculate_targets(weight, delta=0):
    final_coeff = 3.0 + delta
    return {
        "p_range": (weight * 1.4, weight * 1.6),
        "p_std": weight * 1.5,
        "f_range": (weight * 0.5, weight * 0.6),
        "c_target": final_coeff * weight,
        "actual_coeff": final_coeff
    }

# --- 侧边栏：研究员日常状态设定 ---
st.sidebar.header("📊 今日状态矩阵")
st.sidebar.markdown("基准：正常科研+不训练 = 3.0x")

train_level = st.sidebar.select_slider(
    "今日运动状态",
    options=["休息/不训练", "正常训练", "高强度/冲重"],
    value="休息/不训练"
)

study_level = st.sidebar.select_slider(
    "今日科研状态",
    options=["轻松/不科研", "正常科研", "高压科研/冲刺"],
    value="正常科研"
)

# --- 核心逻辑矩阵实现 ---
delta = 0.0

# 判定逻辑
if study_level == "正常科研" and train_level == "休息/不训练":
    delta = 0.0  # 你的生活常态，保持基准
elif study_level == "正常科研" and train_level == "正常训练":
    delta = 0.2  # 科研常态下叠加了训练，上调
elif study_level == "高压科研/冲刺" or train_level == "高强度/冲重":
    # 只要有一项是极高，就开始上调
    if study_level == "高压科研/冲刺" and train_level == "高强度/冲重":
        delta = 0.5 # 双高
    else:
        delta = 0.3 # 单高
elif study_level == "轻松/不科研" and train_level == "休息/不训练":
    delta = -0.3 # 彻底休息，下调
elif study_level == "轻松/不科研" or train_level == "休息/不训练":
    # 针对“单一低功耗”场景的微调
    delta = -0.1

targets = calculate_targets(USER_WEIGHT, delta)

# --- 主界面 ---
st.title("🏋️‍♂️ Alpha-Tracker 营养监控看板")

coeff_display = f"3.0x {'+' if delta >= 0 else ''}{delta}x = {targets['actual_coeff']:.1f}x"
st.subheader(f"🎯 今日碳水目标：{targets['c_target']:.1f}g")
st.info(f"💡 逻辑状态：[{study_level}] + [{train_level}] → 当前系数 **{coeff_display}**")

with st.form("输入表单"):
    col1, col2, col3, col4 = st.columns(4)
    with col1: in_kcal = st.number_input("今日总热量 (kcal)", min_value=0.0)
    with col2: in_carb = st.number_input("碳水化合物 (g)", min_value=0.0)
    with col3: in_pro = st.number_input("蛋白质 (g)", min_value=0.0)
    with col4: in_fat = st.number_input("脂肪 (g)", min_value=0.0)
    submitted = st.form_submit_button("确认并保存记录")

if submitted:
    st.divider()
    # 蛋白质反馈
    if in_pro < targets['p_range'][0]:
        st.warning(f"⚠️ 蛋白偏低：距标准还差 {targets['p_range'][0] - in_pro:.1f}g")
    elif in_pro > targets['p_range'][1]:
        st.info("✅ 蛋白充足")
    else:
        st.success(f"🌟 蛋白完美 (1.4x-1.6x)")

    # 脂肪反馈
    if in_fat > targets['f_range'][1]:
        st.error(f"🚨 脂肪偏高：上限为 {targets['f_range'][1]:.1f}g")
    else:
        st.success("✅ 脂肪控制达标")

    # 数据记录
    new_data = {
        "日期": str(date.today()), "总热量": in_kcal, "碳水": in_carb, 
        "蛋白质": in_pro, "脂肪": in_fat, "碳水目标": targets['c_target'],
        "动态调整系数": coeff_display
    }
    df_new = pd.DataFrame([new_data])
    file_exists = os.path.isfile('diet_log.csv')
    df_new.to_csv('diet_log.csv', mode='a', index=False, header=not file_exists)
    st.toast("记录已保存")

# --- 历史管理 ---
st.divider()
st.header("📖 历史记录管理")
if os.path.isfile('diet_log.csv'):
    history_df = pd.read_csv('diet_log.csv')
    column_mapping = {"Date": "日期", "Kcal": "总热量", "Carb": "碳水", "Protein": "蛋白质", "Fat": "脂肪", "Carb_Target": "碳水目标", "Delta": "动态调整系数"}
    history_df.rename(columns=column_mapping, inplace=True)
    st.write("💡 直接在表格中修改，选中行按 Delete 删除：")
    edited_df = st.data_editor(history_df, num_rows="dynamic", use_container_width=True)
    if st.button("同步所有修改"):
        edited_df.to_csv('diet_log.csv', index=False)
        st.success("云端数据同步完成！")
        st.rerun()
