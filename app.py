import streamlit as st
import sqlite3
import pandas as pd
import random
from datetime import datetime


# ==========================================
# 1. 数据库初始化 (严格模式)
# ==========================================
def init_db():
    conn = sqlite3.connect('hospital.db')
    c = conn.cursor()

    script_file = 'schema.sql'

    try:
        with open(script_file, 'r', encoding='utf-8') as f:
            sql_script = f.read()

        c.executescript(sql_script)

    except FileNotFoundError:
        st.error(f"❌ 找不到 {script_file}！请把 SQL 代码填进去！")
        st.stop()

    conn.commit()
    conn.close()


# ==========================================
# 2. 调试工具：生成与清空数据
# ==========================================
def generate_fake_data():
    conn = sqlite3.connect('hospital.db')
    c = conn.cursor()

    # 清空旧数据
    tables = ["Staff", "Appointments", "Consultations", "Payments"]
    for t in tables:
        c.execute(f"DELETE FROM {t}")

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
        # 插入已离院的记录
        c.execute(
            "INSERT INTO Consultations (patient_name, dept_name, status, visit_time) VALUES (?, ?, '已离院', datetime('now','-1 day'))",
            (f"模拟患者{i}", dept))
        cid = c.lastrowid
        # 插入费用
        c.execute(
            "INSERT INTO Payments (consultation_id, total_amount, insurance_amount, self_pay_amount, payment_time) VALUES (?, ?, ?, ?, datetime('now','-1 day'))",
            (cid, total, total * 0.3, total * 0.7))

    # 3. 生成待核验预约
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
    # 只清空数据，不删表结构
    tables = ["Appointments", "Consultations", "Payments", "Staff"]
    for t in tables:
        c.execute(f"DELETE FROM {t}")
    conn.commit();
    conn.close()
    return "🗑️ 所有数据已清空！"


# 程序入口：初始化数据库
init_db()

# ==========================================
# 3. 界面逻辑
# ==========================================
st.set_page_config(page_title="社区医院系统", layout="wide", page_icon="🏥")
st.title("🏥 社区医院门诊管理系统")

role = st.sidebar.selectbox("当前操作角色", ["患者", "前台", "管理员"])

# --- A. 患者端 ---
if role == "患者":
    st.header("📋 患者自助服务")
    # 增加了一个 Tab：我的状态
    tab1, tab2 = st.tabs(["预约挂号", "我的就诊状态"])

    conn = sqlite3.connect('hospital.db')

    with tab1:
        with st.form("appt"):
            c1, c2 = st.columns(2)
            name = c1.text_input("姓名")
            phone = c2.text_input("电话")

            # 读取科室
            try:
                dept_list = [r[0] for r in conn.execute("SELECT DISTINCT dept_name FROM Staff")]
            except:
                dept_list = ["内科", "外科"]

            dept = st.selectbox("科室", dept_list if dept_list else ["内科", "外科"])
            time = st.time_input("预计到达时间")

            if st.form_submit_button("提交预约"):
                conn.execute(
                    "INSERT INTO Appointments (patient_name, dept_name, phone, expected_time, status) VALUES (?,?,?,?,'待就诊')",
                    (name, dept, phone, str(time)))
                conn.commit()
                st.success("预约成功！请按时到院核验。")

    with tab2:
        st.subheader("🔍 查询我的就诊进度")
        my_phone = st.text_input("请输入预留电话查询:", max_chars=11)
        if my_phone:
            # 1. 先查是不是还在预约里
            df_appt = pd.read_sql(
                f"SELECT patient_name, dept_name, status, expected_time FROM Appointments WHERE phone='{my_phone}' AND status='待就诊'",
                conn)
            # 2. 再查是不是已经进系统了
            df_cons = pd.read_sql(
                f"SELECT patient_name, dept_name, room_number, status FROM Consultations WHERE phone='{my_phone}' ORDER BY id DESC",
                conn)

            if not df_appt.empty:
                st.info(f"您好，{df_appt.iloc[0]['patient_name']}！")
                st.warning(f"当前状态：【{df_appt.iloc[0]['status']}】\n\n请前往前台核验身份。")
            elif not df_cons.empty:
                row = df_cons.iloc[0]
                st.info(f"您好，{row['patient_name']}！")
                if row['status'] == '就诊中':
                    st.success(f"当前状态：【{row['status']}】\n\n请前往 **{row['room_number']}** 就诊。")
                else:
                    st.balloons()
                    st.success(f"当前状态：【{row['status']}】\n\n缴费已完成，祝您早日康复！")
            else:
                st.error("未找到相关记录，请检查电话是否输入正确。")
    conn.close()

