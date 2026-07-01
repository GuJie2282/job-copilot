# [功能名称] 功能设计文档

## 📋 文档信息

| 字段         | 内容                       |
|--------------|----------------------------|
| 功能名称     | [例如：任务单批量签名]     |
| 功能模块     | [例如：tz-module-pressure] |
| 版本号       | v1.0                       |
| 创建日期     | 2025-01-07                 |
| 创建人       | XXX                        |
| 最后更新     | 2025-01-07                 |
| 文档状态     | 设计中/开发中/已完成       |

---

## 📑 变更历史

| 版本号 | 时间       | 修改内容           | 修改人   | 审核人   |
|--------|------------|--------------------|----------|----------|
| v1.0   | 2025-01-07 | 初稿               | XXX      | XXX      |
| v1.1   | 2025-01-08 | 新增XXX功能        | XXX      | XXX      |

---

## 目录

1. [功能概述](#1-功能概述)
2. [需求分析](#2-需求分析)
3. [业务流程](#3-业务流程)
4. [系统设计](#4-系统设计)
5. [数据库设计](#5-数据库设计)
6. [接口设计](#6-接口设计)
7. [核心代码实现](#7-核心代码实现)
8. [技术方案](#8-技术方案)
9. [异常处理](#9-异常处理)
10. [性能优化](#10-性能优化)
11. [测试方案](#11-测试方案)
12. [部署说明](#12-部署说明)
13. [影响分析](#13-影响分析)
14. [后续扩展](#14-后续扩展)
15. [附录](#15-附录)

---

## 1. 功能概述

### 1.1 功能背景

**业务背景**:
描述为什么要做这个功能，解决什么业务问题。

例如：
- 当前业务场景中，检验员需要手动对多个报告进行签名，效率低下
- 客户要求提升批量操作的效率，减少重复工作
- 需要与Grape City文档服务集成，实现自动化签名

### 1.2 功能目标

**主要目标**:
1. 支持批量选择多个报告进行签名
2. 与Grape City服务集成，自动完成签名流程
3. 提供详细的签名结果反馈
4. 保证签名过程的事务性和数据一致性

**次要目标**:
- 提供签名日志记录
- 支持签名状态查询
- 支持签名撤销（如果需要）

### 1.3 功能范围

**包含**:
- ✅ 批量报告签名接口
- ✅ 签名状态查询接口
- ✅ 签名日志记录
- ✅ 与Grape City集成

**不包含**:
- ❌ 单个报告签名（已有功能）
- ❌ 签名撤销（未来版本）
- ❌ 签名模板管理（其他模块）

### 1.4 用户角色

| 角色     | 职责                       | 权限                                   |
|----------|----------------------------|----------------------------------------|
| 检验员   | 提交批量签名请求           | 可对自己负责的报告进行签名             |
| 审核员   | 审核签名结果               | 可查看所有签名记录                     |
| 管理员   | 配置签名参数               | 可管理签名配置、查看所有签名记录       |

---

## 2. 需求分析

### 2.1 功能需求

#### FR-01 批量签名功能
**优先级**: P0 (必须有)

**需求描述**:
用户可以选择多个报告（最多100个），一次性提交签名请求，系统自动调用Grape City服务完成签名。

**验收标准**:
- [ ] 支持选择1-100个报告
- [ ] 超过100个报告时，前端提示并拦截
- [ ] 签名成功后更新报告状态
- [ ] 返回详细的签名结果（成功/失败列表）

#### FR-02 签名状态查询
**优先级**: P1 (应该有)

**需求描述**:
用户可以查询报告的签名状态（未签名/签名中/已签名/签名失败）。

**验收标准**:
- [ ] 提供查询接口
- [ ] 显示签名时间、签名人
- [ ] 签名失败时显示失败原因

#### FR-03 签名日志
**优先级**: P1 (应该有)

**需求描述**:
记录所有签名操作的日志，包括操作人、操作时间、操作结果。

**验收标准**:
- [ ] 日志记录到数据库
- [ ] 提供日志查询接口
- [ ] 日志包含详细的请求和响应信息

### 2.2 非功能需求

#### NFR-01 性能需求
- 批量签名100个报告，响应时间 < 30秒
- 并发签名请求支持 ≥ 10个/秒

#### NFR-02 安全需求
- 签名操作需要鉴权
- 签名日志不可篡改
- 与Grape City通信使用加密传输

#### NFR-03 可用性需求
- 系统可用性 ≥ 99.5%
- Grape City服务故障时，系统应优雅降级

### 2.3 业务约束

1. 只有报告状态为"待签名"的报告才能签名
2. 报告必须有完整的检验数据才能签名
3. 签名操作不可逆（一旦签名成功，不能撤销）
4. 签名失败不影响其他报告的签名流程

---

## 3. 业务流程

### 3.1 正常流程

```
┌─────────┐     ┌─────────┐     ┌─────────────┐     ┌─────────┐     ┌─────────┐
│ 前端用户 │ ──▶ │ 检验员  │ ──▶ │ 批量签名接口 │ ──▶ │ Grape   │ ──▶ │ 签名完成 │
└─────────┘     └─────────┘     └─────────────┘     └─────────┘     └─────────┘
                     │                  │                    │
                     │                  ▼                    │
                     │         ┌─────────────┐              │
                     │         │ 数据校验     │              │
                     │         │ 状态检查     │              │
                     │         │ 权限验证     │              │
                     │         └─────────────┘              │
                     │                  │                    │
                     │                  ▼                    │
                     │         ┌─────────────┐              │
                     │         │ 并发签名     │              │
                     │         │ 结果收集     │              │
                     │         └─────────────┘              │
                     │                  │                    │
                     │                  ▼                    │
                     │         ┌─────────────┐              │
                     │         │ 更新状态     │              │
                     │         │ 记录日志     │              │
                     │         └─────────────┘              │
                     │                  │                    │
                     ▼                  ▼                    ▼
              ┌────────────────────────────────────────────┐
              │          返回签名结果给前端                 │
              │  - totalCount, successCount, failCount     │
              │  - successItems[], failedItems[]           │
              └────────────────────────────────────────────┘
```

### 3.2 异常流程

#### 场景1: 报告不存在
```
用户提交签名请求 → 数据校验失败 → 返回错误"报告不存在"
```

#### 场景2: 报告状态不允许签名
```
用户提交签名请求 → 状态检查失败（已签名/已作废）→ 返回错误"报告状态不允许签名"
```

#### 场景3: Grape City服务超时
```
用户提交签名请求 → 调用Grape City → 超时 → 记录失败日志 → 继续处理其他报告
```

#### 场景4: 部分报告签名失败
```
用户提交签名请求 → 部分成功/部分失败 → 返回详细结果 → 前端展示失败列表
```

### 3.3 状态机

```
┌──────────┐   检验完成   ┌──────────┐   签名成功   ┌──────────┐
│  草稿    │ ──────────▶ │ 待签名    │ ──────────▶ │  已签名  │
└──────────┘             └──────────┘             └──────────┘
                            │   ▲
                            │   │ 签名失败
                            │   └──────────┐
                            ▼              │
                       ┌──────────┐       │
                       │ 签名失败  │ ◀─────┘
                       └──────────┘
```

**状态说明**:

| 状态码     | 状态文本 | 说明                 | 可执行操作           |
|------------|----------|----------------------|----------------------|
| DRAFT      | 草稿     | 报告还在编辑中       | 编辑、提交检验       |
| INSPECTED  | 已检验   | 检验数据已录入       | 提交签名             |
| PENDING    | 待签名   | 等待签名             | 批量签名             |
| SIGNED     | 已签名   | 签名成功             | 查看、下载           |
| SIGN_FAIL  | 签名失败 | 签名失败             | 重新签名             |

---

## 4. 系统设计

### 4.1 架构设计

```
┌──────────────────────────────────────────────────────────────┐
│                         前端层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  列表页面    │  │  批量选择    │  │  结果展示    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                       Controller层                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  AppApiTaskOrderController                           │   │
│  │    - batchSign(List<OrderItemSignVO>)                │   │
│  │    - getSignStatus(String id)                        │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                        Service层                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  TaskOrderExpandService                              │   │
│  │    - batchSign() → BatchOperationRespVO              │   │
│  │       ├─ 数据校验                                     │   │
│  │       ├─ 并发签名                                     │   │
│  │       ├─ 结果收集                                     │   │
│  │       └─ 日志记录                                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                              │                                │
│                              ▼                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  TaskOrderItemReportService                          │   │
│  │    - signReport() → Boolean                          │   │
│  │    - updateSignStatus()                              │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                          外部服务                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Grape City Document Service                         │   │
│  │    - signDocument()                                  │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 模块划分

#### 4.2.1 Controller层
**职责**: 接收HTTP请求，参数校验，调用Service层

**主要类**:
- `AppApiTaskOrderController`: 处理签名相关请求
- `TaskOrderSignController`: Admin后台管理接口

#### 4.2.2 Service层
**职责**: 业务逻辑处理，事务管理

**主要类**:
- `TaskOrderExpandService`: 批量签名业务逻辑
- `TaskOrderItemReportService`: 单个报告签名逻辑
- `SignLogService`: 签名日志管理

#### 4.2.3 DAL层
**职责**: 数据访问，数据库操作

**主要类**:
- `TaskOrderItemReportMapper`: 报告数据访问
- `SignLogMapper`: 签名日志数据访问

### 4.3 类设计

#### 4.3.1 VO类

```java
// 批量签名请求VO
public class OrderItemSignVO {
    private String id;              // 报告ID（必填）
    private String orderItemId;     // 设备项ID（必填）
    private String signerName;      // 签名人（必填）
    private String signerCert;      // 签名证书（可选）
}

// 批量操作响应VO
public class BatchOperationRespVO {
    private Integer totalCount;          // 总数据量
    private Integer successCount;        // 成功数量
    private Integer failCount;           // 失败数量
    private Boolean allSuccess;          // 是否全部成功
    private String errorMessage;         // 错误消息
    private List<BatchOperationItemVO> successItems;  // 成功列表
    private List<BatchOperationItemVO> failedItems;   // 失败列表
}

// 批量操作单项VO
public class BatchOperationItemVO {
    private String id;               // ID
    private String reportName;       // 报告名称
    private Boolean success;         // 是否成功
    private String errorMessage;     // 错误消息
}
```

### 4.4 时序图

```
前端      Controller       Service       Grape City      数据库
 │            │              │               │              │
 │─批量签名请求▶│              │               │              │
 │            │              │               │              │
 │            │─数据校验─────▶│               │              │
 │            │              │               │              │
 │            │              │─查询报告─────────────────────▶│
 │            │              │◀────返回报告─────────────────│
 │            │              │               │              │
 │            │              │─并发签名──────▶│              │
 │            │              │               │              │
 │            │              │               │─签名文档────▶│
 │            │              │               │◀─返回结果────│
 │            │              │◀────返回结果──│              │
 │            │              │               │              │
 │            │              │─更新状态─────────────────────▶│
 │            │              │─记录日志─────────────────────▶│
 │            │◀─返回结果────│               │              │
 │◀─接收结果──│              │               │              │
```

---

## 5. 数据库设计

### 5.1 表结构（DM8数据库）

#### 5.1.1 tz_task_order_item_report (报告表)

**新增字段**:

| 字段名        | 类型    | 长度 | 允许空 | 说明           | 索引 |
|---------------|---------|------|--------|----------------|------|
| sign_status   | VARCHAR | 20   | Y      | 签名状态       |      |
| sign_time     | DATETIME| -    | Y      | 签名时间       |      |
| signer_name   | VARCHAR | 100  | Y      | 签名人         |      |
| sign_error    | VARCHAR | 500  | Y      | 签名错误信息   |      |

**新增索引**:
```sql
CREATE INDEX idx_sign_status ON tz_task_order_item_report(sign_status);
```

**状态枚举值**:
- `PENDING`: 待签名
- `SIGNING`: 签名中
- `SIGNED`: 已签名
- `SIGN_FAILED`: 签名失败

### 5.2 SQL变更脚本

```sql
-- 添加字段ALTER TABLE LABORATORY_BUSINESS_ACCEPTANCE_CIRCULATION_RECORD
ADD COLUMN SORT INT DEFAULT NULL;
COMMENT ON COLUMN LABORATORY_BUSINESS_ACCEPTANCE_CIRCULATION_RECORD.SORT IS '排序';
ALTER TABLE LABORATORY_BUSINESS_ACCEPTANCE_FEE
   ADD COLUMN CHECK_DATE DATE DEFAULT NULL;
COMMENT ON COLUMN LABORATORY_BUSINESS_ACCEPTANCE_FEE.CHECK_DATE IS '检验日期';
ALTER TABLE LABORATORY_BUSINESS_ACCEPTANCE
   ADD COLUMN SERVICE_ORDER_RECIPIENT_PHONE VARCHAR2(11) DEFAULT NULL;
COMMENT ON COLUMN LABORATORY_BUSINESS_ACCEPTANCE.SERVICE_ORDER_RECIPIENT_PHONE IS '服务单接收人员电话';
    
-- 创建表
CREATE TABLE LABORATORY_USER_ENTRUST_UNIT
(
   ID                 VARCHAR2(64)           NOT NULL,
   ENTRUST_UNIT       VARCHAR2(255)          NOT NULL,
   CONTACT            VARCHAR2(64)           NOT NULL,
   PHONE              VARCHAR2(32)           NOT NULL,
   REGISTERED_ADDRESS VARCHAR2(512),
   USER_ID            VARCHAR2(32),
   STATUS             VARCHAR2(2)  DEFAULT '0',
   CREATOR            VARCHAR2(64) DEFAULT '',
   CREATE_TIME        TIMESTAMP              NOT NULL DEFAULT SYSTIMESTAMP,
   UPDATER            VARCHAR2(64) DEFAULT '',
   UPDATE_TIME        TIMESTAMP              NOT NULL DEFAULT SYSTIMESTAMP,
   DELETED            NUMBER(1)    DEFAULT 0 NOT NULL,
   TENANT_ID          NUMBER(20)   DEFAULT 0 NOT NULL,
   PRIMARY KEY (ID)
);

-- 添加表注释
COMMENT ON TABLE LABORATORY_USER_ENTRUST_UNIT IS '实验室-用户委托单位信息表';
COMMENT ON COLUMN LABORATORY_USER_ENTRUST_UNIT.ID IS '主键';
COMMENT ON COLUMN LABORATORY_USER_ENTRUST_UNIT.ENTRUST_UNIT IS '委托单位';
COMMENT ON COLUMN LABORATORY_USER_ENTRUST_UNIT.CONTACT IS '联系人';
COMMENT ON COLUMN LABORATORY_USER_ENTRUST_UNIT.PHONE IS '电话';
COMMENT ON COLUMN LABORATORY_USER_ENTRUST_UNIT.REGISTERED_ADDRESS IS '注册地址';
COMMENT ON COLUMN LABORATORY_USER_ENTRUST_UNIT.USER_ID IS '用户ID';
COMMENT ON COLUMN LABORATORY_USER_ENTRUST_UNIT.STATUS IS '状态 0-待受理 1-已受理 2-已拒绝';
COMMENT ON COLUMN LABORATORY_USER_ENTRUST_UNIT.CREATOR IS '创建者';
COMMENT ON COLUMN LABORATORY_USER_ENTRUST_UNIT.CREATE_TIME IS '创建时间';
COMMENT ON COLUMN LABORATORY_USER_ENTRUST_UNIT.UPDATER IS '更新者';
COMMENT ON COLUMN LABORATORY_USER_ENTRUST_UNIT.UPDATE_TIME IS '更新时间';
COMMENT ON COLUMN LABORATORY_USER_ENTRUST_UNIT.DELETED IS '是否删除';
COMMENT ON COLUMN LABORATORY_USER_ENTRUST_UNIT.TENANT_ID IS '租户编号';

-- 创建索引
CREATE INDEX IDX_USER_ENTRUST_UNIT_USER_ID ON LABORATORY_USER_ENTRUST_UNIT (USER_ID);
```

---

## 6. 接口设计

### 6.1 批量签名接口

**接口地址**: `PUT /pressure/task-order/batch-sign`

**请求方法**: PUT

**请求参数**:
```json
[
  {
    "id": "report-id-001",
    "orderItemId": "item-id-001",
    "signerName": "张三",
    "signerCert": "cert-base64-string"
  },
  {
    "id": "report-id-002",
    "orderItemId": "item-id-002",
    "signerName": "张三",
    "signerCert": "cert-base64-string"
  }
]
```

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "totalCount": 2,
    "successCount": 2,
    "failCount": 0,
    "allSuccess": true,
    "successItems": [
      {
        "id": "report-id-001",
        "reportName": "压力容器检验报告-设备A",
        "success": true
      },
      {
        "id": "report-id-002",
        "reportName": "压力容器检验报告-设备B",
        "success": true
      }
    ],
    "failedItems": []
  },
  "msg": "操作成功"
}
```

**详细API文档**: 参见 [API接口文档模板](api-template.md)

---

## 7. 核心代码实现

### 7.1 Service层实现

#### 7.1.1 批量签名核心方法

**文件位置**: `tz-module-pressure/tz-module-pressure-biz/src/main/java/cn/start/tz/module/pressure/service/taskorder/TaskOrderExpandServiceImpl.java`

```java
@Override
public BatchOperationRespVO batchSign(List<OrderItemSignVO> signVOs) {
    log.info("[batchSign] 开始批量签名，共 {} 条数据", signVOs.size());

    // 1. 数据校验
    validateSignRequest(signVOs);

    // 2. 动态超时计算：每个报告最多2秒，最少30秒，最多300秒
    long timeoutSec = Math.min(Math.max(signVOs.size() * 2L, 30L), 300L);

    // 3. 使用线程池工具类并发执行签名
    ThreadPoolUtils.BatchResult result = ThreadPoolUtils.executeBatch(
        signVOs,
        this::signSingleReport,      // 方法引用：单个报告签名逻辑
        asyncExecutor,                // 自定义线程池
        timeoutSec                     // 超时时间
    );

    log.info("[batchSign] 批量签名完成，总数据: {}, 成功: {}, 失败: {}",
        result.getTotalCount(), result.getSuccessCount(), result.getFailCount());

    // 4. 返回结果
    return BatchOperationRespVO.success(
        result.getTotalCount(),
        result.getSuccessCount(),
        result.getFailCount()
    );
}

/**
 * 单个报告签名（方法引用）
 */
private void signSingleReport(OrderItemSignVO signVO) {
    // 1. 查询报告
    TaskOrderItemReportDO report = taskOrderItemReportMapper.selectById(signVO.getId());
    if (report == null) {
        throw exception(REPORT_NOT_EXISTS);
    }

    // 2. 状态检查
    if (!"PENDING".equals(report.getSignStatus())) {
        throw exception(REPORT_STATUS_ERROR);
    }

    // 3. 调用Grape City服务
    boolean signResult = grapeCityService.signDocument(
        report.getDataJson(),
        signVO.getSignerCert()
    );

    // 4. 更新状态
    if (signResult) {
        report.setSignStatus("SIGNED");
        report.setSignTime(new Date());
        report.setSignerName(signVO.getSignerName());
    } else {
        report.setSignStatus("SIGN_FAILED");
        report.setSignError("签名服务返回失败");
    }

    taskOrderItemReportMapper.updateById(report);

    // 5. 记录日志
    signLogService.log(report, signVO, signResult);
}

/**
 * 数据校验
 */
private void validateSignRequest(List<OrderItemSignVO> signVOs) {
    // 1. 数量校验
    if (signVOs == null || signVOs.isEmpty()) {
        throw exception(SIGN_LIST_EMPTY);
    }
    if (signVOs.size() > 100) {
        throw exception(SIGN_LIST_EXCEED_LIMIT);
    }

    // 2. 必填字段校验
    for (int i = 0; i < signVOs.size(); i++) {
        OrderItemSignVO vo = signVOs.get(i);
        if (StrUtil.isBlank(vo.getId())) {
            throw exception(new ErrorCode(400, "第" + (i+1) + "条数据的ID不能为空"));
        }
        if (StrUtil.isBlank(vo.getSignerName())) {
            throw exception(new ErrorCode(400, "第" + (i+1) + "条数据的签名人不能为空"));
        }
    }
}
```

### 7.2 线程池配置

**文件位置**: `tz-framework/tz-common/src/main/java/cn/start/tz/framework/common/util/concurrent/ThreadPoolConfig.java`

```java
@Bean("asyncExecutor")
public ThreadPoolTaskExecutor asyncExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    int cpuCore = Runtime.getRuntime().availableProcessors();

    executor.setCorePoolSize(cpuCore);              // 核心线程数 = CPU核心数
    executor.setMaxPoolSize(cpuCore * 2);           // 最大线程数 = CPU核心数 × 2
    executor.setQueueCapacity(200);                 // 队列容量
    executor.setKeepAliveSeconds(60);               // 空闲线程存活时间
    executor.setThreadNamePrefix("async-sign-");    // 线程名称前缀
    executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());

    executor.initialize();
    return executor;
}
```

### 7.3 工具类方法

**文件位置**: `tz-framework/tz-common/src/main/java/cn/start/tz/framework/common/util/concurrent/ThreadPoolUtils.java`

详见: [线程池工具类文档](../framework/tz-common/src/main/java/cn/start/tz/framework/common/util/concurrent/README.md)

---

## 8. 技术方案

### 8.1 并发处理方案

**方案选择**: CompletableFuture + 自定义线程池

**优势**:
- ✅ 异步非阻塞，提升性能
- ✅ 自动异常处理，单个失败不影响整体
- ✅ 可控制超时时间
- ✅ 自动统计结果

**性能对比**:

| 数据量 | 顺序处理 | 并发处理 | 提升倍数 |
|--------|----------|----------|----------|
| 10条   | 20秒     | 3秒      | 6.7x     |
| 50条   | 100秒    | 15秒     | 6.7x     |
| 100条  | 200秒    | 30秒     | 6.7x     |

### 8.2 事务处理方案

**方案**: 每个报告签名在独立事务中执行

**原因**:
- 批量操作中，单个失败不应影响其他报告
- 签名操作涉及外部服务，需要隔离性
- 便于错误恢复和重试

**实现**:
```java
@Transactional(propagation = Propagation.REQUIRES_NEW)
public void signSingleReport(OrderItemSignVO signVO) {
    // 签名逻辑
}
```

### 8.3 与Grape City集成方案

**方案**: Feign Client调用

**配置**:
```java
@FeignClient(name = "grape-city-service", url = "${grape.city.url}")
public interface GrapeCityServiceClient {
    @PostMapping("/api/document/sign")
    GrapeCitySignResult signDocument(@RequestBody SignRequest request);
}
```

**容错**:
- 超时时间: 5秒
- 重试次数: 1次
- 降级策略: 记录失败日志，继续处理其他报告

---

## 9. 异常处理

### 9.1 异常分类

| 异常类型             | 异常码   | 处理策略                       |
|----------------------|----------|--------------------------------|
| 报告不存在           | 404001   | 记录失败，不中断整体流程       |
| 报告状态不允许签名   | 400002   | 记录失败，不中断整体流程       |
| Grape City服务超时   | 500001   | 记录失败，不中断整体流程       |
| Grape City服务错误   | 500002   | 记录失败，不中断整体流程       |
| 数据库连接失败       | 500003   | 抛出异常，中断整体流程         |
| 参数校验失败         | 400001   | 前端拦截，不调用后端接口       |

### 9.2 异常处理流程

```
┌─────────────┐
│  发生异常    │
└──────┬──────┘
       │
       ▼
┌─────────────┐     是     ┌─────────────┐
│ 可恢复异常？ │────────────▶│ 记录失败日志 │
└──────┬──────┘             └─────────────┘
       │否                          │
       ▼                            ▼
┌─────────────┐              ┌─────────────┐
│ 抛出异常    │              │ 继续处理    │
│ 回滚事务    │              │ 其他报告    │
└─────────────┘              └─────────────┘
```

### 9.3 错误码定义

```java
public class ErrorCodeConstants {
    public static final ErrorCode REPORT_NOT_EXISTS = new ErrorCode(404001, "报告不存在");
    public static final ErrorCode REPORT_STATUS_ERROR = new ErrorCode(400002, "报告状态不允许签名");
    public static final ErrorCode SIGN_LIST_EMPTY = new ErrorCode(400003, "签名列表不能为空");
    public static final ErrorCode SIGN_LIST_EXCEED_LIMIT = new ErrorCode(400004, "签名列表超过100条");
    public static finalErrorCode GRAPE_CITY_TIMEOUT = new ErrorCode(500001, "Grape City服务超时");
    public static final ErrorCode GRAPE_CITY_ERROR = new ErrorCode(500002, "Grape City服务错误");
}
```

---

## 10. 性能优化

### 10.1 优化策略

#### 策略1: 并发处理
- **优化前**: 顺序处理，100个报告耗时200秒
- **优化后**: 并发处理，100个报告耗时30秒
- **提升**: 6.7倍

#### 策略2: 线程池复用
- 使用自定义线程池，避免频繁创建/销毁线程
- 合理配置线程池参数（核心线程数、最大线程数、队列容量）

#### 策略3: 超时控制
- 动态计算超时时间（每条2秒 × 数据量）
- 最小30秒，最大300秒
- 避免长时间阻塞

#### 策略4: 数据库优化
- 添加索引: `sign_status`
- 批量更新，减少数据库交互次数
- 使用连接池，避免频繁创建连接

### 10.2 性能监控

**监控指标**:
- 接口响应时间 (P50, P95, P99)
- 签名成功率
- Grape City服务响应时间
- 线程池使用情况

**告警阈值**:
- 接口响应时间 > 60秒 → 告警
- 签名成功率 < 95% → 告警
- Grape City服务超时率 > 10% → 告警

---

## 11. 测试方案

### 11.1 单元测试

**测试类**: `TaskOrderExpandServiceImplTest`

**测试用例**:
1. `testBatchSign_success()`: 测试全部成功场景
2. `testBatchSign_partialFailure()`: 测试部分失败场景
3. `testBatchSign_allFailure()`: 测试全部失败场景
4. `testBatchSign_exceedLimit()`: 测试超过100条限制
5. `testBatchSign_emptyList()`: 测试空列表
6. `testBatchSign_missingRequiredField()`: 测试缺少必填字段

**示例**:
```java
@Test
public void testBatchSign_success() {
    // 准备测试数据
    List<OrderItemSignVO> list = new ArrayList<>();
    list.add(createSignVO("report-1"));
    list.add(createSignVO("report-2"));

    // 执行
    BatchOperationRespVO result = taskOrderExpandService.batchSign(list);

    // 验证
    assertEquals(2, result.getTotalCount());
    assertEquals(2, result.getSuccessCount());
    assertEquals(0, result.getFailCount());
    assertTrue(result.getAllSuccess());
}
```

### 11.2 集成测试

**测试场景**:
1. 正常流程测试
2. Grape City服务超时测试
3. Grape City服务错误测试
4. 数据库连接失败测试

**测试工具**: Postman, JMeter

### 11.3 性能测试

**测试工具**: JMeter

**测试场景**:
1. 10个报告批量签名 → 预期响应时间 < 5秒
2. 50个报告批量签名 → 预期响应时间 < 20秒
3. 100个报告批量签名 → 预期响应时间 < 30秒

**并发测试**:
- 10个用户同时发起批量签名请求
- 每个用户签名10个报告
- 预期：所有请求在10秒内完成

---

## 12. 部署说明

### 12.1 配置项

**application-local.yaml**:
```yaml
grape:
  city:
    url: http://localhost:8080
    timeout: 5000
    retry: 1

thread:
  pool:
    core-size: 8
    max-size: 16
    queue-capacity: 200
```

### 12.2 部署步骤

1. **执行数据库脚本**:
   ```bash
   mysql -u root -p < sql/sign_feature.sql
   ```

2. **编译打包**:
   ```bash
   mvn clean package -DskipTests
   ```

3. **启动服务**:
   ```bash
   java -jar tz-module-pressure-biz.jar --spring.profiles.active=prod
   ```

4. **验证接口**:
   ```bash
   curl -X PUT http://localhost:48100/pressure/task-order/batch-sign \
     -H "Content-Type: application/json" \
     -d '[{"id":"report-1","signerName":"张三"}]'
   ```

### 12.3 回滚方案

如果部署后发现问题，回滚步骤：

1. 停止服务
2. 恢复旧版本jar包
3. 回滚数据库脚本（如果有Schema变更）
4. 重新启动服务
5. 验证功能正常

---

## 13. 影响分析

### 13.1 对现有功能的影响

#### 影响范围1: 任务单报告表 (tz_task_order_item_report)
- **影响类型**: Schema变更
- **变更内容**: 新增4个字段（sign_status, sign_time, signer_name, sign_error）
- **兼容性**: ✅ 向后兼容（新字段允许为NULL）
- **风险等级**: 🟢 低风险

#### 影响范围2: 现有签名功能
- **影响类型**: 功能增强
- **变更内容**: 新增批量签名接口
- **兼容性**: ✅ 不影响现有单个签名接口
- **风险等级**: 🟢 低风险

#### 影响范围3: Grape City服务
- **影响类型**: 依赖增加
- **变更内容**: 调用Grape City签名接口
- **兼容性**: ✅ 新增功能，不影响现有调用
- **风险等级**: 🟡 中风险（如果Grape City服务不稳定）

### 13.2 对其他模块的影响

| 模块名称 | 影响类型 | 影响说明 | 风险等级 |
|----------|----------|----------|----------|
| tz-module-system | 无影响 | 无依赖 | 🟢 |
| tz-module-infra | 无影响 | 无依赖 | 🟢 |
| tz-module-bpm | 无影响 | 无依赖 | 🟢 |
| 前端模块 | 需要适配 | 新增批量签名接口 | 🟡 |

### 13.3 对数据库的影响

**表变更**:
- `tz_task_order_item_report`: 新增4个字段
- `tz_sign_log`: 新表

**数据迁移**: 无需数据迁移

**性能影响**:
- 新增索引可能略微影响INSERT/UPDATE性能
- 预估影响: < 5%

### 13.4 对性能的影响

**资源消耗**:
- CPU: 并发签名会增加CPU使用率
- 内存: 线程池会占用额外内存
- 数据库连接: 批量更新会增加连接占用

**优化建议**:
- 配置合理的线程池参数
- 监控资源使用情况
- 必要时限流

---

## 14. 后续扩展

### 14.1 已知限制

1. 单次批量签名最多100个报告
2. 签名操作不可逆（不支持撤销）
3. 不支持签名进度实时推送

### 14.2 未来优化

#### 优化1: 支持更多报告
- **当前限制**: 最多100个
- **优化方案**: 分批处理 + 进度推送
- **优先级**: P2

#### 优化2: 签名进度实时推送
- **当前方案**: 轮询查询
- **优化方案**: WebSocket推送
- **优先级**: P2

#### 优化3: 签名撤销功能
- **当前方案**: 不支持撤销
- **优化方案**: 增加撤销接口，记录撤销日志
- **优先级**: P3

#### 优化4: 异步签名
- **当前方案**: 同步等待签名完成
- **优化方案**: 提交任务后异步处理，通过回调通知结果
- **优先级**: P3

### 14.3 扩展点

1. **签名方式扩展**: 支持更多签名服务（不限于Grape City）
2. **签名模板管理**: 支持自定义签名位置和样式
3. **签名审计**: 增强签名日志和审计功能
4. **批量导出**: 支持批量导出已签名的报告

---

## 15. 附录

### 15.1 术语表

| 术语     | 全称                     | 说明                     |
|----------|--------------------------|--------------------------|
| Grape City| Grape City Document Service | 文档签名服务            |
| VO       | Value Object             | 值对象，用于数据传输     |
| DO       | Data Object              | 数据对象，对应数据库表   |
| P0/P1/P2 | Priority 0/1/2           | 优先级（0=必须有）       |

### 15.2 参考文档

1. [Spring Cloud Alibaba官方文档](https://spring-cloud-alibaba-group.github.io/)
2. [MyBatis Plus官方文档](https://baomidou.com/)
3. [Grape City API文档](./grape-city-api.md)
4. [项目编码规范](../docs/coding-standard.md)

### 15.3 相关代码路径

| 模块             | 路径                                                                 |
|------------------|----------------------------------------------------------------------|
| Controller       | `tz-module-pressure/.../controller/appapi/taskorder/`               |
| Service          | `tz-module-pressure/.../service/taskorder/`                         |
| Mapper           | `tz-module-pressure/.../dal/mysql/taskorderitemreport/`             |
| VO               | `tz-module-pressure/.../controller/appapi/taskorder/vo/`            |
| 线程池工具       | `tz-framework/tz-common/.../util/concurrent/`                       |

### 15.4 联系人

| 角色     | 姓名   | 邮箱              | 职责                 |
|----------|--------|-------------------|----------------------|
| 需求方   | XXX    | xxx@example.com   | 需求澄清、验收       |
| 开发负责人 | XXX  | xxx@example.com   | 技术方案、开发实现   |
| 测试负责人 | XXX  | xxx@example.com   | 测试用例、质量保障   |
| 运维负责人 | XXX  | xxx@example.com   | 部署、监控、运维     |

---

**文档结束**
