import streamlit as st
import pandas as pd
import os
from datetime import date

st.set_page_config(page_title="Alpha-Tracker 生理建模版", layout="wide")

# --- 1. 身体数据与 TDEE 计算逻辑 ---
st.sidebar.header("👤 个人身体档案")
gender = st.sidebar.radio("性别", ["男", "女"], index=0)
age = st.sidebar.number_input("年龄", min_value=15, max_value=80, value=24)
height = st.sidebar.number_input("身高 (cm)", min_value=140, max_value=210, value=183)
weight = st.sidebar.number_input("体重 (kg)", min_value=40.0, max_value=150.0, value=75.0)

st.sidebar.divider()
st.sidebar.header("⚡ 能量消耗设定")
# 活动水平系数 (PAL)
pal_options = {
    "久坐 (几乎不运动)": 1.2,
    "轻度活跃 (每周1-2次)": 1.375,
    "中度活跃 (每周3-5次)": 1.55,
    "高度活跃 (每日运动)": 1.725
}
pal_val = st.sidebar.selectbox("日常活动水平", list(pal_options.keys()), index=2)
pal = pal_options[pal_val]

# 热量缺口设定
deficit = st.sidebar.slider("目标热量缺口 (kcal)", 0, 800, 400, step=50)

# 计算 BMR (Mifflin-St Jeor)
if gender == "男":
    bmr = 10 * weight + 6.25 * height - 5 * age + 5
else:
    bmr = 10 * weight + 6.25 * height - 5 * age - 161

tdee = bmr * pal
daily_target_kcal = tdee - deficit

# --- 2. 自动推导营养基准 ---
# 蛋白质固定 1.5x，脂肪固定 0.6x
p_gram = weight * 1.5
f_gram = weight * 0.6
p_kcal = p_gram * 4
f_kcal = f_gram * 9

# 剩余热量全给碳水，推导基准系数
c_kcal_baseline = daily_target_kcal - p_kcal - f_kcal
c_gram_baseline = c_kcal_baseline / 4
base_coeff = c_gram_baseline / weight # 自动生成的基准系数

# --- 3. 状态决策矩阵 (Delta 调整) ---
st.sidebar.divider()
st.sidebar.header("📊 今日状态微调")
train_level = st.sidebar.select_slider("运动强度", options=["休息/不训练", "正常训练", "高强度/冲重"], value="休息/不训练")
study_level = st.sidebar.select_slider("科研状态", options=["轻松/不科研", "正常科研", "高压科研/冲刺"], value="正常科研")

delta = 0.0
if study_level == "正常科研" and train_level == "休息/不训练": delta = 0.0
elif study_level == "正常科研" and train_level == "正常训练": delta = 0.2
elif study_level == "高压科研/冲刺" and train_level == "高强度/冲重": delta = 0.5
elif study_level == "高压科研/冲刺" or train_level == "高强度/冲重": delta = 0.3
elif study_level == "轻松/不科研" and train_level == "休息/不训练": delta = -0.3
else: delta = -0.1

final_coeff = base_coeff + delta
c_target_final = final_coeff * weight

# 侧边栏看板
st.sidebar.divider()
st.sidebar.metric("TDEE (总消耗)", f"{tdee:.0f} kcal")
st.sidebar.metric("建议摄入系数", f"{final_coeff:.2f}x", f"{delta:+.1f}x (状态调整)")

# --- 4. 饮食决策中心 ---
st.title(f"🚀 Alpha-Tracker 决策中心")
st.info(f"💡 根据身体档案，你的 BMR 为 **{bmr:.0f}**，TDEE 为 **{tdee:.0f}**。设定缺口 **{deficit}** kcal 后，今日建议摄入总热量：**{daily_target_kcal:.0f}** kcal。")

# 辅助函数：将 None 转换为 0.0
def nz(value):
    return value if value is not None else 0.0

