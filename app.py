import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime


# ==========================================
# 0. 数据库初始化 (对应 PPT 里的字段要求)
# ==========================================
def init_db():
    conn = sqlite3.connect('hospital.db')
    c = conn.cursor()

    # 1. 预约表：加了 expected_time
    c.execute('''CREATE TABLE IF NOT EXISTS Appointments
                 (id INTEGER PRIMARY KEY,
                  patient_name TEXT,
                  dept_name TEXT,
                  phone TEXT,
                  expected_time TEXT,
                  status TEXT)''')

    # 2. 就诊表：加了 身份证、性别、诊室号
    c.execute('''CREATE TABLE IF NOT EXISTS Consultations
                 (id INTEGER PRIMARY KEY,
                  patient_name TEXT,
                  gender TEXT,
                  id_card TEXT,
                  phone TEXT,
                  dept_name TEXT,
                  room_number TEXT,
                  status TEXT,
                  visit_time TEXT)''')

    # 3. 费用表：加了 医保/自费 拆分
    c.execute('''CREATE TABLE IF NOT EXISTS Payments
                 (id INTEGER PRIMARY KEY,
                  consultation_id INTEGER,
                  total_amount REAL,
                  insurance_amount REAL,
                  self_pay_amount REAL,
                  payment_time TEXT)''')
    conn.commit()
    conn.close()


# 初始化数据库
init_db()

# ==========================================
# 1. 界面布局与导航
# ==========================================
st.set_page_config(page_title="社区医院门诊管理系统", layout="wide")
st.title("🏥 社区医院门诊管理系统")

# 侧边栏选择角色
role = st.sidebar.selectbox(
    "请选择您的角色",
    ["患者 (Patient)", "前台 (Front Desk)", "管理员 (Manager)"]
)

# ==========================================
# 2. 患者端逻辑 (对应 PPT 患者需求)
# ==========================================
if role == "患者 (Patient)":
    st.header("📋 患者服务中心")
    tab1, tab2 = st.tabs(["网上预约", "我的信息"])

    with tab1:
        st.subheader("预约挂号 (需求①)")
        with st.form("appointment_form"):
            col1, col2 = st.columns(2)
            name = col1.text_input("姓名")
            phone = col2.text_input("联系电话")
            dept = st.selectbox("就诊科室", ["内科", "外科", "儿科", "口腔科"])

            # 【PPT重点】预计到达时间
            arrival_time = st.time_input("预计到达时间")

            submitted = st.form_submit_button("提交预约")
            if submitted:
                conn = sqlite3.connect('hospital.db')
                c = conn.cursor()
                c.execute(
                    "INSERT INTO Appointments (patient_name, dept_name, phone, expected_time, status) VALUES (?, ?, ?, ?, '待就诊')",
                    (name, dept, phone, str(arrival_time)))
                conn.commit()
                conn.close()
                st.success(f"预约成功！请于 {arrival_time} 前往医院核验。")

# ==========================================
# 3. 前台端逻辑 (对应 PPT 前台需求)
# ==========================================
elif role == "前台 (Front Desk)":
    st.header("💁 前台工作台")
    task = st.radio("业务类型", ["预约核验/分诊", "收费结算"])

    conn = sqlite3.connect('hospital.db')

    # --- 业务A: 预约核验 (需求②) ---
    if task == "预约核验/分诊":
        st.subheader("待核验预约列表")
        # 查出所有待就诊的预约
        df_appt = pd.read_sql("SELECT * FROM Appointments WHERE status='待就诊'", conn)

        if not df_appt.empty:
            for index, row in df_appt.iterrows():
                with st.expander(f"患者：{row['patient_name']} (预约时间: {row['expected_time']})"):
                    col1, col2 = st.columns(2)
                    # 补全 PPT 要求的核验信息
                    id_card = col1.text_input(f"补全身份证号 ({row['id']})", key=f"id_{row['id']}")
                    gender = col2.selectbox(f"补全性别 ({row['id']})", ["男", "女"], key=f"gen_{row['id']}")
                    room_num = st.text_input(f"分配诊室号 ({row['id']})", value="301诊室", key=f"room_{row['id']}")

                    if st.button(f"核验并转入就诊 ({row['id']})", key=f"btn_{row['id']}"):
                        c = conn.cursor()
                        # 1. 插入到就诊表
                        c.execute(
                            "INSERT INTO Consultations (patient_name, gender, id_card, phone, dept_name, room_number, status, visit_time) VALUES (?, ?, ?, ?, ?, ?, '就诊中', datetime('now'))",
                            (row['patient_name'], gender, id_card, row['phone'], row['dept_name'], room_num))
                        # 2. 标记预约已完成
                        c.execute("UPDATE Appointments SET status='已完成' WHERE id=?", (row['id'],))
                        conn.commit()
                        st.success("核验成功！已转入就诊信息表。")
                        st.rerun()  # 刷新页面
        else:
            st.info("当前没有待核验的预约。")

    # --- 业务B: 收费结算 (需求③) ---
    elif task == "收费结算":
        st.subheader("待缴费患者")
        # 查出所有“就诊中”的患者
        df_consult = pd.read_sql("SELECT * FROM Consultations WHERE status='就诊中'", conn)

        patient_list = df_consult['patient_name'].tolist() if not df_consult.empty else []
        selected_patient = st.selectbox("选择缴费患者", patient_list)

        if selected_patient:
            # 获取该患者当前就诊记录ID
            curr_row = df_consult[df_consult['patient_name'] == selected_patient].iloc[0]
            cid = int(curr_row['id'])

            st.write(f"正在为 **{selected_patient}** ({curr_row['dept_name']}) 办理离院结算")

            c1, c2, c3 = st.columns(3)
            total = c1.number_input("本次就诊总费用", value=100.0, step=10.0)
            insurance = c2.number_input("医保报销金额", value=30.0, step=10.0)
            # 自动计算自费
            self_pay = total - insurance
            c3.metric("自费金额 (自动计算)", f"¥ {self_pay}")

            if st.button("结算并离院"):
                c = conn.cursor()
                # 1. 插入费用表
                c.execute(
                    "INSERT INTO Payments (consultation_id, total_amount, insurance_amount, self_pay_amount, payment_time) VALUES (?, ?, ?, ?, datetime('now'))",
                    (cid, total, insurance, self_pay))
                # 2. 修改状态为“已离院”
                c.execute("UPDATE Consultations SET status='已离院' WHERE id=?", (cid,))
                conn.commit()
                st.success("结算完成！患者状态已更新为“已离院”。")
                st.rerun()

    conn.close()

# ==========================================
# 4. 管理员端逻辑 (对应 PPT 管理员需求)
# ==========================================
elif role == "管理员 (Manager)":
    st.header("📊 医院运营数据")

    conn = sqlite3.connect('hospital.db')

    # 需求②：按科室统计收入与人次
    st.subheader("门诊收入统计 (需求②)")

    sql = '''
    SELECT 
        c.dept_name as 科室,
        COUNT(c.id) as 就诊人次,
        SUM(p.total_amount) as 总收入
    FROM Consultations c
    JOIN Payments p ON c.id = p.consultation_id
    GROUP BY c.dept_name
    '''
    df_stats = pd.read_sql(sql, conn)

    if not df_stats.empty:
        st.dataframe(df_stats, use_container_width=True)
        # 画个简单的图表
        st.bar_chart(df_stats.set_index("科室")["总收入"])
    else:
        st.info("暂无财务数据，请先去前台进行收费结算操作。")

    conn.close()