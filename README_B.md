对于schema.sql，基于模块SQLite实现了医院门诊管理系统的先进数据架构。不同于传统的CRUD设计，本项目采用了“业务逻辑下沉”（Logic Push-down）的策略，利用数据库的触发器（Triggers）和视图（Views）来保证数据的一致性、原子性和查询效率。

技术栈（技术堆栈）

数据库：SQLite 3

功能：触发器、视图、索引、事务

约束：外键、唯一约束、检查约束（通过触发器）

本模块主要解决了以下核心业务痛点：

1.自动化业务流转（Automated Workflows）

利用SQLite实现状态自动流转，消耗应用层干预：

挂号计数：预约成功后，排班表Doctor_Shift中的已挂号数自动+1。

状态闭环: 患者缴费成功(PayStatus变更为1)后，就诊状态自动流转为已离院。

2.数据一致性保护（并发控制）

防超卖机制：使用BEFORE INSERT引发“乐观锁”。在并发挂号场景下，若号源已满（BookedNum >= MaxNum），数据库层直接发送RAISE(ABORT)异常，阻止非法写入。

3.性能报表（分析与性能）

预编译视图：创建View_Dept_Income_Report，封装了复杂的多表连接 ( JOIN) 和聚合查询 ( GROUP BY)，供管理员快速查看科室分区。

索引优化：针对高频查询字段( ShiftDate, PayStatus, DeptID)建立了B-Tree索引，显着提升查询速度。