with st.expander("📝 开启分餐辅助计算器", expanded=False):
    tabs = st.tabs(["🌅 早", "☀️ 午", "🌙 晚", "🍎 加"])
    meals = ["b", "l", "d", "s"]
    meal_data = {}
    for i, m in enumerate(meals):
        with tabs[i]:
            c1, c2, c3, c4 = st.columns(4)
            meal_data[f"{m}_k"] = c1.number_input(f"热量", value=None, placeholder="0.0", key=f"{m}_k")
            meal_data[f"{m}_c"] = c2.number_input(f"碳水", value=None, placeholder="0.0", key=f"{m}_c")
            meal_data[f"{m}_p"] = c3.number_input(f"蛋白", value=None, placeholder="0.0", key=f"{m}_p")
            meal_data[f"{m}_f"] = c4.number_input(f"脂肪", value=None, placeholder="0.0", key=f"{m}_f")

    if st.button("🔢 汇总并更新下方总量"):
        st.session_state.total_k = sum(nz(meal_data[f"{m}_k"]) for m in meals)
        st.session_state.total_c = sum(nz(meal_data[f"{m}_c"]) for m in meals)
        st.session_state.total_p = sum(nz(meal_data[f"{m}_p"]) for m in meals)
        st.session_state.total_f = sum(nz(meal_data[f"{m}_f"]) for m in meals)
        st.rerun()

st.subheader("🏁 今日摄入数据汇总")
col1, col2, col3, col4 = st.columns(4)
tk = col1.number_input("总热量(kcal)", value=st.session_state.get('total_k', None), placeholder="必填", key="tk")
tc = col2.number_input("总碳水(g)", value=st.session_state.get('total_c', None), placeholder="必填", key="tc")
tp = col3.number_input("总蛋白(g)", value=st.session_state.get('total_p', None), placeholder="必填", key="tp")
tf = col4.number_input("总脂肪(g)", value=st.session_state.get('total_f', None), placeholder="必填", key="tf")

# --- 5. 实时剩余预算 ---
st.divider()
cur_c, cur_p, cur_f = nz(tc), nz(tp), nz(tf)
rem_c, rem_p, rem_f = c_target_final - cur_c, p_gram - cur_p, f_gram - cur_f

m1, m2, m3 = st.columns(3)
m1.metric("碳水剩余", f"{rem_c:.1f}g", f"目标 {c_target_final:.0f}g", delta_color="inverse")
m2.metric("蛋白剩余", f"{rem_p:.1f}g", f"目标 {p_gram:.0f}g")
m3.metric("脂肪剩余", f"{rem_f:.1f}g", f"上限 {f_gram:.0f}g", delta_color="inverse")

# --- 6. 存档与管理 ---
target_date = st.date_input("存档日期", date.today())
if st.button("💾 保存/覆盖该日记录"):
    new_row = {
        "日期": str(target_date), "总热量": nz(tk), "碳水": cur_c, "蛋白质": cur_p, 
        "脂肪": cur_f, "碳水目标": c_target_final, "系数": f"{final_coeff:.2f}x", "缺口": deficit
    }
    df_new = pd.DataFrame([new_row])
    if os.path.isfile('diet_log.csv'):
        old_df = pd.read_csv('diet_log.csv')
        old_df = old_df[old_df['日期'] != str(target_date)]
        final_df = pd.concat([old_df, df_new], ignore_index=True)
    else:
        final_df = df_new
    final_df.sort_values(by="日期", ascending=False).to_csv('diet_log.csv', index=False)
    st.success(f"【{target_date}】记录已更新！")

st.divider()
st.header("📖 历史记录管理")
if os.path.isfile('diet_log.csv'):
    edited_df = st.data_editor(pd.read_csv('diet_log.csv'), num_rows="dynamic", use_container_width=True)
    if st.button("🔥 彻底同步修改"):
        edited_df.to_csv('diet_log.csv', index=False)
        st.success("数据已彻底同步！")
        st.rerun()
