# Trade 数据库 Schema

## 表结构

### 1. companies — 公司（多租户根实体）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| name | TEXT NOT NULL | 公司名称 |
| slug | TEXT UNIQUE NOT NULL | URL 标识（自动生成） |
| logo_url | TEXT | 公司 logo |
| website | TEXT | 公司网站 |
| contact_name | TEXT | 统一联系人 |
| contact_email | TEXT | 统一邮箱 |
| address | TEXT | 地址 |
| is_active | INTEGER DEFAULT 1 | 1=激活, 0=停用（软删除，`list_all()` 仅返回 `is_active=1`） |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |
| extra1 | TEXT (JSON) | {"industry":"", "country":"", ...} |
| extra2 | TEXT (JSON) | {"employee_count":"", "annual_revenue":"", ...} |
| extra3 | TEXT (JSON) | 备用扩展 |

### 2. trade_companies — Trade 系统配置

| 列名 | 类型 | 说明 |
|------|------|------|
| company_id | INTEGER PK (FK→companies) | 关联公司 |
| data_dir | TEXT NOT NULL | 数据目录 `~/.trade/{slug}/` |
| agent_identity_md | TEXT | Agent 身份文本（在线编辑） |
| is_active | INTEGER DEFAULT 1 | 1=激活会话 |
| created_at | TEXT | 创建时间 |
| extra1 | TEXT (JSON) | {"max_iterations":90, "temperature":0.7, ...} |
| extra2 | TEXT (JSON) | {"model":"", "provider":"", ...} |
| extra3 | TEXT (JSON) | 备用扩展 |
| license_data | TEXT (JSON) | {"first_launch_at":"","activated":false,"expires_at":null} |

### 3. libraries — 文档库

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| company_id | INTEGER (FK→companies) | 所属公司 |
| name | TEXT NOT NULL | 库名称 |
| root_path | TEXT NOT NULL | 本地目录路径 |
| description | TEXT | 描述 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |
| extra1 | TEXT (JSON) | {"scan_depth":3, "file_count":0, "last_scan":""} |
| extra2 | TEXT (JSON) | {"indexed":false, "index_version":1} |
| extra3 | TEXT (JSON) | 备用扩展 |

### 4. customers — 客户

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| company_id | INTEGER (FK→companies) | 所属公司 |
| name | TEXT NOT NULL | 公司名称 |
| contact | TEXT | 联系人姓名 |
| note | TEXT | 备注 / 跟进项目 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |
| extra1 | TEXT (JSON) | {"country":"", "tier":"A/B/C", "linkedin_url":"", "company_website":"", "social_media":{}} |
| extra2 | TEXT (JSON) | {"title":"", "email":"", "backup_email":"", "phone":"", "whatsapp":"", "source":"", "last_contact_at":""} |
| extra3 | TEXT (JSON) | 备用扩展 |

### 5. customer_libraries — 客户↔文档库关联

| 列名 | 类型 | 说明 |
|------|------|------|
| customer_id | INTEGER (FK→customers) | 客户 ID |
| library_id | INTEGER (FK→libraries) | 文档库 ID |
| extra1 | TEXT (JSON) | {"relevance_score":0.0, "notes":""} |
| extra2 | TEXT (JSON) | 备用扩展 |
| extra3 | TEXT (JSON) | 备用扩展 |
| | | **PRIMARY KEY (customer_id, library_id)** |

### 6. conversations — 对话记录

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| company_id | INTEGER (FK→companies) | 所属公司 |
| library_id | INTEGER (FK→libraries) | 关联文档库（可空） |
| query | TEXT NOT NULL | 用户问题 |
| response | TEXT | AI 回复 |
| files_read | TEXT (JSON) | [{"file":"...","pages":[1,2]}] |
| created_at | TEXT | 创建时间 |
| extra1 | TEXT (JSON) | {"tokens_used":0, "model":"", "duration_ms":0} |
| extra2 | TEXT (JSON) | {"rating":null, "feedback":""} |
| extra3 | TEXT (JSON) | {"tools_used":[], "iterations":0} |

### 7. orders — 订单

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| company_id | INTEGER (FK→companies) | 所属公司 |
| customer_id | INTEGER (FK→customers) | 关联客户 |
| order_no | TEXT | 订单号（自定义） |
| product_name | TEXT NOT NULL | 品名 |
| quantity | REAL CHECK(quantity >= 0) | 数量（不允许负数） |
| unit | TEXT | 单位（套/米/吨） |
| unit_price | REAL CHECK(unit_price >= 0) | 单价（不允许负数） |
| currency | TEXT DEFAULT 'USD' | 币种 |
| total_amount | REAL CHECK(total_amount >= 0) | 总金额（不允许负数） |
| status | TEXT DEFAULT '报价中' | 报价中/已下单/已出货/已完成 |
| delivery_date | TEXT | 交期 |
| payment_terms | TEXT | 付款方式 |
| notes | TEXT | 备注 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### 8. order_libraries — 订单↔文档库关联

| 列名 | 类型 | 说明 |
|------|------|------|
| order_id | INTEGER (FK→orders) | 订单 ID |
| library_id | INTEGER (FK→libraries) | 文档库 ID |
| | | **PRIMARY KEY (order_id, library_id)** |

## 索引

| 索引名 | 表 | 列 |
|--------|-----|-----|
| idx_libraries_company | libraries | company_id |
| idx_customers_company | customers | company_id |
| idx_orders_company | orders | company_id |
| idx_orders_customer | orders | customer_id |
| idx_conversations_company | conversations | company_id |
| idx_conversations_library | conversations | library_id |
| idx_conversations_created | conversations | created_at |

## 外键关系

```
companies
  ├── trade_companies (1:1)
  ├── libraries (1:N, CASCADE)
  ├── customers (1:N, CASCADE)
  ├── conversations (1:N, CASCADE)
  └── orders (1:N, CASCADE)

customers
  ├── customer_libraries (N:M → libraries)
  └── orders (1:N, CASCADE)

orders
  └── order_libraries (N:M → libraries)

libraries
  ├── customer_libraries (N:M → customers)
  ├── order_libraries (N:M → orders)
  └── conversations (1:N, SET NULL)
```
