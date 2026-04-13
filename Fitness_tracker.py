import streamlit as st
import pandas as pd
import os
from datetime import date

# 页面配置
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

# --- 侧边栏：精准状态矩阵 ---
st.sidebar.header("📊 今日状态矩阵")
st.sidebar.markdown("系统将根据运动与科研的交集自动计算系数。")

# 定义三个等级：0-低, 1-正常, 2-高强度
train_level = st.sidebar.select_slider(
    "今日运动状态",
    options=["休息/久坐", "正常训练", "高强度/冲重"],
    value="正常训练"
)

study_level = st.sidebar.select_slider(
    "今日科研状态",
    options=["轻松/无事", "正常科研", "高压科研/冲刺"],
    value="正常科研"
)

# --- 映射逻辑矩阵 ---
delta = 0.0

# 将状态转换为数值索引方便判断
e_idx = ["休息/久坐", "正常训练", "高强度/冲重"].index(train_level)
s_idx = ["轻松/无事", "正常科研", "高压科研/冲刺"].index(study_level)

# 核心逻辑实现
if e_idx == 0 and s_idx == 0:
    delta = -0.3  # 双低
elif (e_idx == 0 and s_idx == 1) or (e_idx == 1 and s_idx == 0):
    delta = -0.1  # 单一低功耗
elif e_idx == 1 and s_idx == 1:
    delta = 0.0   # 双正常（保持 3.0x）
elif (e_idx == 2 and s_idx < 2) or (s_idx == 2 and e_idx < 2):
    delta = 0.3   # 单项高压
elif e_idx == 2 and s_idx == 2:
    delta = 0.5   # 极限双高

targets = calculate_targets(USER_WEIGHT, delta)

# --- 主界面 ---
st.title("🏋️‍♂️ Alpha-Tracker 营养监控看板")

coeff_display = f"3.0x {'+' if delta >= 0 else ''}{delta}x = {targets['actual_coeff']:.1f}x"
st.subheader(f"🎯 今日碳水目标：{targets['c_target']:.1f}g")
st.info(f"💡 当前调节逻辑：{train_level} + {study_level} → 系数 **{coeff_display}**")

with st.form("输入表单"):
    col1, col2, col3, col4 = st.columns(4)
    with col1: in_kcal = st.number_input("今日总热量 (kcal)", min_value=0.0)
    with col2: in_carb = st.number_input("碳水化合物 (g)", min_value=0.0)
    with col3: in_pro = st.number_input("蛋白质 (g)", min_value=0.0)
    with col4: in_fat = st.number_input("脂肪 (g)", min_value=0.0)
    submitted = st.form_submit_button("保存记录")

if submitted:
    st.divider()
    # 反馈提醒
    if in_pro < targets['p_range'][0]:
        st.warning(f"⚠️ 蛋白偏低：需补足 {targets['p_range'][0] - in_pro:.1f}g")
    elif in_pro > targets['p_range'][1]:
        st.info("✅ 蛋白充足")
    else:
        st.success(f"🌟 蛋白完美")

    if in_fat > targets['f_range'][1]:
        st.error(f"🚨 脂肪偏高：上限为 {targets['f_range'][1]:.1f}g")
    else:
        st.success("✅ 脂肪控制达标")

    # 数据持久化
    new_data = {
        "日期": str(date.today()),
        "总热量": in_kcal, 
        "碳水": in_carb, 
        "蛋白质": in_pro, 
        "脂肪": in_fat,
        "碳水目标": targets['c_target'],
        "动态调整系数": coeff_display
    }
    df_new = pd.DataFrame([new_data])
    file_exists = os.path.isfile('diet_log.csv')
    df_new.to_csv('diet_log.csv', mode='a', index=False, header=not file_exists)
    st.toast("数据已同步！")

# --- 历史管理 ---
st.divider()
st.header("📖 历史数据管理")

if os.path.isfile('diet_log.csv'):
    history_df = pd.read_csv('diet_log.csv')
    # 强制汉化表头
    column_mapping = {"Date": "日期", "Kcal": "总热量", "Carb": "碳水", "Protein": "蛋白质", "Fat": "脂肪", "Carb_Target": "碳水目标", "Delta": "动态调整系数"}
    history_df.rename(columns=column_mapping, inplace=True)

    st.write("💡 修改数值后请务必点击下方按钮同步：")
    edited_df = st.data_editor(history_df, num_rows="dynamic", use_container_width=True)
    
    if st.button("同步修改并保存"):
        edited_df.to_csv('diet_log.csv', index=False)
        st.success("云端数据已更新！")
        st.rerun()