# --- B. 前台端 ---
elif role == "前台":
    st.header("💁 前台分诊与收费")

    tab1, tab2, tab3 = st.tabs(["预约核验", "收费结算", "患者信息查询"])

    conn = sqlite3.connect('hospital.db')

    with tab1:
        df = pd.read_sql("SELECT * FROM Appointments WHERE status='待就诊'", conn)
        if df.empty:
            st.info("暂无待核验预约")
        for i, row in df.iterrows():
            with st.expander(f"待核验：{row['patient_name']} ({row['dept_name']})"):
                c1, c2 = st.columns(2)
                fake_id = f"1101011990{random.randint(10000000, 99999999)}"
                id_card = c1.text_input(f"身份证号", value=fake_id, key=f"id_{row['id']}")
                gender = c2.selectbox(f"性别", ["男", "女"], key=f"gen_{row['id']}")
                room = st.text_input("分配诊室", "101诊室", key=f"r{row['id']}")
                if st.button("核验通过", key=f"b{row['id']}"):
                    conn.execute(
                        "INSERT INTO Consultations (patient_name, gender, id_card, dept_name, phone, room_number, status, visit_time) VALUES (?,?,?,?,?,?,'就诊中', datetime('now'))",
                        (row['patient_name'], gender, id_card, row['dept_name'], row['phone'], room))
                    conn.execute("UPDATE Appointments SET status='已完成' WHERE id=?", (row['id'],))
                    conn.commit();
                    st.rerun()

    with tab2:

        st.info("💡 提示：收费后触发器将自动更新离院状态")
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
                conn.execute(
                    "INSERT INTO Payments (consultation_id, total_amount, insurance_amount, self_pay_amount, payment_time) VALUES (?,?,?,?, datetime('now'))",
                    (int(row['id']), total, insur, self_p))
                conn.commit();
                st.success("收费成功！");
                st.rerun()

    with tab3:

        st.subheader("🔍 全院患者状态一览表")
        search_term = st.text_input("输入姓名或电话进行全局搜索:")

        if search_term:
            # 查预约中的
            sql_appt = f"SELECT patient_name as 姓名, dept_name as 科室, '尚未分配' as 诊室号, status as 状态, phone as 电话 FROM Appointments WHERE (patient_name LIKE '%{search_term}%' OR phone LIKE '%{search_term}%')"
            # 查就诊/离院的
            sql_cons = f"SELECT patient_name as 姓名, dept_name as 科室, room_number as 诊室号, status as 状态, phone as 电话 FROM Consultations WHERE (patient_name LIKE '%{search_term}%' OR phone LIKE '%{search_term}%')"

            df1 = pd.read_sql(sql_appt, conn)
            df2 = pd.read_sql(sql_cons, conn)

            # 合并显示
            df_all = pd.concat([df1, df2], ignore_index=True)

            if not df_all.empty:
                st.dataframe(df_all, use_container_width=True)
            else:
                st.warning("未找到匹配的患者信息")
        else:
            # 如果没搜索，就显示今天所有的就诊记录
            st.caption("今日就诊记录：")
            df_today = pd.read_sql(
                "SELECT patient_name as 姓名, dept_name as 科室, room_number as 诊室号, status as 状态 FROM Consultations",
                conn)
            st.dataframe(df_today, use_container_width=True)

    conn.close()

