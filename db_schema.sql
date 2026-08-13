-- ============================================================
-- 诊疗决策板块数据库脚本（整合版：建库 + 种子数据 + 网络资料扩充 + 蓝耳病/别名）
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

-- 2. 疾病表（alias: 别名列，逗号分隔俗名/缩写/曾用名，供交叉验证别名归一）
CREATE TABLE disease (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(64)  NOT NULL UNIQUE COMMENT '疾病名',
  alias         VARCHAR(256) COMMENT '别名，逗号分隔（俗名/缩写/曾用名），如：蓝耳病,PRRS',
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


-- ============ 第二节：网络资料扩充（爬取数据入库） ============
-- 数据来源: data/kg/herbs_extra.md, formulas_extra.md, data/rag/classics/*.txt

-- 1. 补充知识来源
INSERT INTO kg_source (id, title, category, detail) VALUES
(8, '《究原方》（录自《医方类聚》）', '典籍', '玉屏风散出处'),
(9, '《太平惠民和剂局方》', '典籍', '二陈汤出处'),
(10, '《医学心悟》', '典籍', '止嗽散出处'),
(11, '中兽医方剂（荆防败毒散）', '教材', '辛温解表剂，兽用非处方药'),
(12, '江西畜牧兽医杂志1991', '期刊', '清肺散验方'),
(13, '网络公开资料整理2026', '其他', '兽药典2015/兽药产品页/期刊摘要');

-- 2. 新增疾病：猪传染性胸膜肺炎
INSERT INTO disease (id, name, pathogen, epidemiology, symptoms, label, reference_id) VALUES
(5, '猪传染性胸膜肺炎', '胸膜肺炎放线杆菌', '急性高度接触性呼吸道病、各年龄均易感', '高热41℃+、犬坐姿势、张口呼吸、口鼻血性泡沫、四型分型', 'app', 13);

-- 3. 新增证候
INSERT INTO syndrome (id, name, stage, description, principle, reference_id) VALUES
(6, '风寒束肺', '前期', '风寒犯肺，肺失宣降，恶寒发热轻、鼻流清涕、咳嗽', '疏风散寒，宣肺止咳', 1),
(7, '痰湿壅肺', '中期', '脾失健运，痰湿犯肺，咳嗽痰多色白易咯、胸膈痞闷', '燥湿化痰，理气和中', 1);

-- 4. 新增药材（27味，剂量为网络公开人用/兽用参考）
INSERT INTO herb (id, name, property, flavor, meridian, effect, dosage_min, dosage_max, caution, reference_id) VALUES
(22, '薄荷', '凉', '辛', '肺肝', '疏散风热、清利头目、利咽透疹、疏肝行气', 3.0, 6.0, '体虚多汗不宜；后下不宜久煎', 13),
(23, '桑白皮', '寒', '甘', '肺', '泻肺平喘、利水消肿', 6.0, 15.0, '肺虚无火、风寒咳嗽忌', 13),
(24, '鱼腥草', '微寒', '辛', '肺', '清热解毒、消痈排脓、利尿通淋', 15.0, 25.0, '虚寒证及阴性外疡忌', 13),
(25, '浙贝母', '寒', '苦', '肺心', '清热化痰止咳、解毒散结消痈', 5.0, 10.0, '反乌头；寒痰湿痰不宜', 13),
(26, '板蓝根', '寒', '苦', '心胃', '清热解毒、凉血利咽', 9.0, 15.0, '体虚无实火热毒忌', 13),
(27, '蒲公英', '寒', '苦甘', '肝胃', '清热解毒、消肿散结、利尿通淋', 10.0, 15.0, '阳虚外寒、脾胃虚弱忌', 13),
(28, '紫菀', '温', '辛苦', '肺', '润肺下气、消痰止咳', 5.0, 10.0, '阴虚干咳慎服', 13),
(29, '款冬花', '温', '辛微苦', '肺', '润肺下气、止咳化痰', 5.0, 10.0, '孕妇不宜', 13),
(30, '瓜蒌', '寒', '甘微苦', '肺胃大肠', '清热涤痰、宽胸散结、润燥滑肠', 9.0, 15.0, '反乌头；脾胃虚寒、便溏忌', 13),
(31, '白术', '温', '苦甘', '脾胃', '健脾益气、燥湿利水、止汗安胎', 6.0, 15.0, '阴虚内热、津液亏耗者慎', 13),
(32, '防风', '微温', '辛甘', '膀胱肝脾', '祛风解表、胜湿止痛、止痉', 5.0, 10.0, '血虚痉急、阴虚火旺者慎', 13),
(33, '大青叶', '寒', '苦', '心胃', '清热解毒、凉血消斑', 9.0, 15.0, '脾胃虚寒者慎用', 13),
(34, '荆芥', '微温', '辛', '肺肝', '解表散风、透疹、消疮', 5.0, 10.0, NULL, 13),
(35, '牛蒡子', '寒', '辛苦', '肺胃', '疏散风热、宣肺透疹、解毒利咽', 6.0, 12.0, '气虚便溏者慎用', 13),
(36, '淡豆豉', '凉', '苦辛', '肺胃', '解表除烦、宣发郁热', 6.0, 12.0, NULL, 13),
(37, '淡竹叶', '寒', '甘淡', '心胃小肠', '清热泻火、除烦止渴、利尿通淋', 6.0, 10.0, NULL, 13),
(38, '芦根', '寒', '甘', '肺胃', '清热生津、除烦止呕、利尿', 15.0, 30.0, NULL, 13),
(39, '百部', '微温', '甘苦', '肺', '润肺下气止咳、杀虫灭虱', 5.0, 10.0, NULL, 13),
(40, '白前', '微温', '辛苦', '肺', '降气化痰、止咳', 5.0, 10.0, NULL, 13),
(41, '知母', '寒', '苦甘', '肺胃肾', '清热泻火、滋阴润燥', 6.0, 12.0, '脾胃虚寒、大便溏泄者忌', 13),
(42, '前胡', '微寒', '苦辛', '肺', '降气化痰、散风清热', 5.0, 10.0, NULL, 13),
(43, '枳壳', '微寒', '苦辛酸', '脾胃', '理气宽中、行滞消胀', 3.0, 10.0, '脾胃虚弱、孕妇慎用', 13),
(44, '川芎', '温', '辛', '肝胆心包', '活血行气、祛风止痛', 3.0, 10.0, '阴虚火旺、月经过多者慎用', 13),
(45, '羌活', '温', '辛苦', '膀胱肾', '解表散寒、祛风胜湿、止痛', 3.0, 10.0, NULL, 13),
(46, '独活', '微温', '辛苦', '肾膀胱', '祛风除湿、通痹止痛', 3.0, 10.0, NULL, 13),
(47, '柴胡', '微寒', '辛苦', '肝胆肺', '疏散退热、疏肝解郁、升举阳气', 3.0, 10.0, '肝阳上亢、阴虚火旺者慎', 13),
(48, '葶苈子', '大寒', '辛苦', '肺膀胱', '泻肺平喘、行水消肿', 3.0, 10.0, '肺虚喘咳、脾虚肿满者忌', 13);

-- 5. 新增配伍禁忌（反乌头：浙贝母/瓜蒌，来源: 网络资料）
INSERT INTO herb_contraindication (herb_a, herb_b, rule_type, description, reference_id) VALUES
(25, 21, '十八反', '浙贝母反乌头', 13),
(30, 21, '十八反', '瓜蒌反乌头', 13);

-- 6. 新增方剂（10首，挂证候）
INSERT INTO formula (id, name, syndrome_id, usage_method, course, notes, reference_id) VALUES
(5, '麻杏石甘汤', 2, '水煎温服（兽用可拌料）', '连用3-7天', '辛凉重剂：清肺平喘，主治肺热咳喘', 2),
(6, '玉屏风散', 5, '研末6-9g/次，或煎汤服', '连用7-14天', '益气固表，表虚自汗、体虚易感', 8),
(7, '二陈汤', 7, '水煎温服，加生姜7片乌梅1个', '连用3-5天', '燥湿化痰、理气和中', 9),
(8, '荆防败毒散', 6, '猪内服40-80g/次拌料；治疗1000g拌250kg料', '连用3-5天', '辛温解表、疏风祛湿，风寒感冒', 11),
(9, '止嗽散', 6, '散剂6-9g/次，姜汤送服', '连用3-7天', '宣利肺气、疏风止咳，新久咳嗽皆宜', 10),
(10, '清肺散', 2, '猪30-50g/头拌料或灌服', '连用3-5天', '清肺平喘、化痰止咳（江西畜牧兽医杂志1991验方）', 12),
(11, '麻杏石甘散（兽用）', 2, '猪30-60g/次拌料，每日1次', '连用5-7天', '清热宣肺平喘，肺热实喘', 13),
(12, '银翘散（兽用）', 1, '猪50-80g拌料；颗粒100g拌200kg料', '连用5-7天', '辛凉解表、清热解毒，风热感冒', 3),
(13, '双黄连口服液（兽用）', 1, '猪灌服10-15ml/次，或0.25ml/kg', '连用3-5天', '辛凉解表、清热解毒，流感/肺热咳喘', 13),
(14, '板青颗粒（兽用）', 1, '猪混饲100g拌100-150kg料', '连用3-7天', '清热解毒、凉血，风热感冒/病毒病', 13);

-- 7. 新增方剂组成
INSERT INTO formula_herb (formula_id, herb_id, dosage_g, role, sort_order) VALUES
-- 麻杏石甘汤：麻黄9 杏仁9 石膏24 甘草6
(5, 7, 9.0, '君', 1),
(5, 8, 24.0, '臣', 2),
(5, 11, 9.0, '佐', 3),
(5, 2, 6.0, '使', 4),
-- 玉屏风散：黄芪30 白术30 防风15
(6, 1, 30.0, '君', 1),
(6, 31, 30.0, '臣', 2),
(6, 32, 15.0, '佐', 3),
-- 二陈汤：半夏15 陈皮15 茯苓9 甘草4.5
(7, 12, 15.0, '君', 1),
(7, 13, 15.0, '臣', 2),
(7, 4, 9.0, '佐', 3),
(7, 2, 4.5, '使', 4),
-- 荆防败毒散（12味）
(8, 34, 45.0, '君', 1),
(8, 32, 30.0, '君', 2),
(8, 45, 25.0, '臣', 3),
(8, 46, 25.0, '臣', 4),
(8, 47, 30.0, '臣', 5),
(8, 42, 25.0, '臣', 6),
(8, 43, 30.0, '佐', 7),
(8, 4, 45.0, '佐', 8),
(8, 5, 30.0, '佐', 9),
(8, 44, 25.0, '佐', 10),
(8, 22, 15.0, '佐', 11),
(8, 2, 15.0, '使', 12),
-- 止嗽散：桔梗3 荆芥6 紫菀9 百部9 白前6 甘草3 陈皮6
(9, 5, 3.0, '臣', 1),
(9, 34, 6.0, '佐', 2),
(9, 28, 9.0, '君', 3),
(9, 39, 9.0, '君', 4),
(9, 40, 6.0, '臣', 5),
(9, 2, 3.0, '使', 6),
(9, 13, 6.0, '佐', 7),
-- 清肺散：板蓝根30 葶苈子25 浙贝母20 桔梗20 甘草15
(10, 26, 30.0, '君', 1),
(10, 48, 25.0, '臣', 2),
(10, 25, 20.0, '臣', 3),
(10, 5, 20.0, '佐', 4),
(10, 2, 15.0, '使', 5),
-- 麻杏石甘散兽用（同麻杏石甘汤组成）
(11, 7, 9.0, '君', 1),
(11, 8, 24.0, '臣', 2),
(11, 11, 9.0, '佐', 3),
(11, 2, 6.0, '使', 4),
-- 银翘散兽用：金银花60 连翘45 薄荷30 荆芥30 淡豆豉30 牛蒡子45 桔梗25 淡竹叶20 甘草20 芦根30
(12, 9, 60.0, '君', 1),
(12, 10, 45.0, '君', 2),
(12, 22, 30.0, '臣', 3),
(12, 34, 30.0, '臣', 4),
(12, 36, 30.0, '臣', 5),
(12, 35, 45.0, '臣', 6),
(12, 5, 25.0, '佐', 7),
(12, 37, 20.0, '佐', 8),
(12, 38, 30.0, '佐', 9),
(12, 2, 20.0, '使', 10),
-- 双黄连口服液：金银花 黄芩 连翘
(13, 9, 20.0, '君', 1),
(13, 3, 15.0, '臣', 2),
(13, 10, 15.0, '佐', 3),
-- 板青颗粒：板蓝根 大青叶
(14, 26, 30.0, '君', 1),
(14, 33, 30.0, '臣', 2);

-- 8. 新增随症加减规则
INSERT INTO add_rule (formula_id, condition_desc, herb_id, operation, dosage_g, reference_id) VALUES
(5, '痰黄黏重加', 24, '加', 20.0, 13),
(5, '口渴甚加', 38, '加', 15.0, 13),
(8, '咳重加', 39, '加', 10.0, 13),
(12, '咽喉肿痛加', 35, '加', 15.0, 13);

-- 9. 新增辨证规则（基于网络资料）
INSERT INTO syndrome_mapping
  (id, temperature_min, temperature_max, cough_type, excretion, other_signs, syndrome_id, disease_id, evidence, weight, reference_id) VALUES
(5, 39.5, 42.0, '阵咳似尖叫、呼吸急促', '便秘', '突发高热、扎堆卧、眼鼻分泌物', 1, 2, '发病急、传播快、病程5-7天', 9, 13),
(6, 40.0, 42.0, '咳嗽、张口呼吸', '便秘', '犬坐姿势、口鼻血性泡沫', 2, 5, '高热41℃+、最急性24-36h死亡', 8, 13),
(7, NULL, 39.0, '干咳、晨夜加重', '正常', '体温正常、食欲尚可、病程长', 2, 1, '体温不高是支原体关键鉴别点', 9, 13),
(8, NULL, NULL, '恶寒颤抖、鼻流清涕', '正常', '耳耷头低、腰弓毛乍、发热轻', 6, NULL, '风寒感冒、无高热', 7, 13),
(9, NULL, NULL, '咳嗽痰多色白易咯', '正常', '胸膈痞闷、肢体困重', 7, NULL, '湿痰证、苔白滑', 6, 13);


-- ============ 第三节：蓝耳病入库 + 疾病别名 ============

-- 1. 补充现有疾病的别名
UPDATE disease SET alias='猪气喘病,支原体肺炎,Mhp' WHERE id=1;
UPDATE disease SET alias='猪流感,SI,Swine Influenza' WHERE id=2;
UPDATE disease SET alias='猪巴氏杆菌病,锁喉风,肿脖子瘟,Pasteurella multocida' WHERE id=3;
UPDATE disease SET alias='PRDC,多病原混合感染' WHERE id=4;
UPDATE disease SET alias='APP,胸膜肺炎放线杆菌病' WHERE id=5;

-- 2. 新增：猪繁殖与呼吸综合征（蓝耳病）
INSERT INTO disease (id, name, alias, pathogen, epidemiology, symptoms, label, reference_id) VALUES
(6, '猪繁殖与呼吸综合征', '蓝耳病,猪蓝耳病,PRRS,猪繁殖与呼吸障碍综合征,神秘猪病,HP-PRRS',
 '猪繁殖与呼吸综合征病毒（PRRSV）',
 '动脉炎病毒科RNA病毒，免疫抑制性强（"免疫抑制之王"），猪唯一易感；妊娠母猪和1月龄内仔猪最易感，哺乳仔猪死亡率可达80%以上；接触/气溶胶/精液/垂直四种传播途径；冬春高发',
 '繁殖障碍+呼吸道症状，"三高一低"（高体温/高发病率/高死亡率/低治愈率）：母猪发热40-42.5℃、妊娠后期流产早产死胎木乃伊胎、耳尖及躯干发绀；仔猪呼吸困难、耳尖发紫继而全耳蓝紫色、共济失调、僵猪比例大；育肥猪两耳发蓝、生长发育缓慢；剖检间质性肺炎"橡皮肺"',
 'prrs', 13);

-- 3. 新增辨证规则（依据典籍蓝耳病章节，中医病机映射）
-- 急性型：高热+呼吸急促+耳尖发紫 → 疫热壅肺（中期）
INSERT INTO syndrome_mapping
  (id, temperature_min, temperature_max, cough_type, excretion, other_signs, syndrome_id, disease_id, evidence, weight, reference_id) VALUES
(10, 40.0, 42.5, '呼吸急促、咳嗽气喘', '正常', '耳尖发紫、精神沉郁、母猪流产死胎、三高一低', 2, 6,
 '蓝耳病急性型：高热40-42.5℃+呼吸急促+耳尖发绀，热毒壅肺', 8, 13);
-- 慢性型：耳尖发紫+病程长+发育迟缓 → 气阴两伤（后期，正虚邪恋/免疫抑制）
INSERT INTO syndrome_mapping
  (id, temperature_min, temperature_max, cough_type, excretion, other_signs, syndrome_id, disease_id, evidence, weight, reference_id) VALUES
(11, NULL, 39.5, '咳嗽、喘气', '腹泻（仔猪）', '耳尖发紫、病程长、发育迟缓、僵猪、免疫抑制', 3, 6,
 '蓝耳病慢性型：病程长、正虚邪恋（免疫抑制），耳尖发绀+僵猪为气阴两伤表现', 7, 13);

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
