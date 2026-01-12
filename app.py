import streamlit as st
import sqlite3
import pandas as pd
import random
from datetime import datetime, timedelta


# ==========================================
# 0. 数据库初始化 & 升级
# ==========================================
def init_db():
    conn = sqlite3.connect('hospital.db')
    c = conn.cursor()

    # 1. 预约表
    c.execute('''CREATE TABLE IF NOT EXISTS Appointments
                 (id INTEGER PRIMARY KEY,
                  patient_name TEXT, dept_name TEXT, phone TEXT, 
                  expected_time TEXT, status TEXT)''')

    # 2. 就诊表
    c.execute('''CREATE TABLE IF NOT EXISTS Consultations
                 (id INTEGER PRIMARY KEY,
                  patient_name TEXT, gender TEXT, id_card TEXT, phone TEXT, 
                  dept_name TEXT, room_number TEXT, status TEXT, visit_time TEXT)''')

    # 3. 费用表
    c.execute('''CREATE TABLE IF NOT EXISTS Payments
                 (id INTEGER PRIMARY KEY,
                  consultation_id INTEGER,
                  total_amount REAL, insurance_amount REAL, self_pay_amount REAL,
                  payment_time TEXT)''')

    # 4. 【新增】员工表 (满足管理员需求①④⑤)
    # 包含：工号(id), 姓名, 职称, 科室, 诊室, 排班时间, 状态
    c.execute('''CREATE TABLE IF NOT EXISTS Staff
                 (id INTEGER PRIMARY KEY,
                  name TEXT, title TEXT, dept_name TEXT, 
                  room_number TEXT, schedule_time TEXT, 
                  phone TEXT, status TEXT)''')

    conn.commit()
    conn.close()


# ==========================================
# 工具函数：生成假数据 (演示神器)
# ==========================================
def generate_fake_data():
    conn = sqlite3.connect('hospital.db')
    c = conn.cursor()

    # 1. 清空旧数据 (防止重复点导致数据爆炸)
    c.execute("DELETE FROM Staff")
    c.execute("DELETE FROM Appointments")
    c.execute("DELETE FROM Consultations")
    c.execute("DELETE FROM Payments")

    # 2. 生成医生数据
    doctors = [
        ("王大神", "主任医师", "内科", "101诊室", "周一/周三 上午"),
        ("李圣手", "副主任医师", "外科", "202诊室", "周二/周四 全天"),
        ("张爱心", "主治医师", "儿科", "303诊室", "周一至周五 上午"),
        ("刘整齐", "医师", "口腔科", "401诊室", "周五 下午"),
        ("赵明亮", "主任医师", "眼科", "501诊室", "周三 全天")
    ]
    for doc in doctors:
        c.execute(
            "INSERT INTO Staff (name, title, dept_name, room_number, schedule_time, phone, status) VALUES (?, ?, ?, ?, ?, '13800138000', '在职')",
            doc)

    # 3. 生成一些历史就诊和收入数据 (为了让图表有东西显示)
    depts = ["内科", "外科", "儿科", "口腔科"]
    for i in range(20):
        dept = random.choice(depts)
        total = random.randint(50, 500)
        insurance = round(total * 0.4, 2)
        self_pay = total - insurance

        # 插入就诊记录
        c.execute(
            "INSERT INTO Consultations (patient_name, dept_name, status, visit_time) VALUES (?, ?, '已离院', datetime('now', '-1 day'))",
            (f"模拟患者{i}", dept))
        cid = c.lastrowid
        # 插入费用记录
        c.execute(
            "INSERT INTO Payments (consultation_id, total_amount, insurance_amount, self_pay_amount, payment_time) VALUES (?, ?, ?, ?, datetime('now', '-1 day'))",
            (cid, total, insurance, self_pay))

    conn.commit()
    conn.close()
    return "✅ 演示数据已生成！包含5位医生和20条流水记录。"
