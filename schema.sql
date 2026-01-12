-- 1. 员工/排班表
CREATE TABLE IF NOT EXISTS Staff (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    title TEXT,
    dept_name TEXT,
    room_number TEXT,
    schedule_time TEXT,
    phone TEXT,
    status TEXT DEFAULT '在职'
);

-- 2. 预约表
CREATE TABLE IF NOT EXISTS Appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_name TEXT,
    dept_name TEXT,
    phone TEXT,
    expected_time TEXT,
    status TEXT DEFAULT '待就诊'
);

-- 3. 就诊信息表 
CREATE TABLE IF NOT EXISTS Consultations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_name TEXT,
    gender TEXT,
    id_card TEXT,
    phone TEXT,
    dept_name TEXT,
    room_number TEXT,
    status TEXT,
    visit_time TEXT
);

-- 4. 费用表 
CREATE TABLE IF NOT EXISTS Payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consultation_id INTEGER,
    total_amount REAL,
    insurance_amount REAL,
    self_pay_amount REAL,
    payment_time TEXT
);

-- 5. 触发器：缴费后自动改状态 
DROP TRIGGER IF EXISTS After_Payment_Update_Status;
CREATE TRIGGER After_Payment_Update_Status
AFTER INSERT ON Payments
BEGIN
    UPDATE Consultations
    SET status = '已离院'
    WHERE id = NEW.consultation_id;
END;

-- 6. 视图：管理员统计 
DROP VIEW IF EXISTS View_Dept_Income;
CREATE VIEW View_Dept_Income AS
SELECT
    c.dept_name AS 科室,
    IFNULL(SUM(p.total_amount), 0) AS 总收入
FROM Consultations c
JOIN Payments p ON c.id = p.consultation_id
GROUP BY c.dept_name;