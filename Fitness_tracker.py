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

# 辅助函数：将 None 转换为 0.0
def nz(value):
    return value if value is not None else 0.0

# --- 2. 日期与状态决策 (系统核心) ---
st.sidebar.header("📅 日期与状态设定")
# 允许手动调整日期
target_date = st.sidebar.date_input("选择记录日期", date.today())
st.sidebar.divider()

train_options = {"休息/不训练": 0.0, "正常训练": 0.2, "高强度/冲重": 0.4}
study_options = {"轻松/不科研": -0.2, "正常科研": 0.0, "高压科研/冲刺": 0.3}

train_val = st.sidebar.select_slider("今日运动强度", options=list(train_options.keys()), value="休息/不训练")
study_val = st.sidebar.select_slider("今日科研状态", options=list(study_options.keys()), value="正常科研")

# 复合逻辑计算 Delta
delta = 0.0
if study_val == "正常科研" and train_val == "休息/不训练": delta = 0.0
elif study_val == "正常科研" and train_val == "正常训练": delta = 0.2
elif study_val == "高压科研/冲刺" and train_val == "高强度/冲重": delta = 0.5
elif study_val == "高压科研/冲刺" or train_val == "高强度/冲重": delta = 0.3
elif study_val == "轻松/不科研" and train_val == "休息/不训练": delta = -0.3
else: delta = -0.1

targets = get_targets(USER_WEIGHT, delta)
st.sidebar.metric("碳水系数", f"{targets['actual_coeff']:.1f}x", f"{delta:+.1f}x")

# --- 3. 饮食决策中心 ---
st.title(f"🏋️‍♂️ 饮食决策中心 ({target_date})")

# 分餐记录 (仅作为今日总量的辅助计算器)
with st.expander("📝 开启分餐计算器 (辅助加总，不直接存档)", expanded=False):
    tabs = st.tabs(["🌅 早餐", "☀️ 午餐", "🌙 晚餐", "🍎 加餐"])
    meals = ["b", "l", "d", "s"]
    meal_data = {}
    for i, m in enumerate(meals):
        with tabs[i]:
            c1, c2, c3, c4 = st.columns(4)
            meal_data[f"{m}_k"] = c1.number_input(f"热量", value=None, placeholder="0.0", key=f"{m}_k")
            meal_data[f"{m}_c"] = c2.number_input(f"碳水", value=None, placeholder="0.0", key=f"{m}_c")
            meal_data[f"{m}_p"] = c3.number_input(f"蛋白", value=None, placeholder="0.0", key=f"{m}_p")
            meal_data[f"{m}_f"] = c4.number_input(f"脂肪", value=None, placeholder="0.0", key=f"{m}_f")

    if st.button("🔢 汇总分餐数据至今日总量"):
        st.session_state.total_k = sum(nz(meal_data[f"{m}_k"]) for m in meals)
        st.session_state.total_c = sum(nz(meal_data[f"{m}_c"]) for m in meals)
        st.session_state.total_p = sum(nz(meal_data[f"{m}_p"]) for m in meals)
        st.session_state.total_f = sum(nz(meal_data[f"{m}_f"]) for m in meals)
        st.rerun()

# 核心总量记录 (必须项)
st.subheader("🏁 今日摄入总计")
c1, c2, c3, c4 = st.columns(4)
total_k = c1.number_input("总热量(kcal)", value=st.session_state.get('total_k', None), placeholder="必填", key="tk")
total_c = c2.number_input("总碳水(g)", value=st.session_state.get('total_c', None), placeholder="必填", key="tc")
total_p = c3.number_input("总蛋白(g)", value=st.session_state.get('total_p', None), placeholder="必填", key="tp")
total_f = c4.number_input("总脂肪(g)", value=st.session_state.get('total_f', None), placeholder="必填", key="tf")

# --- 4. 实时预算看板 ---
st.divider()
cur_c, cur_p, cur_f = nz(total_c), nz(total_p), nz(total_f)
rem_c, rem_p, rem_f = targets['c_target'] - cur_c, targets['p_target'] - cur_p, targets['f_max'] - cur_f

m1, m2, m3 = st.columns(3)
m1.metric("碳水剩余", f"{rem_c:.1f}g", delta=f"目标 {targets['c_target']:.0f}", delta_color="inverse")
m2.metric("蛋白剩余", f"{rem_p:.1f}g", delta=f"目标 {targets['p_target']:.0f}")
m3.metric("脂肪剩余", f"{rem_f:.1f}g", delta=f"上限 {targets['f_max']:.0f}", delta_color="inverse")

# --- 5. 存档与删除逻辑 ---
if st.button("💾 保存该日数据 (覆盖/新建)"):
    if cur_c == 0 and cur_p == 0:
        st.error("请先输入有效摄入量数据。")
    else:
        new_row = {
            "日期": str(target_date), "总热量": nz(total_k), "碳水": cur_c, 
            "蛋白质": cur_p, "脂肪": cur_f, "碳水目标": targets['c_target'], 
            "系数": f"{targets['actual_coeff']:.1f}x"
        }
        df_new = pd.DataFrame([new_row])
        
        if os.path.isfile('diet_log.csv'):
            old_df = pd.read_csv('diet_log.csv')
            # 如果日期已存在，先删除旧的那一行再添加
            old_df = old_df[old_df['日期'] != str(target_date)]
            final_df = pd.concat([old_df, df_new], ignore_index=True)
        else:
            final_df = df_new
            
        final_df.sort_values(by="日期", ascending=False, inplace=True)
        final_df.to_csv('diet_log.csv', index=False)
        st.success(f"【{target_date}】的数据已保存/更新！")
        # 清除当前 Session 缓存
        for key in ['total_k', 'total_c', 'total_p', 'total_f']:
            if key in st.session_state: del st.session_state[key]

# --- 6. 历史记录管理 (彻底删除版) ---
st.divider()
st.header("📖 历史记录管理")
if os.path.isfile('diet_log.csv'):
    history_df = pd.read_csv('diet_log.csv')
    st.write("💡 操作说明：直接修改数值，或选中左侧框按 Delete 键删除行，最后必须点击下方按钮生效。")
    
    # 获取编辑后的 Dataframe
    edited_df = st.data_editor(history_df, num_rows="dynamic", use_container_width=True, key="history_editor")
    
    if st.button("🔥 同步修改并彻底保存"):
        # 将编辑后的结果直接覆盖原 CSV 文件
        edited_df.to_csv('diet_log.csv', index=False)
        st.success("云端 CSV 文件已重写，数据已彻底更新！")
        st.rerun()
else:
    st.info("尚无记录，开始你的第一次存档吧。")
