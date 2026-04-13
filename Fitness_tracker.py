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

# --- 2. 侧边栏：带预判的决策矩阵 ---
st.sidebar.header("📊 状态决策矩阵")

# 定义状态对应的单项描述（为了提示用户）
train_options = {
    "休息/不训练": "保持基准 (0.0)",
    "正常训练": "需求上调 (+0.2)",
    "高强度/冲重": "需求激增 (+0.3~0.5)"
}

study_options = {
    "轻松/不科研": "消耗降低 (-0.1~0.3)",
    "正常科研": "保持基准 (0.0)",
    "高压科研/冲刺": "需求上调 (+0.3~0.5)"
}

# 侧边栏滑块
train_val = st.sidebar.select_slider(
    "今日运动强度",
    options=list(train_options.keys()),
    value="休息/不训练",
    help="训练会消耗肌糖原，需要额外碳水修复。"
)
st.sidebar.caption(f"💡 运动影响预期：{train_options[train_val]}")

study_val = st.sidebar.select_slider(
    "今日科研状态",
    options=list(study_options.keys()),
    value="正常科研",
    help="高强度脑力劳动会消耗大量葡萄糖。"
)
st.sidebar.caption(f"💡 科研影响预期：{study_options[study_val]}")

# --- 核心复合逻辑计算 ---
delta = 0.0
e_idx = list(train_options.keys()).index(train_val)
s_idx = list(study_options.keys()).index(study_val)

# 应用你定义的“研究员稳态”逻辑
if s_idx == 1 and e_idx == 0:
    delta = 0.0  # 正常科研 + 不训练 = 3.0x
elif s_idx == 1 and e_idx == 1:
    delta = 0.2  # 正常科研 + 正常训练 = 3.2x
elif s_idx == 2 and e_idx == 2:
    delta = 0.5  # 双高 = 3.5x
elif s_idx == 2 or e_idx == 2:
    delta = 0.3  # 单高 = 3.3x
elif s_idx == 0 and e_idx == 0:
    delta = -0.3 # 双低 = 2.7x
else:
    delta = -0.1 # 单低 = 2.9x

targets = get_targets(USER_WEIGHT, delta)

# 侧边栏即时合成看板
st.sidebar.divider()
st.sidebar.metric("合成碳水系数", f"{targets['actual_coeff']:.1f}x", f"{delta:+.1f}x 对比基准")
st.sidebar.write(f"建议摄入：**{targets['c_target']:.1f}g**")

# --- 3. 饮食录入区 ---
st.title("🏋️‍♂️ Alpha-Tracker 决策中心")

# 分餐记录（选填）
with st.expander("📝 分餐明细记录", expanded=False):
    tabs = st.tabs(["🌅 早餐", "☀️ 午餐", "🌙 晚餐", "🍎 加餐"])
    meals = ["b", "l", "d", "s"]
    meal_data = {}
    for i, m in enumerate(meals):
        with tabs[i]:
            c1, c2, c3, c4 = st.columns(4)
            meal_data[f"{m}_k"] = c1.number_input(f"热量(kcal)", min_value=0.0, key=f"{m}_k")
            meal_data[f"{m}_c"] = c2.number_input(f"碳水(g)", min_value=0.0, key=f"{m}_c")
            meal_data[f"{m}_p"] = c3.number_input(f"蛋白(g)", min_value=0.0, key=f"{m}_p")
            meal_data[f"{m}_f"] = c4.number_input(f"脂肪(g)", min_value=0.0, key=f"{m}_f")

    if st.button("🔄 同步分餐至今日总量"):
        st.session_state.total_k = sum(meal_data[f"{m}_k"] for m in meals)
        st.session_state.total_c = sum(meal_data[f"{m}_c"] for m in meals)
        st.session_state.total_p = sum(meal_data[f"{m}_p"] for m in meals)
        st.session_state.total_f = sum(meal_data[f"{m}_f"] for m in meals)

# 核心总量记录
st.subheader("🏁 今日摄入总计 (保存依据)")
c1, c2, c3, c4 = st.columns(4)
total_k = c1.number_input("总热量(kcal)", min_value=0.0, key="total_k_input", value=st.session_state.get('total_k', 0.0))
total_c = c2.number_input("总碳水(g)", min_value=0.0, key="total_c_input", value=st.session_state.get('total_c', 0.0))
total_p = c3.number_input("总蛋白(g)", min_value=0.0, key="total_p_input", value=st.session_state.get('total_p', 0.0))
total_f = c4.number_input("总脂肪(g)", min_value=0.0, key="total_f_input", value=st.session_state.get('total_f', 0.0))

# --- 4. 实时看板 ---
st.divider()
rem_c = targets['c_target'] - total_c
rem_p = targets['p_target'] - total_p
rem_f = targets['f_max'] - total_f

m1, m2, m3 = st.columns(3)
m1.metric("碳水剩余 (g)", f"{rem_c:.1f}", delta=f"建议 {targets['c_target']:.0f}", delta_color="inverse")
m2.metric("蛋白剩余 (g)", f"{rem_p:.1f}", delta=f"目标 {targets['p_target']:.0f}")
m3.metric("脂肪剩余 (g)", f"{rem_f:.1f}", delta=f"上限 {targets['f_max']:.0f}", delta_color="inverse")

# 教练提示
if total_c > 0 or total_p > 0:
    if rem_c < 0: st.error(f"⚠️ 碳水已超支 {abs(rem_c):.1f}g！大脑和肌肉已饱和，请削减主食。")
    elif rem_c < 50: st.warning("💡 碳水余额不多，建议优先保证高质量蛋白。")
    else: st.success(f"✅ 能量空间充足，还可摄入约 {rem_c:.1f}g 碳水。")

# --- 5. 保存与历史 ---
if st.button("💾 存档今日数据"):
    new_data = {"日期": str(date.today()), "总热量": total_k, "碳水": total_c, "蛋白质": total_p, "脂肪": total_f, "碳水目标": targets['c_target'], "动态调整系数": f"{targets['actual_coeff']:.1f}x"}
    df_new = pd.DataFrame([new_data])
    df_new.to_csv('diet_log.csv', mode='a', index=False, header=not os.path.isfile('diet_log.csv'))
    st.success("数据已成功保存。")

st.divider()
st.header("📖 历史记录")
if os.path.isfile('diet_log.csv'):
    st.data_editor(pd.read_csv('diet_log.csv'), num_rows="dynamic", use_container_width=True)
