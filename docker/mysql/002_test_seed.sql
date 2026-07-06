INSERT INTO ums_member (
  id, member_level_id, username, password, nickname, phone, status,
  create_time, gender, city, job, personalized_signature,
  integration, growth
) VALUES
  (9001, 4, 'autotest_a', '$2a$10$NZ5o7r2E.ayT2ZoxgjlI.eJ6OEYqjH7INR/F.mXDbjZJi9HF0YCVG',
   'autotest_a', '19900009001', 1, NOW(), 1, '深圳', 'QA', 'API automation user A', 5000, 1000),
  (9002, 4, 'autotest_b', '$2a$10$NZ5o7r2E.ayT2ZoxgjlI.eJ6OEYqjH7INR/F.mXDbjZJi9HF0YCVG',
   'autotest_b', '19900009002', 1, NOW(), 1, '深圳', 'QA', 'API automation user B', 5000, 1000)
ON DUPLICATE KEY UPDATE
  password = VALUES(password), status = 1, integration = 5000, growth = 1000;

INSERT INTO ums_member_receive_address (
  id, member_id, name, phone_number, default_status, post_code,
  province, city, region, detail_address
) VALUES
  (9001, 9001, '自动化用户A', '19900009001', 1, '518000', '广东省', '深圳市', '南山区', '测试地址A'),
  (9002, 9002, '自动化用户B', '19900009002', 1, '518000', '广东省', '深圳市', '福田区', '测试地址B')
ON DUPLICATE KEY UPDATE
  member_id = VALUES(member_id), default_status = 1;

UPDATE pms_product
SET name = 'AUTOTEST_PRODUCT_P20', publish_status = 1, delete_status = 0
WHERE id = 26;

UPDATE pms_sku_stock
SET stock = 500, lock_stock = 0
WHERE id = 110;
