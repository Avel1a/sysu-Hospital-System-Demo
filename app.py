import streamlit as st
import mysql.connector
import pandas as pd
import time

# --- 1. 数据库连接配置 (改成你自己的) ---
db_config = {
    'host': 'localhost',
    'user': 'root',
    'port': 3307,
    'password': 'zjy060115',  # 记得改这里！！
    'database': 'hospital_db'
}


def get_connection():
    return mysql.connector.connect(**db_config)


def run_query(query, params=None):
    conn = get_connection()
    cursor = conn.cursor()
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
        conn.commit()
    conn.close()
    return cursor


def get_data(query):
    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df


# --- 2. 界面布局 ---
st.set_page_config(page_title="社区医院门诊管理系统", layout="wide")
st.title("🏥 社区医院门诊管理系统")

# 侧边栏：角色切换
role = st.sidebar.radio("当前操作角色", ["患者 (挂号)", "医生 (接诊)", "收费处 (缴费/管理)"])

# --- 3. 角色功能实现 ---

# === 角色 A: 患者 (对应 PPT 的“网上预约”需求) ===
if role == "患者 (挂号)":
    st.header("📝 患者预约挂号")

    with st.form("booking_form"):
        p_name = st.text_input("请输入您的姓名")
        # 从数据库动态获取医生列表
        doc_df = get_data("SELECT name, department FROM doctors")
        # 拼接成 "张三 - 内科" 格式供选择
        doc_choice = st.selectbox("选择医生", doc_df['name'] + " - " + doc_df['department'])

        submitted = st.form_submit_button("确认挂号")
        if submitted and p_name:
            doc_name = doc_choice.split(" - ")[0]
            # 写入数据库
            run_query("INSERT INTO appointments (patient_name, doctor_name) VALUES (%s, %s)", (p_name, doc_name))
            st.success(f"挂号成功！请前往 {doc_choice} 候诊。")

if st.sidebar.button("⚠️ 重置系统数据 (测试用)"):
    run_query("TRUNCATE TABLE appointments")
    st.success("数据已重置")

# === 角色 B: 医生 (对应 PPT 的“就诊”需求) ===
elif role == "医生 (接诊)":
    st.header("👨‍⚕️ 医生接诊台")

    # 展示当前挂这个医生的号
    st.subheader("当前候诊列表")
    # 这里为了演示简单，展示所有“已预约”的单子
    pending_df = get_data("SELECT * FROM appointments WHERE status='已预约'")
    st.dataframe(pending_df)

    if not pending_df.empty:
        # 医生操作区
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            app_id = st.selectbox("选择就诊单号", pending_df['id'])
        with col2:
            cost = st.number_input("录入诊疗费用", min_value=0.0, step=10.0)

        if st.button("完成诊疗 (发送至收费处)"):
            run_query("UPDATE appointments SET status='待缴费', cost=%s WHERE id=%s", (cost, app_id))
            st.success("诊疗完成，已通知患者缴费！")
            time.sleep(1)
            st.rerun()  # 刷新页面

# === 角色 C: 收费处/管理员 (对应 PPT 的“缴费与统计”需求) ===
elif role == "收费处 (缴费/管理)":
    # === 仪表盘优化 ===
    st.header("📊 医院运营看板")
    col1, col2, col3 = st.columns(3)

    # 获取实时数据
    today_count = get_data("SELECT COUNT(*) as c FROM appointments WHERE DATE(create_time) = CURDATE()").iloc[0]['c']
    total_revenue = get_data("SELECT SUM(cost) as t FROM appointments WHERE status='已完成'").iloc[0]['t'] or 0
    busy_doc = get_data("SELECT doctor_name FROM appointments GROUP BY doctor_name ORDER BY COUNT(*) DESC LIMIT 1")
    busy_doc_name = busy_doc.iloc[0]['doctor_name'] if not busy_doc.empty else "暂无"

    col1.metric("今日接诊量", f"{today_count} 人", "+5%")
    col2.metric("总营收", f"¥ {total_revenue:,.2f}")
    col3.metric("今日值班之星", busy_doc_name)

    st.divider()  # 分割线
    # ... 原有的代码 ...
    st.header("💰 收费与管理中心")

    tab1, tab2 = st.tabs(["收费窗口", "数据报表"])

    with tab1:  # 收费功能
        unpaid_df = get_data("SELECT * FROM appointments WHERE status='待缴费'")
        if unpaid_df.empty:
            st.info("暂无待缴费项目")
        else:
            st.dataframe(unpaid_df)
            pay_id = st.selectbox("选择缴费单号", unpaid_df['id'])
            if st.button("确认收费"):
                run_query("UPDATE appointments SET status='已完成' WHERE id=%s", (pay_id,))
                st.balloons()  # 放个气球动画，演示效果拉满
                st.success("缴费成功！流程结束。")
                time.sleep(1)
                st.rerun()

    with tab2:  # 报表功能 (PPT 要求演示统计)
        st.subheader("科室就诊人数统计")
        # 一个复杂的聚合查询，体现数据库水平
        sql = """
        SELECT d.department, COUNT(a.id) as count 
        FROM appointments a 
        JOIN doctors d ON a.doctor_name = d.name 
        GROUP BY d.department
        """
        stat_df = get_data(sql)
        st.bar_chart(stat_df.set_index("department"))  # 自动画图

        st.subheader("今日流水")
        income = get_data("SELECT SUM(cost) as total FROM appointments WHERE status='已完成'")
        st.metric("总收入", f"¥ {income['total'].iloc[0] or 0}")