# ==========================================
# 工具函数：一键清空所有数据 (慎用！)
# ==========================================
def clear_all_data():
    conn = sqlite3.connect('hospital.db')
    c = conn.cursor()
    # 清空所有表的内容，但保留表结构
    c.execute("DELETE FROM Appointments")
    c.execute("DELETE FROM Consultations")
    c.execute("DELETE FROM Payments")
    c.execute("DELETE FROM Staff")
    conn.commit()
    conn.close()
    return "🗑️ 所有数据已清空！系统已重置为初始状态。"

# 初始化
init_db()

# ==========================================
# 界面主逻辑
# ==========================================
st.set_page_config(page_title="社区医院系统", layout="wide", page_icon="🏥")
st.title("🏥 社区医院门诊管理系统 (最终演示版)")

# 侧边栏
role = st.sidebar.selectbox("当前操作角色", ["患者", "前台", "管理员"])

# ---------------- 患者端 ----------------
if role == "患者":
    st.header("📋 患者自助服务")
    tab1, tab2 = st.tabs(["预约挂号", "我的状态"])
    with tab1:
        with st.form("appt_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("姓名")
            phone = c2.text_input("电话")
            # 动态从数据库读取科室列表
            conn = sqlite3.connect('hospital.db')
            df_staff = pd.read_sql("SELECT DISTINCT dept_name FROM Staff", conn)
            dept_list = df_staff['dept_name'].tolist() if not df_staff.empty else ["内科", "外科"]
            conn.close()

            dept = st.selectbox("选择科室", dept_list)
            time = st.time_input("预计到达时间")
            if st.form_submit_button("提交预约"):
                conn = sqlite3.connect('hospital.db')
                conn.execute(
                    "INSERT INTO Appointments (patient_name, dept_name, phone, expected_time, status) VALUES (?, ?, ?, ?, '待就诊')",
                    (name, dept, phone, str(time)))
                conn.commit()
                st.success("预约成功！")

# ---------------- 前台端 ----------------
elif role == "前台":
    st.header("💁 前台分诊与收费")
    task = st.radio("业务模式", ["预约核验 (转就诊)", "收费结算 (离院)"], horizontal=True)

    conn = sqlite3.connect('hospital.db')

    if task == "预约核验 (转就诊)":
        st.subheader("待核验预约")
        df = pd.read_sql("SELECT * FROM Appointments WHERE status='待就诊'", conn)
        for i, row in df.iterrows():
            with st.expander(f"{row['patient_name']} - {row['dept_name']} (预: {row['expected_time']})"):
                c1, c2 = st.columns(2)
                room = c1.text_input("分配诊室", value="101诊室", key=f"r{row['id']}")
                if st.button("核验通过", key=f"b{row['id']}"):
                    conn.execute(
                        "INSERT INTO Consultations (patient_name, dept_name, phone, room_number, status, visit_time) VALUES (?, ?, ?, ?, '就诊中', datetime('now'))",
                        (row['patient_name'], row['dept_name'], row['phone'], room))
                    conn.execute("UPDATE Appointments SET status='已完成' WHERE id=?", (row['id'],))
                    conn.commit()
                    st.rerun()

    elif task == "收费结算 (离院)":
        st.subheader("待缴费列表")
        df = pd.read_sql("SELECT * FROM Consultations WHERE status='就诊中'", conn)
        pat = st.selectbox("选择患者", df['patient_name'].tolist() if not df.empty else [])
        if pat:
            row = df[df['patient_name'] == pat].iloc[0]
            c1, c2, c3 = st.columns(3)
            total = c1.number_input("总费用", 100.0)
            insur = c2.number_input("医保支付", 0.0)
            self_p = total - insur
            c3.metric("自费应收", f"¥{self_p}")
            if st.button("确认收费并离院"):
                conn.execute(
                    "INSERT INTO Payments (consultation_id, total_amount, insurance_amount, self_pay_amount, payment_time) VALUES (?, ?, ?, ?, datetime('now'))",
                    (int(row['id']), total, insur, self_p))
                conn.execute("UPDATE Consultations SET status='已离院' WHERE id=?", (int(row['id']),))
                conn.commit()
                st.success("结算成功！")
                st.rerun()
    conn.close()

# ---------------- 管理员端 (本次重点升级) ----------------
# ---------------- 管理员端 ----------------
elif role == "管理员":
    st.header("🛡️ 医院管理后台")

    # 管理员侧边栏工具箱
    with st.sidebar:
        st.markdown("---")
        st.markdown("**🛠️ 调试工具**")

        # 按钮1: 生成数据
        if st.button("✨ 一键生成演示数据"):
            msg = generate_fake_data()
            st.toast(msg)
            st.rerun()

        # 按钮2: 清空数据 (加个分割线，搞成红色的提示)
        st.markdown("---")
        st.warning("⚠️ 危险操作区")
        if st.button("🔥 一键清空所有数据"):
            msg = clear_all_data()
            st.toast(msg, icon="🗑️")
            st.rerun()

    tab1, tab2, tab3 = st.tabs(["数据看板", "员工/排班管理", "全院查询"])

    conn = sqlite3.connect('hospital.db')

    # Tab 1: 统计图表 (需求②)
    with tab1:
        st.subheader("门诊收入统计")
        df_stat = pd.read_sql(
            "SELECT c.dept_name, SUM(p.total_amount) as 收入 FROM Consultations c JOIN Payments p ON c.id=p.consultation_id GROUP BY c.dept_name",
            conn)
        if not df_stat.empty:
            c1, c2 = st.columns([2, 1])
            c1.bar_chart(df_stat.set_index("dept_name"))
            c2.dataframe(df_stat)
        else:
            st.info("暂无数据，请点击左侧 sidebar 的“一键生成演示数据”按钮！")

    # Tab 2: 员工管理 (需求①④⑤)
    with tab2:
        st.subheader("添加/修改 医生排班")

        # A. 列表展示
        st.caption("当前在职员工列表：")
        df_staff = pd.read_sql("SELECT * FROM Staff", conn)
        st.dataframe(df_staff, use_container_width=True)

        st.divider()

        # B. 新增/修改表单
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 📝 录入/修改员工信息")
            with st.form("staff_form"):
                s_name = st.text_input("姓名 (必填)")
                s_dept = st.selectbox("所属科室", ["内科", "外科", "儿科", "口腔科", "眼科", "急诊"])
                s_title = st.selectbox("职称", ["主任医师", "副主任医师", "主治医师", "医师", "实习生"])
                s_room = st.text_input("诊室编号 (如: 201诊室)")
                s_time = st.text_input("排班时间 (如: 周一上午)")
                s_phone = st.text_input("联系电话")

                submitted = st.form_submit_button("保存员工信息")
                if submitted and s_name:
                    # 简单处理：如果名字存在就更新，不存在就插入 (Upsert逻辑太复杂，这里用Insert演示)
                    conn.execute(
                        "INSERT INTO Staff (name, title, dept_name, room_number, schedule_time, phone, status) VALUES (?, ?, ?, ?, ?, ?, '在职')",
                        (s_name, s_title, s_dept, s_room, s_time, s_phone))
                    conn.commit()
                    st.success(f"员工 {s_name} 信息已保存！")
                    st.rerun()

    # Tab 3: 全院查询 (需求③④)
    with tab3:
        st.subheader("🔍 综合信息查询")
        search_term = st.text_input("输入姓名/电话/身份证号进行搜索:")
        if search_term:
            st.write("🔎 患者/就诊记录匹配结果：")
            sql = f"SELECT * FROM Consultations WHERE patient_name LIKE '%{search_term}%' OR phone LIKE '%{search_term}%'"
            st.dataframe(pd.read_sql(sql, conn))

    conn.close()