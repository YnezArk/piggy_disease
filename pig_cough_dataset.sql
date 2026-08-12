/*
 Navicat Premium Dump SQL

 Source Server         : 猪咳嗽数据库
 Source Server Type    : MySQL
 Source Server Version : 80046 (8.0.46)
 Source Host           : localhost:3306
 Source Schema         : pig_cough_dataset

 Target Server Type    : MySQL
 Target Server Version : 80046 (8.0.46)
 File Encoding         : 65001

 Date: 11/08/2026 21:24:30
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for audio_sample
-- ----------------------------
DROP TABLE IF EXISTS `audio_sample`;
CREATE TABLE `audio_sample`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '样本唯一ID',
  `farm_code` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '猪场编号',
  `pig_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '猪只编号',
  `sample_type` tinyint NOT NULL COMMENT '1=咳嗽正样本，0=无咳嗽负样本',
  `audio_filename` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '音频文件名',
  `relative_path` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '音频相对路径（交付关键）',
  `audio_duration` float NOT NULL COMMENT '音频时长秒',
  `sample_rate` int NOT NULL COMMENT '采样率',
  `file_size` int NOT NULL COMMENT '文件大小字节',
  `record_time` datetime NOT NULL COMMENT '录制时间',
  `annotator` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '标注人',
  `dataset_split` tinyint NOT NULL DEFAULT 0 COMMENT '0未划分 1训练集 2验证集 3测试集',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_sample_type`(`sample_type` ASC) USING BTREE,
  INDEX `idx_dataset_split`(`dataset_split` ASC) USING BTREE,
  INDEX `idx_farm`(`farm_code` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 303 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '生猪咳嗽音频样本总表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of audio_sample
-- ----------------------------
INSERT INTO `audio_sample` VALUES (3, 'net01', 'net01001', 1, '1.wav', 'positive/farm_net01/1.wav', 0, 16000, 16512, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (4, 'net01', 'net01002', 1, '2.wav', 'positive/farm_net01/2.wav', 0, 16000, 16716, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (5, 'net01', 'net01003', 1, '3.wav', 'positive/farm_net01/3.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (6, 'net01', 'net01004', 1, '4.wav', 'positive/farm_net01/4.wav', 0, 16000, 16512, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (7, 'net01', 'net01005', 1, '5.wav', 'positive/farm_net01/5.wav', 0, 16000, 16128, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (8, 'net01', 'net01006', 1, '6.wav', 'positive/farm_net01/6.wav', 0, 16000, 16238, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (9, 'net01', 'net01007', 1, '7.wav', 'positive/farm_net01/7.wav', 0, 16000, 16200, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (10, 'net01', 'net01008', 1, '8.wav', 'positive/farm_net01/8.wav', 0, 16000, 16572, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (11, 'net01', 'net01009', 1, '9.wav', 'positive/farm_net01/9.wav', 0, 16000, 16144, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (12, 'net01', 'net01010', 1, '10.wav', 'positive/farm_net01/10.wav', 0, 16000, 16144, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (13, 'net01', 'net01011', 1, '11.wav', 'positive/farm_net01/11.wav', 0, 16000, 16144, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (14, 'net01', 'net01012', 1, '12.wav', 'positive/farm_net01/12.wav', 0, 16000, 16112, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (15, 'net01', 'net01013', 1, '13.wav', 'positive/farm_net01/13.wav', 0, 16000, 16274, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (16, 'net01', 'net01014', 1, '14.wav', 'positive/farm_net01/14.wav', 0, 16000, 16194, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (17, 'net01', 'net01015', 1, '15.wav', 'positive/farm_net01/15.wav', 0, 16000, 16074, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (18, 'net01', 'net01016', 1, '16.wav', 'positive/farm_net01/16.wav', 0, 16000, 16154, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (19, 'net01', 'net01017', 1, '17.wav', 'positive/farm_net01/17.wav', 0, 16000, 16154, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (20, 'net01', 'net01018', 1, '18.wav', 'positive/farm_net01/18.wav', 0, 16000, 16164, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (21, 'net01', 'net01019', 1, '19.wav', 'positive/farm_net01/19.wav', 0, 16000, 16164, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (22, 'net01', 'net01020', 1, '20.wav', 'positive/farm_net01/20.wav', 0, 16000, 16164, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (23, 'net01', 'net01021', 1, '21.wav', 'positive/farm_net01/21.wav', 0, 16000, 16126, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (24, 'net01', 'net01022', 1, '22.wav', 'positive/farm_net01/22.wav', 0, 16000, 16096, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (25, 'net01', 'net01023', 1, '23.wav', 'positive/farm_net01/23.wav', 0, 16000, 16096, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (26, 'net01', 'net01024', 1, '24.wav', 'positive/farm_net01/24.wav', 0, 16000, 17034, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (27, 'net01', 'net01025', 1, '25.wav', 'positive/farm_net01/25.wav', 0, 16000, 16096, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (28, 'net01', 'net01026', 1, '26.wav', 'positive/farm_net01/26.wav', 0, 16000, 16070, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (29, 'net01', 'net01027', 1, '27.wav', 'positive/farm_net01/27.wav', 0, 16000, 16182, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (30, 'net01', 'net01028', 1, '28.wav', 'positive/farm_net01/28.wav', 0, 16000, 16130, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (31, 'net01', 'net01029', 1, '29.wav', 'positive/farm_net01/29.wav', 0, 16000, 16162, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (32, 'net01', 'net01030', 1, '30.wav', 'positive/farm_net01/30.wav', 0, 16000, 16180, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (33, 'net01', 'net01031', 1, '31.wav', 'positive/farm_net01/31.wav', 0, 16000, 16124, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (34, 'net01', 'net01032', 1, '32.wav', 'positive/farm_net01/32.wav', 0, 16000, 16096, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (35, 'net01', 'net01033', 1, '33.wav', 'positive/farm_net01/33.wav', 0, 16000, 16124, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (36, 'net01', 'net01034', 1, '34.wav', 'positive/farm_net01/34.wav', 0, 16000, 16124, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (37, 'net01', 'net01035', 1, '35.wav', 'positive/farm_net01/35.wav', 0, 16000, 16082, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (38, 'net01', 'net01036', 1, '36.wav', 'positive/farm_net01/36.wav', 0, 16000, 16104, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (39, 'net01', 'net01037', 1, '37.wav', 'positive/farm_net01/37.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (40, 'net01', 'net01038', 1, '38.wav', 'positive/farm_net01/38.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (41, 'net01', 'net01039', 1, '39.wav', 'positive/farm_net01/39.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (42, 'net01', 'net01040', 1, '40.wav', 'positive/farm_net01/40.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (43, 'net01', 'net01041', 1, '41.wav', 'positive/farm_net01/41.wav', 0, 16000, 16096, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (44, 'net01', 'net01042', 1, '42.wav', 'positive/farm_net01/42.wav', 0, 16000, 16096, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (45, 'net01', 'net01043', 1, '43.wav', 'positive/farm_net01/43.wav', 0, 16000, 16154, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (46, 'net01', 'net01044', 1, '44.wav', 'positive/farm_net01/44.wav', 0, 16000, 16154, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (47, 'net01', 'net01045', 1, '45.wav', 'positive/farm_net01/45.wav', 0, 16000, 16114, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (48, 'net01', 'net01046', 1, '46.wav', 'positive/farm_net01/46.wav', 0, 16000, 16108, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (49, 'net01', 'net01047', 1, '47.wav', 'positive/farm_net01/47.wav', 0, 16000, 16090, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (50, 'net01', 'net01048', 1, '48.wav', 'positive/farm_net01/48.wav', 0, 16000, 16196, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (51, 'net01', 'net01049', 1, '49.wav', 'positive/farm_net01/49.wav', 0, 16000, 16196, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (52, 'net01', 'net01050', 1, '50.wav', 'positive/farm_net01/50.wav', 0, 16000, 16154, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (53, 'net01', 'net01051', 1, '51.wav', 'positive/farm_net01/51.wav', 0, 16000, 16108, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (54, 'net01', 'net01052', 1, '52.wav', 'positive/farm_net01/52.wav', 0, 16000, 16088, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (55, 'net01', 'net01053', 1, '53.wav', 'positive/farm_net01/53.wav', 0, 16000, 16114, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (56, 'net01', 'net01054', 1, '54.wav', 'positive/farm_net01/54.wav', 0, 16000, 16080, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (57, 'net01', 'net01055', 1, '55.wav', 'positive/farm_net01/55.wav', 0, 16000, 16090, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (58, 'net01', 'net01056', 1, '56.wav', 'positive/farm_net01/56.wav', 0, 16000, 16100, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (59, 'net01', 'net01057', 1, '57.wav', 'positive/farm_net01/57.wav', 0, 16000, 16548, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (60, 'net01', 'net01058', 1, '58.wav', 'positive/farm_net01/58.wav', 0, 16000, 16136, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (61, 'net01', 'net01059', 1, '59.wav', 'positive/farm_net01/59.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (62, 'net01', 'net01060', 1, '60.wav', 'positive/farm_net01/60.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (63, 'net01', 'net01061', 1, '61.wav', 'positive/farm_net01/61.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (64, 'net01', 'net01062', 1, '62.wav', 'positive/farm_net01/62.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (65, 'net01', 'net01063', 1, '63.wav', 'positive/farm_net01/63.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (66, 'net01', 'net01064', 1, '64.wav', 'positive/farm_net01/64.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (67, 'net01', 'net01065', 1, '65.wav', 'positive/farm_net01/65.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (68, 'net01', 'net01066', 1, '66.wav', 'positive/farm_net01/66.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (69, 'net01', 'net01067', 1, '67.wav', 'positive/farm_net01/67.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (70, 'net01', 'net01068', 1, '68.wav', 'positive/farm_net01/68.wav', 0, 16000, 16548, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (71, 'net01', 'net01069', 1, '69.wav', 'positive/farm_net01/69.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (72, 'net01', 'net01070', 1, '70.wav', 'positive/farm_net01/70.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (73, 'net01', 'net01071', 1, '71.wav', 'positive/farm_net01/71.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (74, 'net01', 'net01072', 1, '72.wav', 'positive/farm_net01/72.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (75, 'net01', 'net01073', 1, '73.wav', 'positive/farm_net01/73.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (76, 'net01', 'net01074', 1, '74.wav', 'positive/farm_net01/74.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (77, 'net01', 'net01075', 1, '75.wav', 'positive/farm_net01/75.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (78, 'net01', 'net01076', 1, '76.wav', 'positive/farm_net01/76.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (79, 'net01', 'net01077', 1, '77.wav', 'positive/farm_net01/77.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (80, 'net01', 'net01078', 1, '78.wav', 'positive/farm_net01/78.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (81, 'net01', 'net01079', 1, '79.wav', 'positive/farm_net01/79.wav', 0, 16000, 16174, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (82, 'net01', 'net01080', 1, '80.wav', 'positive/farm_net01/80.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (83, 'net01', 'net01081', 1, '81.wav', 'positive/farm_net01/81.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (84, 'net01', 'net01082', 1, '82.wav', 'positive/farm_net01/82.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (85, 'net01', 'net01083', 1, '83.wav', 'positive/farm_net01/83.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (86, 'net01', 'net01084', 1, '84.wav', 'positive/farm_net01/84.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (87, 'net01', 'net01085', 1, '85.wav', 'positive/farm_net01/85.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (88, 'net01', 'net01086', 1, '86.wav', 'positive/farm_net01/86.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (89, 'net01', 'net01087', 1, '87.wav', 'positive/farm_net01/87.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (90, 'net01', 'net01088', 1, '88.wav', 'positive/farm_net01/88.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (91, 'net01', 'net01089', 1, '89.wav', 'positive/farm_net01/89.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (92, 'net01', 'net01090', 1, '90.wav', 'positive/farm_net01/90.wav', 0, 16000, 16556, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (93, 'net01', 'net01091', 1, '91.wav', 'positive/farm_net01/91.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (94, 'net01', 'net01092', 1, '92.wav', 'positive/farm_net01/92.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (95, 'net01', 'net01093', 1, '93.wav', 'positive/farm_net01/93.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (96, 'net01', 'net01094', 1, '94.wav', 'positive/farm_net01/94.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (97, 'net01', 'net01095', 1, '95.wav', 'positive/farm_net01/95.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (98, 'net01', 'net01096', 1, '96.wav', 'positive/farm_net01/96.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (99, 'net01', 'net01097', 1, '97.wav', 'positive/farm_net01/97.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (100, 'net01', 'net01098', 1, '98.wav', 'positive/farm_net01/98.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (101, 'net01', 'net01099', 1, '99.wav', 'positive/farm_net01/99.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (102, 'net01', 'net01100', 1, '100.wav', 'positive/farm_net01/100.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 20:52:53', '2026-08-11 20:52:53');
INSERT INTO `audio_sample` VALUES (203, 'net01', 'net01101', 0, '1.wav', 'negative/farm_net01/1.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (204, 'net01', 'net01102', 0, '2.wav', 'negative/farm_net01/2.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (205, 'net01', 'net01103', 0, '3.wav', 'negative/farm_net01/3.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (206, 'net01', 'net01104', 0, '4.wav', 'negative/farm_net01/4.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (207, 'net01', 'net01105', 0, '5.wav', 'negative/farm_net01/5.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (208, 'net01', 'net01106', 0, '6.wav', 'negative/farm_net01/6.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (209, 'net01', 'net01107', 0, '7.wav', 'negative/farm_net01/7.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (210, 'net01', 'net01108', 0, '8.wav', 'negative/farm_net01/8.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (211, 'net01', 'net01109', 0, '9.wav', 'negative/farm_net01/9.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (212, 'net01', 'net01110', 0, '10.wav', 'negative/farm_net01/10.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (213, 'net01', 'net01111', 0, '11.wav', 'negative/farm_net01/11.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (214, 'net01', 'net01112', 0, '12.wav', 'negative/farm_net01/12.wav', 0, 16000, 15116, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (215, 'net01', 'net01113', 0, '13.wav', 'negative/farm_net01/13.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (216, 'net01', 'net01114', 0, '14.wav', 'negative/farm_net01/14.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (217, 'net01', 'net01115', 0, '15.wav', 'negative/farm_net01/15.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (218, 'net01', 'net01116', 0, '16.wav', 'negative/farm_net01/16.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (219, 'net01', 'net01117', 0, '17.wav', 'negative/farm_net01/17.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (220, 'net01', 'net01118', 0, '18.wav', 'negative/farm_net01/18.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (221, 'net01', 'net01119', 0, '19.wav', 'negative/farm_net01/19.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (222, 'net01', 'net01120', 0, '20.wav', 'negative/farm_net01/20.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (223, 'net01', 'net01121', 0, '21.wav', 'negative/farm_net01/21.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (224, 'net01', 'net01122', 0, '22.wav', 'negative/farm_net01/22.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (225, 'net01', 'net01123', 0, '23.wav', 'negative/farm_net01/23.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (226, 'net01', 'net01124', 0, '24.wav', 'negative/farm_net01/24.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (227, 'net01', 'net01125', 0, '25.wav', 'negative/farm_net01/25.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (228, 'net01', 'net01126', 0, '26.wav', 'negative/farm_net01/26.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (229, 'net01', 'net01127', 0, '27.wav', 'negative/farm_net01/27.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (230, 'net01', 'net01128', 0, '28.wav', 'negative/farm_net01/28.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (231, 'net01', 'net01129', 0, '29.wav', 'negative/farm_net01/29.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (232, 'net01', 'net01130', 0, '30.wav', 'negative/farm_net01/30.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (233, 'net01', 'net01131', 0, '31.wav', 'negative/farm_net01/31.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (234, 'net01', 'net01132', 0, '32.wav', 'negative/farm_net01/32.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (235, 'net01', 'net01133', 0, '33.wav', 'negative/farm_net01/33.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (236, 'net01', 'net01134', 0, '34.wav', 'negative/farm_net01/34.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (237, 'net01', 'net01135', 0, '35.wav', 'negative/farm_net01/35.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (238, 'net01', 'net01136', 0, '36.wav', 'negative/farm_net01/36.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (239, 'net01', 'net01137', 0, '37.wav', 'negative/farm_net01/37.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (240, 'net01', 'net01138', 0, '38.wav', 'negative/farm_net01/38.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (241, 'net01', 'net01139', 0, '39.wav', 'negative/farm_net01/39.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (242, 'net01', 'net01140', 0, '40.wav', 'negative/farm_net01/40.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (243, 'net01', 'net01141', 0, '41.wav', 'negative/farm_net01/41.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (244, 'net01', 'net01142', 0, '42.wav', 'negative/farm_net01/42.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (245, 'net01', 'net01143', 0, '43.wav', 'negative/farm_net01/43.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (246, 'net01', 'net01144', 0, '44.wav', 'negative/farm_net01/44.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (247, 'net01', 'net01145', 0, '45.wav', 'negative/farm_net01/45.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (248, 'net01', 'net01146', 0, '46.wav', 'negative/farm_net01/46.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (249, 'net01', 'net01147', 0, '47.wav', 'negative/farm_net01/47.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (250, 'net01', 'net01148', 0, '48.wav', 'negative/farm_net01/48.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (251, 'net01', 'net01149', 0, '49.wav', 'negative/farm_net01/49.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (252, 'net01', 'net01150', 0, '50.wav', 'negative/farm_net01/50.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (253, 'net01', 'net01151', 0, '51.wav', 'negative/farm_net01/51.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (254, 'net01', 'net01152', 0, '52.wav', 'negative/farm_net01/52.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (255, 'net01', 'net01153', 0, '53.wav', 'negative/farm_net01/53.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (256, 'net01', 'net01154', 0, '54.wav', 'negative/farm_net01/54.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (257, 'net01', 'net01155', 0, '55.wav', 'negative/farm_net01/55.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (258, 'net01', 'net01156', 0, '56.wav', 'negative/farm_net01/56.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (259, 'net01', 'net01157', 0, '57.wav', 'negative/farm_net01/57.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (260, 'net01', 'net01158', 0, '58.wav', 'negative/farm_net01/58.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (261, 'net01', 'net01159', 0, '59.wav', 'negative/farm_net01/59.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (262, 'net01', 'net01160', 0, '60.wav', 'negative/farm_net01/60.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (263, 'net01', 'net01161', 0, '61.wav', 'negative/farm_net01/61.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (264, 'net01', 'net01162', 0, '62.wav', 'negative/farm_net01/62.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (265, 'net01', 'net01163', 0, '63.wav', 'negative/farm_net01/63.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (266, 'net01', 'net01164', 0, '64.wav', 'negative/farm_net01/64.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (267, 'net01', 'net01165', 0, '65.wav', 'negative/farm_net01/65.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (268, 'net01', 'net01166', 0, '66.wav', 'negative/farm_net01/66.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (269, 'net01', 'net01167', 0, '67.wav', 'negative/farm_net01/67.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (270, 'net01', 'net01168', 0, '68.wav', 'negative/farm_net01/68.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (271, 'net01', 'net01169', 0, '69.wav', 'negative/farm_net01/69.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (272, 'net01', 'net01170', 0, '70.wav', 'negative/farm_net01/70.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (273, 'net01', 'net01171', 0, '71.wav', 'negative/farm_net01/71.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (274, 'net01', 'net01172', 0, '72.wav', 'negative/farm_net01/72.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (275, 'net01', 'net01173', 0, '73.wav', 'negative/farm_net01/73.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (276, 'net01', 'net01174', 0, '74.wav', 'negative/farm_net01/74.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (277, 'net01', 'net01175', 0, '75.wav', 'negative/farm_net01/75.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (278, 'net01', 'net01176', 0, '76.wav', 'negative/farm_net01/76.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (279, 'net01', 'net01177', 0, '77.wav', 'negative/farm_net01/77.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (280, 'net01', 'net01178', 0, '78.wav', 'negative/farm_net01/78.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (281, 'net01', 'net01179', 0, '79.wav', 'negative/farm_net01/79.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (282, 'net01', 'net01180', 0, '80.wav', 'negative/farm_net01/80.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (283, 'net01', 'net01181', 0, '81.wav', 'negative/farm_net01/81.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (284, 'net01', 'net01182', 0, '82.wav', 'negative/farm_net01/82.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (285, 'net01', 'net01183', 0, '83.wav', 'negative/farm_net01/83.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (286, 'net01', 'net01184', 0, '84.wav', 'negative/farm_net01/84.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (287, 'net01', 'net01185', 0, '85.wav', 'negative/farm_net01/85.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (288, 'net01', 'net01186', 0, '86.wav', 'negative/farm_net01/86.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (289, 'net01', 'net01187', 0, '87.wav', 'negative/farm_net01/87.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (290, 'net01', 'net01188', 0, '88.wav', 'negative/farm_net01/88.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (291, 'net01', 'net01189', 0, '89.wav', 'negative/farm_net01/89.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (292, 'net01', 'net01190', 0, '90.wav', 'negative/farm_net01/90.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (293, 'net01', 'net01191', 0, '91.wav', 'negative/farm_net01/91.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (294, 'net01', 'net01192', 0, '92.wav', 'negative/farm_net01/92.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (295, 'net01', 'net01193', 0, '93.wav', 'negative/farm_net01/93.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (296, 'net01', 'net01194', 0, '94.wav', 'negative/farm_net01/94.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (297, 'net01', 'net01195', 0, '95.wav', 'negative/farm_net01/95.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (298, 'net01', 'net01196', 0, '96.wav', 'negative/farm_net01/96.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (299, 'net01', 'net01197', 0, '97.wav', 'negative/farm_net01/97.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (300, 'net01', 'net01198', 0, '98.wav', 'negative/farm_net01/98.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (301, 'net01', 'net01199', 0, '99.wav', 'negative/farm_net01/99.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');
INSERT INTO `audio_sample` VALUES (302, 'net01', 'net01200', 0, '100.wav', 'negative/farm_net01/100.wav', 0, 16000, 16078, '2026-08-11 00:00:00', 'gy', 0, '2026-08-11 21:07:44', '2026-08-11 21:07:44');

-- ----------------------------
-- Table structure for dataset_stat
-- ----------------------------
DROP TABLE IF EXISTS `dataset_stat`;
CREATE TABLE `dataset_stat`  (
  `stat_id` int NOT NULL AUTO_INCREMENT,
  `stat_date` date NOT NULL COMMENT '统计日期',
  `total_pos` int NOT NULL COMMENT '总正样本',
  `total_neg` int NOT NULL COMMENT '总负样本',
  `train_pos` int NULL DEFAULT NULL,
  `train_neg` int NULL DEFAULT NULL,
  `val_pos` int NULL DEFAULT NULL,
  `val_neg` int NULL DEFAULT NULL,
  `test_pos` int NULL DEFAULT NULL,
  `test_neg` int NULL DEFAULT NULL,
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '样本均衡备注',
  PRIMARY KEY (`stat_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '数据集均衡统计记录表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of dataset_stat
-- ----------------------------
INSERT INTO `dataset_stat` VALUES (1, '2026-08-11', 100, 100, 0, 0, 0, 0, 0, 0, '无');

SET FOREIGN_KEY_CHECKS = 1;
