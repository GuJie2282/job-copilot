# [功能名称] API接口文档

## 📋 变更历史

| 版本号 | 时间       | 修改内容           | 修改人   |
|--------|------------|--------------------|----------|
| v001   | YYYY.MM.DD | 初稿               | XXX      |
| v002   | YYYY.MM.DD | 新增XXX接口        | XXX      |

## 目录

1. [接口说明](#1-接口说明)
2. [通讯约定](#2-通讯约定)
3. [认证机制](#3-认证机制)
4. [接口定义](#4-接口定义)

---

## 1. 接口说明

### 1.1 基础URL

```
开发环境: http://localhost:48100
测试环境: http://test-server:48080/pressure
生产环境: http://prod-server:48080/pressure
```

### 1.2 通用请求头

| 字段名        | 是否必填 | 说明                         | 示例值                    |
|---------------|----------|------------------------------|---------------------------|
| Content-Type  | 是       | 请求内容类型                 | application/json          |
| Authorization | 是       | 认证Token (Bearer Token)     | Bearer eyJhbGc...         |
| tenant-id     | 否       | 租户ID (多租户场景)          | 1                         |

### 1.3 通用响应格式

所有接口返回统一的响应格式：

```json
{
  "code": 0,          // 0表示成功，非0表示失败
  "data": {},         // 业务数据
  "msg": "操作成功"    // 提示信息
}
```

### 1.4 通用错误码

| 错误码 | 说明                     |
|--------|--------------------------|
| 0      | 成功                     |
| 400    | 请求参数错误             |
| 401    | 未认证                   |
| 403    | 无权限                   |
| 404    | 资源不存在               |
| 500    | 服务器内部错误           |
| 900    | 业务错误（具体见业务错误码） |

---

## 2. 通讯约定

1. **协议**: HTTP/HTTPS
2. **请求方法**: RESTful风格 (GET/POST/PUT/DELETE)
3. **数据格式**: JSON
4. **字符编码**: UTF-8
5. **时间格式**: ISO 8601 (`yyyy-MM-dd'T'HH:mm:ss.SSSZ`)

---

## 3. 认证机制

### 3.1 Token获取

**接口地址**: `POST /system/auth/login`

**请求参数**:
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "userId": "1",
    "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expiresTime": 1735689600000
  },
  "msg": "操作成功"
}
```

### 3.2 Token使用

在请求头中添加:
```
Authorization: Bearer {accessToken}
```

### 3.3 Token刷新

**接口地址**: `POST /system/auth/refresh-token`

**请求参数**:
```json
{
  "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

## 4. 接口定义

## 4.1 [模块名称]

### 4.1.1 [接口名称 - 例如：获取任务单列表]

**接口地址**: `GET /pressure/task-order/page`

**接口说明**: 分页查询任务单列表，支持多条件筛选

**请求参数** (Query Parameters):

| 参数名        | 是否必填 | 类型   | 说明             | 示例值       |
|---------------|----------|--------|------------------|--------------|
| pageNo        | 否       | Integer| 页码（从1开始）  | 1            |
| pageSize      | 否       | Integer| 每页条数         | 10           |
| taskNo        | 否       | String | 任务单号（模糊） | RD0025111201 |
| status        | 否       | String | 任务状态         | DRAFT        |
| startTime     | 否       | String | 创建时间-开始    | 2025-01-01   |
| endTime       | 否       | String | 创建时间-结束    | 2025-12-31   |

**请求示例**:
```http
GET /pressure/task-order/page?pageNo=1&pageSize=10&taskNo=RD0025111201
Authorization: Bearer eyJhbGc...
```

**响应示例** (成功):
```json
{
  "code": 0,
  "data": {
    "total": 100,
    "list": [
      {
        "id": "1174571",
        "taskNo": "RD0025111201",
        "status": "DRAFT",
        "statusText": "草稿",
        "unitName": "某某公司",
        "legalFee": 274.00,
        "createTime": "2025-01-07 10:30:00",
        "updateTime": "2025-01-07 15:20:00"
      }
    ]
  },
  "msg": "操作成功"
}
```

**响应字段说明**:

| 字段名     | 类型     | 说明             |
|------------|----------|------------------|
| total      | Integer  | 总记录数         |
| list       | Array    | 数据列表         |
| id         | String   | 任务单ID         |
| taskNo     | String   | 任务单号         |
| status     | String   | 状态码           |
| statusText | String   | 状态文本         |
| unitName   | String   | 单位名称         |
| legalFee   | Decimal  | 法定费用         |
| createTime | String   | 创建时间         |
| updateTime | String   | 更新时间         |

**错误响应示例**:
```json
{
  "code": 400,
  "data": null,
  "msg": "任务单号格式不正确"
}
```

---

### 4.1.2 [接口名称 - 例如：创建任务单]

**接口地址**: `POST /pressure/task-order/create`

**接口说明**: 创建新的任务单

**请求参数** (Request Body):

```json
{
  "taskNo": "RD0025111201",
  "unitName": "某某公司",
  "unitCode": "UNIT001",
  "linkman": "张三",
  "tel": "13800138000",
  "checkDate": "2025-01-15",
  "feeType": "LEGAL",
  "checkType": "RD",
  "remark": "备注信息"
}
```

**请求字段说明**:

| 字段名     | 是否必填 | 类型   | 长度 | 说明               | 示例值         |
|------------|----------|--------|------|--------------------|----------------|
| taskNo     | 是       | String | 50   | 任务单号           | RD0025111201   |
| unitName   | 是       | String | 150  | 单位名称           | 某某公司       |
| unitCode   | 否       | String | 30   | 单位代码           | UNIT001        |
| linkman    | 是       | String | 80   | 联系人             | 张三           |
| tel        | 是       | String | 40   | 联系电话           | 13800138000    |
| checkDate  | 是       | String | 10   | 检验日期           | 2025-01-15     |
| feeType    | 否       | String | 10   | 收费类型           | LEGAL          |
| checkType  | 是       | String | 10   | 约检类型           | RD             |
| remark     | 否       | String | 400  | 备注               | 备注信息       |

**请求示例**:
```http
POST /pressure/task-order/create
Content-Type: application/json
Authorization: Bearer eyJhbGc...

{
  "taskNo": "RD0025111201",
  "unitName": "某某公司",
  "linkman": "张三",
  "tel": "13800138000",
  "checkDate": "2025-01-15",
  "checkType": "RD"
}
```

**响应示例** (成功):
```json
{
  "code": 0,
  "data": "1174571",
  "msg": "创建成功"
}
```

**响应字段说明**:

| 字段名 | 类型   | 说明         |
|--------|--------|--------------|
| data   | String | 新创建的任务单ID |

**错误响应示例**:
```json
{
  "code": 900,
  "data": null,
  "msg": "任务单号已存在"
}
```

---

### 4.1.3 [接口名称 - 例如：批量操作]

**接口地址**: `PUT /pressure/task-order/batch-update`

**接口说明**: 批量更新任务单状态

**请求参数** (Request Body):

```json
[
  {
    "id": "1174571",
    "status": "APPROVED",
    "remark": "审核通过"
  },
  {
    "id": "1174572",
    "status": "APPROVED",
    "remark": "审核通过"
  }
]
```

**请求字段说明**:

| 字段名 | 是否必填 | 类型   | 说明           | 示例值     |
|--------|----------|--------|----------------|------------|
| id     | 是       | String | 任务单ID       | 1174571    |
| status | 是       | String | 目标状态       | APPROVED   |
| remark | 否       | String | 备注           | 审核通过   |

**请求示例**:
```http
PUT /pressure/task-order/batch-update
Content-Type: application/json
Authorization: Bearer eyJhbGc...

[
  {"id": "1174571", "status": "APPROVED"},
  {"id": "1174572", "status": "APPROVED"}
]
```

**响应示例** (全部成功):
```json
{
  "code": 0,
  "data": {
    "totalCount": 2,
    "successCount": 2,
    "failCount": 0,
    "allSuccess": true,
    "errorMessage": null,
    "successItems": [
      {
        "id": "1174571",
        "taskNo": "RD0025111201",
        "success": true,
        "errorMessage": null
      },
      {
        "id": "1174572",
        "taskNo": "RD0025111202",
        "success": true,
        "errorMessage": null
      }
    ],
    "failedItems": []
  },
  "msg": "操作成功"
}
```

**响应示例** (部分失败):
```json
{
  "code": 0,
  "data": {
    "totalCount": 3,
    "successCount": 2,
    "failCount": 1,
    "allSuccess": false,
    "errorMessage": "批量操作部分失败，总数据: 3, 成功: 2, 失败: 1",
    "successItems": [
      {
        "id": "1174571",
        "success": true
      },
      {
        "id": "1174572",
        "success": true
      }
    ],
    "failedItems": [
      {
        "id": "1174573",
        "success": false,
        "errorMessage": "任务单不存在或已被删除"
      }
    ]
  },
  "msg": "操作成功"
}
```

**响应字段说明**:

| 字段名        | 类型     | 说明                       |
|---------------|----------|----------------------------|
| totalCount    | Integer  | 总数据量                   |
| successCount  | Integer  | 成功数量                   |
| failCount     | Integer  | 失败数量                   |
| allSuccess    | Boolean  | 是否全部成功               |
| errorMessage  | String   | 错误消息（仅当有失败时）   |
| successItems  | Array    | 成功的数据列表             |
| failedItems   | Array    | 失败的数据列表             |

---

## 5. 前端对接示例

### 5.1 Vue 3 + Element Plus

```javascript
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getTaskOrderPage, createTaskOrder } from '@/api/task-order'

// 分页查询
const fetchTaskOrders = async () => {
  try {
    const response = await getTaskOrderPage({
      pageNo: 1,
      pageSize: 10,
      taskNo: 'RD0025111201'
    })

    if (response.code === 0) {
      console.log('总数据:', response.data.total)
      console.log('列表数据:', response.data.list)
    }
  } catch (error) {
    ElMessage.error('查询失败')
  }
}

// 创建任务单
const handleCreate = async () => {
  try {
    const response = await createTaskOrder({
      taskNo: 'RD0025111201',
      unitName: '某某公司',
      linkman: '张三',
      tel: '13800138000',
      checkDate: '2025-01-15',
      checkType: 'RD'
    })

    if (response.code === 0) {
      ElMessage.success('创建成功，ID: ' + response.data)
    }
  } catch (error) {
    ElMessage.error('创建失败')
  }
}

// 批量操作
const handleBatchUpdate = async () => {
  const response = await batchUpdate([
    { id: '1174571', status: 'APPROVED' },
    { id: '1174572', status: 'APPROVED' }
  ])

  const result = response.data

  if (result.allSuccess) {
    ElMessage.success(`全部成功！共 ${result.successCount} 条`)
  } else {
    ElNotification({
      title: '部分失败',
      type: 'warning',
      message: `总数据: ${result.totalCount}, 成功: ${result.successCount}, 失败: ${result.failCount}`,
      duration: 0
    })
  }
}
```

### 5.2 React + Ant Design

```javascript
import { message, notification } from 'antd'
import { getTaskOrderPage, createTaskOrder } from '@/api/task-order'

// 分页查询
const fetchTaskOrders = async () => {
  try {
    const response = await getTaskOrderPage({
      pageNo: 1,
      pageSize: 10,
      taskNo: 'RD0025111201'
    })

    if (response.code === 0) {
      console.log('总数据:', response.data.total)
      console.log('列表数据:', response.data.list)
    }
  } catch (error) {
    message.error('查询失败')
  }
}

// 创建任务单
const handleCreate = async () => {
  try {
    const response = await createTaskOrder({
      taskNo: 'RD0025111201',
      unitName: '某某公司',
      linkman: '张三',
      tel: '13800138000',
      checkDate: '2025-01-15',
      checkType: 'RD'
    })

    if (response.code === 0) {
      message.success('创建成功，ID: ' + response.data)
    }
  } catch (error) {
    message.error('创建失败')
  }
}

// 批量操作
const handleBatchUpdate = async () => {
  const response = await batchUpdate([
    { id: '1174571', status: 'APPROVED' },
    { id: '1174572', status: 'APPROVED' }
  ])

  const result = response.data

  if (result.allSuccess) {
    message.success(`全部成功！共 ${result.successCount} 条`)
  } else {
    notification.warning({
      message: '部分失败',
      description: `总数据: ${result.totalCount}, 成功: ${result.successCount}, 失败: ${result.failCount}`
    })
  }
}
```

### 5.3 TypeScript 类型定义

```typescript
// task-order.types.ts

// 任务单对象
export interface TaskOrderVO {
  id: string
  taskNo: string
  status: string
  statusText: string
  unitName: string
  legalFee: number
  createTime: string
  updateTime: string
}

// 分页请求参数
export interface TaskOrderPageReqVO {
  pageNo?: number
  pageSize?: number
  taskNo?: string
  status?: string
  startTime?: string
  endTime?: string
}

// 分页响应
export interface PageResult<T> {
  total: number
  list: T[]
}

// 创建请求
export interface TaskOrderCreateReqVO {
  taskNo: string
  unitName: string
  unitCode?: string
  linkman: string
  tel: string
  checkDate: string
  feeType?: string
  checkType: string
  remark?: string
}

// 批量操作单项结果
export interface BatchOperationItemVO {
  id: string
  taskNo?: string
  success: boolean
  errorMessage?: string
}

// 批量操作响应
export interface BatchOperationRespVO {
  totalCount: number
  successCount: number
  failCount: number
  allSuccess: boolean
  errorMessage?: string
  successItems: BatchOperationItemVO[]
  failedItems: BatchOperationItemVO[]
}

// 通用API响应
export interface ApiResponse<T> {
  code: number
  data: T
  msg: string
}

// API函数
export const taskOrderApi = {
  // 分页查询
  getPage: (params: TaskOrderPageReqVO): Promise<ApiResponse<PageResult<TaskOrderVO>>> => {
    return request.get('/pressure/task-order/page', { params })
  },

  // 创建
  create: (data: TaskOrderCreateReqVO): Promise<ApiResponse<string>> => {
    return request.post('/pressure/task-order/create', data)
  },

  // 批量更新
  batchUpdate: (data: TaskOrderUpdateReqVO[]): Promise<ApiResponse<BatchOperationRespVO>> => {
    return request.put('/pressure/task-order/batch-update', data)
  }
}
```

---

## 6. 常见问题

### Q1: 如何处理Token过期?
**A**: 当收到 `401` 错误时，前端应自动使用 refreshToken 刷新 accessToken，然后重试原请求。

### Q2: 分页参数默认值?
**A**:
- pageNo: 1
- pageSize: 10

### Q3: 时间格式?
**A**: 前端传递时间格式为 `yyyy-MM-dd` 或 `yyyy-MM-dd HH:mm:ss`，后端会自动转换。

### Q4: 批量操作有限制吗?
**A**: 单次批量操作最多100条数据，超过会返回错误。

---

## 7. 相关文档

- [功能设计文档](../design/[功能名称]设计文档.md)
- [数据库设计](../database/[功能名称]数据库设计.md)
- [测试用例](../test/[功能名称]测试用例.md)
