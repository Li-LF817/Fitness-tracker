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

# --- 2. 侧边栏：状态决策矩阵 ---
st.sidebar.header("📊 状态输入")

train_options = {"休息/不训练": "保持基准 (0.0)", "正常训练": "需求上调 (+0.2)", "高强度/冲重": "需求激增 (+0.3~0.5)"}
study_options = {"轻松/不科研": "消耗降低 (-0.1~0.3)", "正常科研": "保持基准 (0.0)", "高压科研/冲刺": "需求上调 (+0.3~0.5)"}

train_val = st.sidebar.select_slider("今日运动强度", options=list(train_options.keys()), value="休息/不训练")
st.sidebar.caption(f"💡 预期：{train_options[train_val]}")

study_val = st.sidebar.select_slider("今日科研状态", options=list(study_options.keys()), value="正常科研")
st.sidebar.caption(f"💡 预期：{study_options[study_val]}")

# 核心复合逻辑
delta = 0.0
e_idx, s_idx = list(train_options.keys()).index(train_val), list(study_options.keys()).index(study_val)

if s_idx == 1 and e_idx == 0: delta = 0.0
elif s_idx == 1 and e_idx == 1: delta = 0.2
elif s_idx == 2 and e_idx == 2: delta = 0.5
elif s_idx == 2 or e_idx == 2: delta = 0.3
elif s_idx == 0 and e_idx == 0: delta = -0.3
else: delta = -0.1

targets = get_targets(USER_WEIGHT, delta)
st.sidebar.divider()
st.sidebar.metric("合成碳水系数", f"{targets['actual_coeff']:.1f}x", f"{delta:+.1f}x")

# --- 3. 饮食录入区 ---
st.title("🏋️‍♂️ Alpha-Tracker 摄入监测系统")

# 辅助函数：将 None 转换为 0.0 以便计算
def nz(value):
    return value if value is not None else 0.0

# 分餐记录（选填）
with st.expander("📝 分餐明细记录", expanded=False):
    tabs = st.tabs(["🌅 早餐", "☀️ 午餐", "🌙 晚餐", "🍎 加餐"])
    meals = ["b", "l", "d", "s"]
    meal_data = {}
    for i, m in enumerate(meals):
        with tabs[i]:
            c1, c2, c3, c4 = st.columns(4)
            # 使用 value=None 和 placeholder 实现虚化效果
            meal_data[f"{m}_k"] = c1.number_input(f"热量(kcal)", value=None, placeholder="0.00", key=f"{m}_k")
            meal_data[f"{m}_c"] = c2.number_input(f"碳水(g)", value=None, placeholder="0.00", key=f"{m}_c")
            meal_data[f"{m}_p"] = c3.number_input(f"蛋白(g)", value=None, placeholder="0.00", key=f"{m}_p")
            meal_data[f"{m}_f"] = c4.number_input(f"脂肪(g)", value=None, placeholder="0.00", key=f"{m}_f")

    if st.button("同步分餐至下方总量"):
        st.session_state.total_k = sum(nz(meal_data[f"{m}_k"]) for m in meals)
        st.session_state.total_c = sum(nz(meal_data[f"{m}_c"]) for m in meals)
        st.session_state.total_p = sum(nz(meal_data[f"{m}_p"]) for m in meals)
        st.session_state.total_f = sum(nz(meal_data[f"{m}_f"]) for m in meals)
        st.rerun()

# 核心总量记录
st.subheader("今日摄入总计")
c1, c2, c3, c4 = st.columns(4)

# 总量框也支持这种逻辑：如果有同步值则显示同步值，否则显示虚化占位符
total_k = c1.number_input("总热量(kcal)", value=st.session_state.get('total_k', None), placeholder="0.00", key="tk")
total_c = c2.number_input("总碳水(g)", value=st.session_state.get('total_c', None), placeholder="0.00", key="tc")
total_p = c3.number_input("总蛋白(g)", value=st.session_state.get('total_p', None), placeholder="0.00", key="tp")
total_f = c4.number_input("总脂肪(g)", value=st.session_state.get('total_f', None), placeholder="0.00", key="tf")

# --- 4. 实时看板 ---
st.divider()
# 计算时使用 nz() 确保安全性
cur_c, cur_p, cur_f = nz(total_c), nz(total_p), nz(total_f)
rem_c, rem_p, rem_f = targets['c_target'] - cur_c, targets['p_target'] - cur_p, targets['f_max'] - cur_f

m1, m2, m3 = st.columns(3)
m1.metric("碳水剩余 (g)", f"{rem_c:.1f}", delta=f"建议 {targets['c_target']:.0f}", delta_color="inverse")
m2.metric("蛋白剩余 (g)", f"{rem_p:.1f}", delta=f"目标 {targets['p_target']:.0f}")
m3.metric("脂肪剩余 (g)", f"{rem_f:.1f}", delta=f"上限 {targets['f_max']:.0f}", delta_color="inverse")

# 教练提示
if cur_c > 0 or cur_p > 0:
    if rem_c < 0: st.error(f"⚠️ 碳水已超支 {abs(rem_c):.1f}g！")
    elif rem_c < 50: st.warning("💡 碳水余额有限，注意摄入质量。")
    else: st.success(f"✅ 能量空间充足。")

# --- 5. 保存与历史 ---
if st.button("💾 存档今日数据"):
    if cur_c == 0 and cur_p == 0:
        st.error("请输入有效数据后再保存。")
    else:
        new_data = {"日期": str(date.today()), "总热量": nz(total_k), "碳水": cur_c, "蛋白质": cur_p, "脂肪": cur_f, "碳水目标": targets['c_target'], "动态调整系数": f"{targets['actual_coeff']:.1f}x"}
        df_new = pd.DataFrame([new_data])
        df_new.to_csv('diet_log.csv', mode='a', index=False, header=not os.path.isfile('diet_log.csv'))
        st.success("数据已成功存档。")
        # 清空 session 状态以便明天记录
        for key in ['total_k', 'total_c', 'total_p', 'total_f']:
            if key in st.session_state: del st.session_state[key]

st.divider()
st.header("📖 历史记录")
if os.path.isfile('diet_log.csv'):
    st.data_editor(pd.read_csv('diet_log.csv'), num_rows="dynamic", use_container_width=True)