# --- C. 管理员端 ---
elif role == "管理员":
    st.header("🛡️ 医院管理后台")

    with st.sidebar:
        st.markdown("---")
        st.caption("🔧 调试工具箱")
        if st.button("✨ 生成演示数据"):
            st.toast(generate_fake_data())
            st.rerun()
        if st.button("🔥 清空所有数据"):
            st.toast(clear_all_data(), icon="🗑️")
            st.rerun()

    t1, t2 = st.tabs(["数据看板", "员工与排班管理"])
    conn = sqlite3.connect('hospital.db')

    with t1:
        # 需求②：统计
        try:
            df = pd.read_sql("SELECT * FROM View_Dept_Income", conn)
            if not df.empty:
                c1, c2 = st.columns([2, 1])
                c1.bar_chart(df.set_index("科室")["总收入"])
                c2.dataframe(df)
            else:
                st.info("暂无数据，请先生成演示数据。")
        except Exception as e:
            st.error("无法读取统计视图，请检查 schema.sql 是否包含 View 定义。")

    with t2:
        # 1. 展示列表
        st.markdown("### 📋 现有员工列表")
        df_staff = pd.read_sql("SELECT * FROM Staff", conn)
        st.dataframe(df_staff, use_container_width=True)

        st.divider()  # 分割线

        c1, c2 = st.columns(2)

        with c1:
            st.subheader("➕ 新增员工")
            with st.form("add_staff"):
                name = st.text_input("姓名")
                dept = st.selectbox("科室", ["内科", "外科", "儿科", "口腔科"], key="add_dept")
                title = st.selectbox("职称", ["主任医师", "副主任医师", "主治医师", "医师", "护士"], key="add_title")
                room = st.text_input("诊室号")
                phone = st.text_input("联系电话")
                schedule = st.text_input("排班时间 (如: 周一上午)")

                if st.form_submit_button("确认添加"):
                    if name:
                        conn.execute(
                            "INSERT INTO Staff (name, title, dept_name, room_number, schedule_time, phone, status) VALUES (?,?,?,?,?,?,'在职')",
                            (name, title, dept, room, schedule, phone))
                        conn.commit()
                        st.success(f"员工 {name} 添加成功！")
                        st.rerun()
                    else:
                        st.error("姓名不能为空")

        # 3. 修改员工信息
        with c2:
            st.subheader("✏️ 修改员工信息")
            if not df_staff.empty:
                # 第一步：选择要修改的人
                staff_names = df_staff['name'].tolist()
                selected_name = st.selectbox("选择要修改的员工", staff_names)

                # 获取该员工当前的详细信息
                current_info = df_staff[df_staff['name'] == selected_name].iloc[0]

                with st.form("edit_staff"):
                    # 显示并允许修改
                    new_phone = st.text_input("修改电话", value=current_info['phone'])
                    new_title = st.selectbox("修改职称", ["主任医师", "副主任医师", "主治医师", "医师", "护士"],
                                             index=["主任医师", "副主任医师", "主治医师", "医师", "护士"].index(
                                                 current_info['title']) if current_info['title'] in ["主任医师",
                                                                                                     "副主任医师",
                                                                                                     "主治医师", "医师",
                                                                                                     "护士"] else 0)
                    new_room = st.text_input("修改诊室", value=current_info['room_number'])
                    new_schedule = st.text_input("修改排班", value=current_info['schedule_time'])

                    # 状态修改
                    new_status = st.selectbox("工作状态", ["在职", "休假", "离职"],
                                              index=["在职", "休假", "离职"].index(current_info['status']) if
                                              current_info['status'] in ["在职", "休假", "离职"] else 0)

                    if st.form_submit_button("保存修改"):
                        conn.execute("""
                            UPDATE Staff 
                            SET phone=?, title=?, room_number=?, schedule_time=?, status=? 
                            WHERE id=?
                        """, (new_phone, new_title, new_room, new_schedule, new_status, int(current_info['id'])))
                        conn.commit()
                        st.success(f"{selected_name} 的信息已更新！")
                        st.rerun()
            else:
                st.info("暂无员工可修改")

    conn.close()