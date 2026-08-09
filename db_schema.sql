-- ============================================================
-- 诊疗决策板块数据库脚本
-- MySQL 8.0 | 库名: pig_diag | 字符集: utf8mb4
-- 配套文档: 诊疗决策板块_数据库设计.md
-- 执行: mysql -u root -p < db_schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS pig_diag
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE pig_diag;

-- ============================================================
-- 一、知识库表（论治层数据底座）
-- ============================================================

DROP TABLE IF EXISTS herb_contraindication;
DROP TABLE IF EXISTS add_rule;
DROP TABLE IF EXISTS formula_herb;
DROP TABLE IF EXISTS formula;
DROP TABLE IF EXISTS herb;
DROP TABLE IF EXISTS syndrome_mapping;
DROP TABLE IF EXISTS syndrome;
DROP TABLE IF EXISTS disease;
DROP TABLE IF EXISTS kg_source;
DROP TABLE IF EXISTS treatment_feedback;
DROP TABLE IF EXISTS prescription_record;
DROP TABLE IF EXISTS diagnosis_record;

-- 1. 知识来源表（杜绝幻觉引用）
CREATE TABLE kg_source (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  title         VARCHAR(256) NOT NULL COMMENT '文献/出处标题',
  category      VARCHAR(32)  COMMENT '类型：教材/典籍/临床病例/PPT验证',
  detail        VARCHAR(512) COMMENT '章节/页码等定位信息',
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识来源表';

-- 2. 疾病表
CREATE TABLE disease (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(64)  NOT NULL UNIQUE COMMENT '疾病名',
  pathogen      VARCHAR(128) COMMENT '病原体',
  epidemiology  VARCHAR(512) COMMENT '流行病学特点',
  symptoms      VARCHAR(512) COMMENT '典型症状',
  label         VARCHAR(64)  COMMENT '辨病模型分类标签(英文小写)',
  reference_id  BIGINT UNSIGNED,
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='疾病表';

-- 3. 证候表（理+法：证候定义与治则治法）
CREATE TABLE syndrome (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(64)  NOT NULL UNIQUE COMMENT '证候名',
  stage         VARCHAR(32)  NOT NULL COMMENT '中医分期',
  description   VARCHAR(512) COMMENT '证候描述',
  principle     VARCHAR(128) NOT NULL COMMENT '治则治法',
  reference_id  BIGINT UNSIGNED,
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='证候表';

-- 4. 辨证库：多维体征 → 证候映射规则
CREATE TABLE syndrome_mapping (
  id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  temperature_min DECIMAL(4,1) COMMENT '体温下限(℃)，NULL=不限',
  temperature_max DECIMAL(4,1) COMMENT '体温上限(℃)，NULL=不限',
  cough_type      VARCHAR(128) COMMENT '咳喘表现关键词',
  excretion       VARCHAR(128) COMMENT '排泄物观察',
  other_signs     VARCHAR(256) COMMENT '其他体征：精神、采食、呼吸等',
  syndrome_id     BIGINT UNSIGNED NOT NULL COMMENT '命中证候',
  disease_id      BIGINT UNSIGNED COMMENT '关联疾病(可空)',
  evidence        VARCHAR(512) COMMENT '鉴别依据',
  weight          TINYINT UNSIGNED DEFAULT 5 COMMENT '权重1-10',
  reference_id    BIGINT UNSIGNED,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_syndrome (syndrome_id),
  KEY idx_disease (disease_id),
  KEY idx_temp (temperature_min, temperature_max)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='辨证库：多维体征→证候映射';

-- 5. 药材表（安全剂量区间 = 校验护栏）
CREATE TABLE herb (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(64)  NOT NULL UNIQUE COMMENT '药材名',
  property      VARCHAR(16)  COMMENT '四性',
  flavor        VARCHAR(32)  COMMENT '五味',
  meridian      VARCHAR(64)  COMMENT '归经',
  effect        VARCHAR(256) COMMENT '功效',
  dosage_min    DECIMAL(6,1) COMMENT '安全剂量下限(克)',
  dosage_max    DECIMAL(6,1) COMMENT '安全剂量上限(克)',
  caution       VARCHAR(256) COMMENT '使用注意',
  reference_id  BIGINT UNSIGNED,
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='药材表';

-- 6. 方剂表
CREATE TABLE formula (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(64)  NOT NULL UNIQUE COMMENT '方剂名',
  syndrome_id   BIGINT UNSIGNED NOT NULL COMMENT '主治证候',
  usage_method  VARCHAR(256) COMMENT '用法',
  course        VARCHAR(64)  COMMENT '疗程',
  notes         VARCHAR(512) COMMENT '方解/备注',
  reference_id  BIGINT UNSIGNED,
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_syndrome (syndrome_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='方剂表';

-- 7. 方剂-药材组成表
CREATE TABLE formula_herb (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  formula_id    BIGINT UNSIGNED NOT NULL,
  herb_id       BIGINT UNSIGNED NOT NULL,
  dosage_g      DECIMAL(6,1) NOT NULL COMMENT '基础剂量(克)',
  role          VARCHAR(16)  NOT NULL COMMENT '君臣佐使',
  note          VARCHAR(256) COMMENT '作用说明',
  sort_order    TINYINT UNSIGNED DEFAULT 0,
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_formula_herb (formula_id, herb_id),
  KEY idx_herb (herb_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='方剂组成表';

-- 8. 随症加减规则表
CREATE TABLE add_rule (
  id             BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  formula_id     BIGINT UNSIGNED NOT NULL COMMENT '所属方剂',
  condition_desc VARCHAR(256) NOT NULL COMMENT '加减条件',
  herb_id        BIGINT UNSIGNED COMMENT '加减药物(可空=减药)',
  operation      VARCHAR(8)    NOT NULL DEFAULT '加' COMMENT '加/减/调整剂量',
  dosage_g       DECIMAL(6,1)  COMMENT '加减剂量',
  reference_id   BIGINT UNSIGNED,
  created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_formula (formula_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='随症加减规则表';

-- 9. 配伍禁忌表（十八反/十九畏，安全护栏）
CREATE TABLE herb_contraindication (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  herb_a        BIGINT UNSIGNED NOT NULL,
  herb_b        BIGINT UNSIGNED NOT NULL,
  rule_type     VARCHAR(16)  NOT NULL COMMENT '十八反/十九畏/孕猪禁用/其他',
  description   VARCHAR(256) COMMENT '说明',
  reference_id  BIGINT UNSIGNED,
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_pair (herb_a, herb_b)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='配伍禁忌表';

-- ============================================================
-- 二、业务记录表（闭环反馈）
-- ============================================================

-- 10. 辨病记录
CREATE TABLE diagnosis_record (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  pig_house     VARCHAR(64)  COMMENT '猪舍编号',
  model_label   VARCHAR(64)  COMMENT '辨病模型输出标签',
  disease_id    BIGINT UNSIGNED COMMENT '命中疾病',
  confidence    DECIMAL(4,3) COMMENT '置信度0-1',
  temp_c        DECIMAL(4,1) COMMENT '体温℃',
  mental_state  VARCHAR(64)  COMMENT '精神状态',
  env_json      JSON         COMMENT '环境参数快照',
  feature_json  JSON         COMMENT '声学特征快照(可选)',
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_house_time (pig_house, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='辨病记录';

-- 11. 处方记录（组方+校验结果）
CREATE TABLE prescription_record (
  id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  diagnosis_id    BIGINT UNSIGNED COMMENT '关联辨病记录',
  syndrome_id     BIGINT UNSIGNED COMMENT '辨证结果-证候',
  formula_id      BIGINT UNSIGNED COMMENT '基础方剂',
  herbs_json      JSON         COMMENT '组方明细[{name,dosage_g,role}]',
  usage_method    VARCHAR(256) COMMENT '用法',
  course          VARCHAR(64)  COMMENT '疗程',
  safety_approved TINYINT(1)   DEFAULT 0 COMMENT '校验是否通过',
  safety_report   JSON         COMMENT '校验报告',
  llm_raw         TEXT         COMMENT 'LLM原始输出(审计用)',
  references_json JSON         COMMENT '引用出处列表',
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_diagnosis (diagnosis_id),
  KEY idx_syndrome (syndrome_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='处方记录';

-- 12. 疗效反馈表（闭环）
CREATE TABLE treatment_feedback (
  id                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  prescription_id   BIGINT UNSIGNED NOT NULL,
  day_after         TINYINT UNSIGNED COMMENT '用药第N天',
  cough_freq_change VARCHAR(32)  COMMENT '咳嗽频率变化',
  temp_change       VARCHAR(32)  COMMENT '体温变化',
  mental_change     VARCHAR(64)  COMMENT '精神状态变化',
  outcome           VARCHAR(32)  COMMENT '结局：治愈/好转/无效/恶化',
  adjustment        VARCHAR(256) COMMENT '方案调整',
  effective_score   DECIMAL(3,2) COMMENT '疗效评分0-1',
  created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_prescription (prescription_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='疗效反馈表';

-- ============================================================
-- 三、种子数据（录入顺序：来源→疾病→证候→辨证→药材→方剂→组成→加减→禁忌）
-- ============================================================

-- 3.1 知识来源
INSERT INTO kg_source (id, title, category, detail) VALUES
(1, '中兽医学（教材）', '教材', '辨证论治/脏腑辨证章节'),
(2, '伤寒论', '典籍', '麻杏石甘汤条目'),
(3, '温病条辨', '典籍', '银翘散条目'),
(4, '丹溪心法', '典籍', '玉屏风散条目'),
(5, '音甘猪咳嗽三代技术PPT', 'PPT验证', '迎甘组方实操验证'),
(6, '兽医中药学', '教材', '药材性味归经/安全剂量'),
(7, '猪呼吸道疾病诊疗规范', '临床', '症状描述/用药指导');

-- 3.2 疾病
INSERT INTO disease (id, name, pathogen, epidemiology, symptoms, label, reference_id) VALUES
(1, '猪支原体肺炎', '猪肺炎支原体', '慢性、接触传播、冬季高发', '湿咳、痰多、呼吸粗、食欲下降', 'mycoplasma', 1),
(2, '猪流感', '猪流感病毒', '突发、群发、传播快', '干咳、鼻流清涕、高热40℃+', 'influenza', 1),
(3, '猪肺疫', '多杀性巴氏杆菌', '急性败血症、死亡快', '咳嗽、呼吸困难、颈部肿胀', 'pasteurella', 1),
(4, '混合感染', '多种病原', '病程长、反复发作', '咳嗽、喘促、精神萎靡', 'mixed', 1);

-- 3.3 证候（理-法）
INSERT INTO syndrome (id, name, stage, description, principle, reference_id) VALUES
(1, '邪袭肺卫', '前期', '表证，卫分证，病邪初犯肺卫', '疏风解表，宣肺止咳', 1),
(2, '疫热壅肺', '中期', '里证，气分证，热邪壅盛于肺', '清热化痰，宣肺平喘', 1),
(3, '气阴两伤', '后期', '虚证，气阴亏虚，正虚邪恋', '益气养阴，扶正祛邪', 1),
(4, '痰热壅肺', '中期', '痰热互结，肺气壅塞', '清肺化痰，降气止咳', 1),
(5, '肺卫气虚', '恢复期', '肺气不足，卫外不固', '益气固表，补肺健脾', 4);

-- 3.4 辨证库（多维体征→证候）
INSERT INTO syndrome_mapping
  (id, temperature_min, temperature_max, cough_type, excretion, other_signs, syndrome_id, disease_id, evidence, weight, reference_id) VALUES
(1, 38.5, 40.0, '湿咳、痰多、呼吸粗', '正常', '食欲下降、精神稍差', 2, 1, '干咳转湿咳、无明显高热', 8, 1),
(2, 40.0, NULL, '干咳、鼻流清涕', '水样便', '精神差、突发、群发', 1, 2, '传播快、体温40℃以上', 8, 1),
(3, 39.0, 41.0, '咳嗽、呼吸困难', '便秘', '颈部肿胀', 2, 3, '急性败血症表现、死亡快', 7, 1),
(4, 38.0, 39.5, '咳嗽、喘促', '稀溏', '精神萎靡、病程长', 3, 4, '反复发作、正虚邪恋', 7, 1);

-- 3.5 药材（PPT 6味 + 经典方常用 10味；剂量区间 = 校验护栏）
INSERT INTO herb (id, name, property, flavor, meridian, effect, dosage_min, dosage_max, caution, reference_id) VALUES
(1, '黄芪', '微温', '甘', '肺脾', '补气升阳、固表止汗', 15.0, 30.0, NULL, 6),
(2, '甘草', '平', '甘', '心肺脾胃', '补脾益气、清热解毒、调和诸药', 5.0, 25.0, NULL, 6),
(3, '黄芩', '寒', '苦', '肺胆', '清热燥湿、泻火解毒', 10.0, 30.0, NULL, 6),
(4, '茯苓', '平', '甘淡', '心脾肾', '利水渗湿、健脾宁心', 10.0, 20.0, NULL, 6),
(5, '桔梗', '平', '苦辛', '肺', '宣肺利咽、祛痰排脓', 5.0, 10.0, NULL, 6),
(6, '满山红', '寒', '苦', '肺', '止咳祛痰', 5.0, 15.0, NULL, 5),
(7, '麻黄', '温', '辛苦', '肺膀胱', '发汗解表、宣肺平喘', 5.0, 15.0, '孕猪慎用', 6),
(8, '石膏', '大寒', '辛甘', '肺胃', '清热泻火、除烦止渴', 15.0, 60.0, NULL, 6),
(9, '金银花', '寒', '甘', '肺心胃', '清热解毒、疏散风热', 10.0, 30.0, NULL, 6),
(10, '连翘', '寒', '苦', '肺心胆', '清热解毒、消肿散结', 10.0, 30.0, NULL, 6),
(11, '杏仁', '温', '苦', '肺大肠', '降气止咳平喘、润肠通便', 5.0, 15.0, NULL, 6),
(12, '半夏', '温', '辛', '脾胃肺', '燥湿化痰、降逆止呕', 5.0, 15.0, '孕猪慎用', 6),
(13, '陈皮', '温', '辛苦', '脾胃肺', '理气健脾、燥湿化痰', 5.0, 15.0, NULL, 6),
(14, '党参', '平', '甘', '脾肺', '补中益气、健脾益肺', 10.0, 30.0, NULL, 6),
(15, '麦冬', '寒', '甘微苦', '心肺胃', '养阴生津、润肺清心', 10.0, 20.0, NULL, 6),
(16, '五味子', '温', '酸甘', '肺心肾', '收敛固涩、益气生津', 3.0, 10.0, NULL, 6),
-- 十八反演示用药（安全护栏校验数据，正常组方不使用）
(17, '甘遂', '寒', '苦', '肺肾大肠', '泻水逐饮、消肿散结（十八反甘草）', 0.5, 3.0, '反甘草，严禁同用', 6),
(18, '大戟', '寒', '苦辛', '肺脾肾', '泻水逐饮（十八反甘草）', 0.5, 3.0, '反甘草，严禁同用', 6),
(19, '芫花', '温', '辛苦', '肺脾肾', '泻水逐饮（十八反甘草）', 0.5, 3.0, '反甘草，严禁同用', 6),
(20, '海藻', '寒', '苦咸', '肝肾', '消痰软坚、利水（十八反甘草）', 3.0, 10.0, '反甘草，严禁同用', 6),
(21, '乌头', '热', '辛苦', '心脾肝肾', '祛风除湿、温经止痛（十八反半夏）', 1.0, 5.0, '反半夏，孕猪禁用', 6);

-- 3.6 方剂
INSERT INTO formula (id, name, syndrome_id, usage_method, course, notes, reference_id) VALUES
(1, '迎甘组方', 2, '按500g饲料混饲', '连用5-7天', 'PPT三代技术实操验证方剂', 5),
(2, '银翘散加减', 1, '按500g饲料混饲', '连用3-5天', '表证宣散，忌用于脾虚便溏', 3),
(3, '生脉散加减', 3, '按500g饲料混饲', '连用7-10天', '扶正为主，外感未解者忌', 1),
(4, '清肺止咳散加减', 4, '按500g饲料混饲', '连用5-7天', '痰热壅肺主方', 1);

-- 3.7 方剂组成（君-臣-佐-使）
INSERT INTO formula_herb (formula_id, herb_id, dosage_g, role, sort_order) VALUES
-- 迎甘组方（PPT验证：黄芪30 甘草25 黄芩20 茯苓15 桔梗5 满山红5）
(1, 1, 30.0, '君', 1),
(1, 3, 20.0, '臣', 2),
(1, 2, 25.0, '佐', 3),
(1, 4, 15.0, '佐', 4),
(1, 5, 5.0, '使', 5),
(1, 6, 5.0, '使', 6),
-- 银翘散加减（金银花15 连翘15 桔梗10 薄荷6 甘草5）
(2, 9, 15.0, '君', 1),
(2, 10, 15.0, '臣', 2),
(2, 5, 10.0, '佐', 3),
(2, 2, 5.0, '使', 4),
-- 生脉散加减（党参20 麦冬15 五味子8 黄芪20）
(3, 14, 20.0, '君', 1),
(3, 15, 15.0, '臣', 2),
(3, 16, 8.0, '佐', 3),
(3, 1, 20.0, '佐', 4),
-- 清肺止咳散加减（黄芩15 桔梗10 杏仁10 半夏10 甘草8）
(4, 3, 15.0, '君', 1),
(4, 5, 10.0, '臣', 2),
(4, 11, 10.0, '臣', 3),
(4, 12, 10.0, '佐', 4),
(4, 2, 8.0, '使', 5);

-- 3.8 随症加减规则
INSERT INTO add_rule (formula_id, condition_desc, herb_id, operation, dosage_g, reference_id) VALUES
(1, '痰多加', 12, '加', 10.0, 5),
(1, '气虚加', 14, '加', 15.0, 5),
(1, '久咳加', 16, '加', 5.0, 5),
(2, '表虚汗多加', 1, '加', 20.0, 3),
(3, '余热未清加', 3, '加', 10.0, 1),
(4, '痰黄黏加', 8, '加', 20.0, 1),
(1, '腹泻减', 3, '减', 5.0, 5);

-- 3.9 配伍禁忌（十八反/十九畏，安全护栏）
-- 注：药材ID见3.5；十九畏规则按需补充（参考《兽医中药学》）
INSERT INTO herb_contraindication (herb_a, herb_b, rule_type, description, reference_id) VALUES
(2, 17, '十八反', '甘草反甘遂', 6),
(2, 18, '十八反', '甘草反大戟', 6),
(2, 19, '十八反', '甘草反芫花', 6),
(2, 20, '十八反', '甘草反海藻', 6),
(21, 12, '十八反', '乌头反半夏', 6),
(12, 21, '十八反', '半夏反乌头', 6);

-- ============================================================
-- 四、常用查询示例（Text-to-SQL 参照）
-- ============================================================

-- 4.1 按体征组合查证候（辨证库精确检索）
-- SELECT s.name, s.principle FROM syndrome_mapping m
--   JOIN syndrome s ON s.id = m.syndrome_id
--   WHERE (m.temperature_min IS NULL OR 39.2 >= m.temperature_min)
--     AND (m.temperature_max IS NULL OR 39.2 <= m.temperature_max)
--     AND m.cough_type LIKE '%湿咳%'
--   ORDER BY m.weight DESC LIMIT 3;

-- 4.2 按证候取方剂+组成+剂量（论治库）
-- SELECT f.name AS formula, h.name AS herb, fh.dosage_g, fh.role, h.dosage_min, h.dosage_max
--   FROM formula f
--   JOIN formula_herb fh ON fh.formula_id = f.id
--   JOIN herb h ON h.id = fh.herb_id
--   WHERE f.syndrome_id = 2
--   ORDER BY fh.sort_order;

-- 4.3 安全校验：查某方剂是否含配伍禁忌
-- SELECT h1.name, h2.name, hc.rule_type
--   FROM formula_herb fh1
--   JOIN formula_herb fh2 ON fh1.formula_id = fh2.formula_id AND fh1.herb_id < fh2.herb_id
--   JOIN herb_contraindication hc ON (hc.herb_a = fh1.herb_id AND hc.herb_b = fh2.herb_id)
--      OR (hc.herb_a = fh2.herb_id AND hc.herb_b = fh1.herb_id)
--   JOIN herb h1 ON h1.id = fh1.herb_id
--   JOIN herb h2 ON h2.id = fh2.herb_id
--   WHERE fh1.formula_id = 1;

-- 4.4 疗效统计（闭环）
-- SELECT syndrome_id, COUNT(*) AS cases,
--        SUM(outcome IN ('治愈','好转')) / COUNT(*) AS effective_rate
--   FROM prescription_record p
--   JOIN treatment_feedback f ON f.prescription_id = p.id
--   GROUP BY syndrome_id;
