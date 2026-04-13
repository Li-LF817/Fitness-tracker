import streamlit as st
import pandas as pd
import os
from datetime import date

# 页面设置
st.set_page_config(page_title="营养达标助手", layout="wide")

# --- 核心配置 ---
USER_WEIGHT = 75.0  # 基准体重

def calculate_targets(weight, delta=0):
    return {
        "p_range": (weight * 1.4, weight * 1.6),
        "p_std": weight * 1.5,
        "f_range": (weight * 0.5, weight * 0.6),
        "c_target": (3.0 + delta) * weight
    }

# --- 侧边栏：状态自评 ---
st.sidebar.header("📊 状态自评")
train_status = st.sidebar.select_slider(
    "过去几天的训练强度",
    options=["休息", "低强度", "正常强度", "高强度/冲重"],
    value="正常强度"
)
study_stress = st.sidebar.select_slider(
    "学业/脑力压力",
    options=["轻松", "中等", "高压科研", "极度疲劳"],
    value="中等"
)

# 动态系数映射
delta = 0
if train_status == "高强度/冲重": delta += 0.5
if study_stress == "高压科研": delta += 0.3
elif study_stress == "极度疲劳": delta += 0.6

targets = calculate_targets(USER_WEIGHT, delta)

# --- 主界面 ---
st.title("🍎 个人饮食营养监控看板")
st.subheader(f"💡 今日建议：碳水应摄入 {targets['c_target']:.1f}g (当前倍数: {3.0+delta}x)")

with st.form("输入表单"):
    col1, col2, col3, col4 = st.columns(4)
    with col1: in_kcal = st.number_input("今日总热量 (kcal)", min_value=0.0)
    with col2: in_carb = st.number_input("碳水化合物 (g)", min_value=0.0)
    with col3: in_pro = st.number_input("蛋白质 (g)", min_value=0.0)
    with col4: in_fat = st.number_input("脂肪 (g)", min_value=0.0)
    
    submitted = st.form_submit_button("保存今日记录")

if submitted:
    st.divider()
    # 蛋白质反馈
    if in_pro < targets['p_range'][0]:
        st.warning(f"⚠️ 蛋白偏低：距最低标准还差 {targets['p_range'][0] - in_pro:.1f}g")
    elif in_pro > targets['p_range'][1]:
        st.info("✅ 蛋白充足：已超过 1.6 倍上限")
    else:
        st.success(f"🌟 蛋白完美：处于 1.4-1.6 倍区间 (标准值: {targets['p_std']:.1f}g)")

    # 脂肪反馈
    if in_fat > targets['f_range'][1]:
        st.error(f"🚨 脂肪超标：已超过上限 {targets['f_range'][1]:.1f}g")
    else:
        st.success("✅ 脂肪控制达标")

    # 碳水偏差
    c_diff = in_carb - targets['c_target']
    st.metric("碳水达成偏差", f"{in_carb}g", f"{c_diff:.1f}g", delta_color="inverse")

    # 数据持久化
    new_data = {
        "日期": str(date.today()),
        "总热量": in_kcal, "碳水": in_carb, "蛋白质": in_pro, "脂肪": in_fat,
        "碳水目标": targets['c_target']
    }
    df_new = pd.DataFrame([new_data])
    file_exists = os.path.isfile('diet_log.csv')
    df_new.to_csv('diet_log.csv', mode='a', index=False, header=not file_exists)
    st.toast("数据已保存！")

# --- 历史记录管理 (修改/删除) ---
st.divider()
st.header("📖 历史数据管理")

if os.path.isfile('diet_log.csv'):
    history_df = pd.read_csv('diet_log.csv')
    
    st.write("💡 你可以直接在下方表格中修改数值，或选中行按 Delete 键删除记录：")
    # 使用 data_editor 实现交互式修改
    edited_df = st.data_editor(
        history_df, 
        num_rows="dynamic",  # 允许删除/添加行
        use_container_width=True,
        key="history_editor"
    )
    
    if st.button("同步修改并保存"):
        edited_df.to_csv('diet_log.csv', index=False)
        st.success("历史数据已更新！")
        st.rerun()  # 刷新页面以显示最新数据
else:
    st.info("暂无历史记录，开始你的第一笔记录吧！")
