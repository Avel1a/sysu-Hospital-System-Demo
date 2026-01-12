
## 1. 实体结构

整个数据库是围绕四个核心实体来开展构建工作的，这四类实体共同对应了门诊系统当中的完整业务流程。

### **Staff**

该表相当于是把员工信息以及排班安排结合在一起进行存放的结构，它会把医生或护士的姓名、职称、电话等基础信息，以及它们所对应的科室名称 dept_name、诊室 room_number、排班时间 schedule_time 等内容一并记录下来。这样一来，就能够契合管理端在查询员工信息以及开展排班调整方面的需求。

### **Appointments**

该表主要是用来承载“到院前”阶段的数据，它会把预约所需的那部分关键信息，比如姓名、科室、电话以及预计到达时间等内容进行保存。按照前台的业务要求，这里的记录会被用来开展核验工作，并且在患者真正到达之后，会被标记成 “Completed”。

### **Consultations**

该表负责记录“现场就诊”阶段的数据，是整个系统当中的核心事务表。无论是预约被核验之后进入就诊，还是出现现场挂号的情况，都会把对应的数据插入到这里。同时，它还会补充一些在 Appointment 阶段并未出现但在就诊环节必须具备的字段，比如 gender、id_card、room_number 等。

### **Payments**

该表负责“离院结算”阶段的内容，它会直接与某一次具体的就诊记录进行关联。

---

## 2. 关系与约束

### **Consultations ↔ Payments（1:1 关系）**

- **机制**：Payments 表当中会选用 consultation_id 作为外键字段。  
- **逻辑**：一次就诊只会生成一条对应的结算记录。依靠这种关联方式，系统就可以把 Payments 与 Consultations 进行连接，从而去统计某个科室或某位医生所产生的收入总额。  
- **规范**：这里严格遵循 SQL 当中 FOREIGN KEY (consultation_id) REFERENCES Consultations(id) 的约束。

### **Appointments ↔ Consultations（逻辑流程关系）**

- **机制**：在给出的 SQL 中，这两者之间并没有设置强外键。  
- **逻辑**：两者之间的关系更多是流程性的。前台会先去查询 Appointments 表，核对 patient_name 与 phone，然后再把对应的数据创建成一条新的 Consultations 记录。这种方式属于一种“松耦合”，在简单的挂号系统中比较常见，因为预约只是“请求”，而真正的就诊才是“事件”。

### **Staff ↔ Consultations（基于字段值的关联）**

- **机制**：两者是依靠 dept_name 与 room_number 来进行匹配的。  
- **逻辑**：为了判断某位患者是由哪位医生接诊，系统会把 Consultations 中的 room_number 与 visit_time，和 Staff 中的 room_number 与 schedule_time 进行比对。

---

## 3. 需求对应情况

### **数据分析（背景需求）**

管理端可以借助对 Consultations（按 dept_name 分组）以及 Payments（对 total_amount 求和）的查询，来开展对患者就诊模式以及收入情况的分析，而不需要构建复杂的数据仓库。

### **患者身份信息**

在实际就诊（Consultations）阶段，id_card 是法律层面必须提供的内容；但在快速线上预约（Appointments）阶段并不强制要求，从而能够在预约环节降低用户操作的阻力。

### **状态追踪**

Appointments 与 Consultations 都具备 status 字段（如“待就诊”“就诊中”“已离院”），这样前台就可以依靠状态来进行筛选，比如查看所有正在进行的就诊记录。




