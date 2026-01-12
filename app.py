import streamlit as st
import sqlite3
import pandas as pd
import random
import os
from datetime import datetime


# ==========================================
# 1. 数据库初始化 (优先读取 schema.sql)
# ==========================================
def init_db():
    conn = sqlite3.connect('hospital.db')
    c = conn.cursor()

    script_file = 'schema.sql'

    # 检查是否存在队友写的 SQL 文件
    if os.path.exists(script_file):
        try:
            with open(script_file, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            c.executescript(sql_script)
            # print("✅ 已加载 schema.sql (含触发器)")
        except Exception as e:
            st.error(f"❌ 加载 SQL 脚本失败: {e}")
    else:
        # 【备用方案】如果没找到文件，为了防止程序报错，先用 Python 建个空表
        # 但这样就没有触发器功能了，状态不会自动变
        st.warning("⚠️ 未找到 schema.sql，正在使用备用初始化模式（无触发器功能）")
        c.execute(
            '''CREATE TABLE IF NOT EXISTS Appointments (id INTEGER PRIMARY KEY, patient_name TEXT, dept_name TEXT, phone TEXT, expected_time TEXT, status TEXT)''')
        c.execute(
            '''CREATE TABLE IF NOT EXISTS Consultations (id INTEGER PRIMARY KEY, patient_name TEXT, gender TEXT, id_card TEXT, phone TEXT, dept_name TEXT, room_number TEXT, status TEXT, visit_time TEXT)''')
        c.execute(
            '''CREATE TABLE IF NOT EXISTS Payments (id INTEGER PRIMARY KEY, consultation_id INTEGER, total_amount REAL, insurance_amount REAL, self_pay_amount REAL, payment_time TEXT)''')
        c.execute(
            '''CREATE TABLE IF NOT EXISTS Staff (id INTEGER PRIMARY KEY, name TEXT, title TEXT, dept_name TEXT, room_number TEXT, schedule_time TEXT, phone TEXT, status TEXT)''')

    conn.commit()
    conn.close()


# ==========================================
# 2. 调试工具：生成与清空数据
# ==========================================
def generate_fake_data():
    conn = sqlite3.connect('hospital.db')
    c = conn.cursor()

    # 先清空，避免重复叠加
    c.execute("DELETE FROM Staff");
    c.execute("DELETE FROM Appointments")
    c.execute("DELETE FROM Consultations");
    c.execute("DELETE FROM Payments")

    # 1. 生成医生
    doctors = [
        ("王大神", "主任医师", "内科", "101诊室", "周一/三", "13800001"),
        ("李圣手", "副主任", "外科", "202诊室", "周二/四", "13800002"),
        ("张爱心", "主治医师", "儿科", "303诊室", "周一至五", "13800003"),
        ("刘整齐", "医师", "口腔科", "401诊室", "周五", "13800004")
    ]
    for doc in doctors:
        c.execute(
            "INSERT INTO Staff (name, title, dept_name, room_number, schedule_time, phone, status) VALUES (?,?,?,?,?,?,'在职')",
            doc)

    # 2. 生成历史流水
    depts = ["内科", "外科", "儿科", "口腔科"]
    for i in range(15):
        dept = random.choice(depts)
        total = random.randint(50, 600)
        c.execute(
            "INSERT INTO Consultations (patient_name, dept_name, status, visit_time) VALUES (?, ?, '已离院', datetime('now','-1 day'))",
            (f"模拟患者{i}", dept))
        cid = c.lastrowid
        c.execute(
            "INSERT INTO Payments (consultation_id, total_amount, insurance_amount, self_pay_amount, payment_time) VALUES (?, ?, ?, ?, datetime('now','-1 day'))",
            (cid, total, total * 0.3, total * 0.7))

    # 3. 生成几个待核验的预约
    c.execute(
        "INSERT INTO Appointments (patient_name, dept_name, phone, expected_time, status) VALUES ('张三待诊', '内科', '1390000', '09:00', '待就诊')")
    c.execute(
        "INSERT INTO Appointments (patient_name, dept_name, phone, expected_time, status) VALUES ('李四待诊', '外科', '1390001', '10:30', '待就诊')")

    conn.commit();
    conn.close()
    return "✅ 演示数据生成完毕！"


def clear_all_data():
    conn = sqlite3.connect('hospital.db')
    c = conn.cursor()
    tables = ["Appointments", "Consultations", "Payments", "Staff"]
    for t in tables:
        c.execute(f"DELETE FROM {t}")
    conn.commit();
    conn.close()
    return "🗑️ 所有数据已清空！"


# 初始化运行
init_db()

# ==========================================
# 3. 界面逻辑
# ==========================================
st.set_page_config(page_title="社区医院系统", layout="wide", page_icon="🏥")
st.title("🏥 社区医院门诊管理系统 (协同开发版)")

role = st.sidebar.selectbox("当前操作角色", ["患者", "前台", "管理员"])

# --- 患者端 ---
if role == "患者":
    st.header("📋 患者自助服务")
    with st.form("appt"):
        c1, c2 = st.columns(2)
        name = c1.text_input("姓名")
        phone = c2.text_input("电话")
        conn = sqlite3.connect('hospital.db')
        dept_list = [r[0] for r in conn.execute("SELECT DISTINCT dept_name FROM Staff")]
        conn.close()
        dept = st.selectbox("科室", dept_list if dept_list else ["内科", "外科"])
        time = st.time_input("预计到达时间")
        if st.form_submit_button("提交预约"):
            conn = sqlite3.connect('hospital.db')
            conn.execute(
                "INSERT INTO Appointments (patient_name, dept_name, phone, expected_time, status) VALUES (?,?,?,?,'待就诊')",
                (name, dept, phone, str(time)))
            conn.commit();
            conn.close()
            st.success("预约成功！请按时到院核验。")

# --- 前台端 ---
elif role == "前台":
    st.header("💁 前台分诊与收费")
    tab1, tab2 = st.tabs(["预约核验", "收费结算"])

    conn = sqlite3.connect('hospital.db')

    with tab1:
        # 需求②：核验并转入就诊
        df = pd.read_sql("SELECT * FROM Appointments WHERE status='待就诊'", conn)
        for i, row in df.iterrows():
            with st.expander(f"待核验：{row['patient_name']} ({row['dept_name']})"):
                c1, c2 = st.columns(2)
                room = c1.text_input("分配诊室", "101诊室", key=f"r{row['id']}")
                if st.button("核验通过", key=f"b{row['id']}"):
                    # 插入就诊表
                    conn.execute(
                        "INSERT INTO Consultations (patient_name, dept_name, phone, room_number, status, visit_time) VALUES (?,?,?,?,'就诊中', datetime('now'))",
                        (row['patient_name'], row['dept_name'], row['phone'], room))
                    # 更新预约表
                    conn.execute("UPDATE Appointments SET status='已完成' WHERE id=?", (row['id'],))
                    conn.commit()
                    st.rerun()

    with tab2:
        # 需求③：收费 (触发器自动改状态)
        st.info("💡 提示：收费后，数据库触发器将自动把患者状态更新为 [已离院]")
        df = pd.read_sql("SELECT * FROM Consultations WHERE status='就诊中'", conn)
        pat = st.selectbox("选择缴费患者", df['patient_name'].tolist() if not df.empty else [])

        if pat:
            row = df[df['patient_name'] == pat].iloc[0]
            c1, c2, c3 = st.columns(3)
            total = c1.number_input("总费用", 100.0)
            insur = c2.number_input("医保支付", 0.0)
            self_p = total - insur
            c3.metric("自费应收", f"¥{self_p}")

            if st.button("确认收费"):
                # 【关键】Python 只负责插入 Payment，不更新 Consultations
                conn.execute(
                    "INSERT INTO Payments (consultation_id, total_amount, insurance_amount, self_pay_amount, payment_time) VALUES (?,?,?,?, datetime('now'))",
                    (int(row['id']), total, insur, self_p))
                conn.commit()
                st.success(f"收费成功！触发器已自动处理 {pat} 的离院状态。")
                st.rerun()
    conn.close()

# --- 管理员端 ---
elif role == "管理员":
    st.header("🛡️ 医院管理后台")

    # 侧边栏工具
    with st.sidebar:
        st.markdown("---")
        st.caption("🔧 调试工具箱")
        if st.button("✨ 生成演示数据"):
            st.toast(generate_fake_data())
            st.rerun()
        if st.button("🔥 清空所有数据"):
            st.toast(clear_all_data(), icon="🗑️")
            st.rerun()

    t1, t2 = st.tabs(["数据看板", "员工管理"])
    conn = sqlite3.connect('hospital.db')

    with t1:
        # 需求②：统计
        df = pd.read_sql(
            "SELECT c.dept_name as 科室, SUM(p.total_amount) as 收入 FROM Consultations c JOIN Payments p ON c.id=p.consultation_id GROUP BY c.dept_name",
            conn)
        if not df.empty:
            st.bar_chart(df.set_index("科室"))
        else:
            st.info("暂无数据，请使用左侧工具生成数据。")

    with t2:
        # 需求①④⑤：员工管理
        st.dataframe(pd.read_sql("SELECT * FROM Staff", conn), use_container_width=True)
        with st.form("add_staff"):
            c1, c2 = st.columns(2)
            name = c1.text_input("姓名")
            dept = c2.selectbox("科室", ["内科", "外科", "儿科", "口腔科"])
            title = c1.selectbox("职称", ["主任医师", "医师", "护士"])
            room = c2.text_input("诊室")
            if st.form_submit_button("添加员工"):
                conn.execute("INSERT INTO Staff (name, title, dept_name, room_number, status) VALUES (?,?,?,?,'在职')",
                             (name, title, dept, room))
                conn.commit()
                st.rerun()
    conn.close()