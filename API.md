# REFPROP 热力学计算 API 接口规范

本文档供前端 (reffrontend.jingyanrong.com) 对接使用。

## 基础信息

- **Base URL**: `https://ref.jingyanrong.com`
- **Content-Type**: `application/json`

---

## POST /calculate

计算给定工质和状态点的热力学性质。

### 请求头

| 头名 | 必填 | 说明 |
|------|------|------|
| `Content-Type` | 是 | `application/json` |

### 请求体 (JSON)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `fluid_string` | string | 是 | 工质字符串 |
| `input_type` | string | 是 | 输入类型（两字符） |
| `value1` | number | 是 | 第一个输入参数 |
| `value2` | number | 是 | 第二个输入参数 |

### fluid_string 格式

- **纯工质**: `"R32"`, `"R1234ZE"`, `"Water"`
- **混合工质（自定义）**: `"R32&R125|0.5&0.5"`
  - `&` 分隔组分名
  - `|` 分隔组分与比例
  - 比例部分用 `&` 分隔，表示摩尔分数（可自动归一化）

示例：

- `"R32"` — 纯 R32
- `"R32&R125|0.5&0.5"` — R32/R125 等摩尔混合物
- `"R32&R125|0.7&0.3"` — R32 70%、R125 30%（摩尔）

### input_type 常用取值

| input_type | value1 | value2 | 说明 |
|------------|--------|--------|------|
| PT | P [kPa] | T [K] | 压力 + 温度 |
| PQ | P [kPa] | Q (干度 0~1) | 压力 + 干度 |
| PH | P [kPa] | H [J/mol] | 压力 + 焓 |
| TD | T [K] | D [mol/dm³] | 温度 + 密度 |
| TQ | T [K] | Q | 温度 + 干度 |
| PS | P [kPa] | S [J/(mol·K)] | 压力 + 熵 |

### 响应体 (JSON)

| 字段 | 类型 | 说明 |
|------|------|------|
| T | number \| null | 温度 [K] |
| P | number \| null | 压力 [kPa] |
| D | number \| null | 密度 [mol/dm³] |
| H | number \| null | 焓 [J/mol] |
| S | number \| null | 熵 [J/(mol·K)] |
| Q | number \| null | 干度（摩尔基，0~1） |
| CP | number \| null | 定压比热 [J/(mol·K)] |
| CV | number \| null | 定容比热 [J/(mol·K)] |
| W | number \| null | 声速 [m/s] |

两相区时，CP、CV、W 可能为 `null`（REFPROP 在两相区不定义这些量）。

### 请求示例

```bash
curl -X POST "https://ref.jingyanrong.com/calculate" \
  -H "Content-Type: application/json" \
  -d '{
    "fluid_string": "R32",
    "input_type": "PT",
    "value1": 101.325,
    "value2": 300
  }'
```

### 响应示例

```json
{
  "T": 300.0,
  "P": 101.325,
  "D": 40.123,
  "H": 12345.67,
  "S": 89.012,
  "Q": null,
  "CP": 75.4,
  "CV": 67.2,
  "W": 450.3
}
```

### 错误响应

| 状态码 | 说明 |
|--------|------|
| 400 | 参数错误（如 fluid_string 或 input_type 格式不正确） |
| 500 | REFPROP 计算错误或服务端配置问题 |

错误响应体示例：

```json
{
  "detail": "REFPROP 计算错误 (ierr=xxx): 错误信息"
}
```

---

## POST /dome

生成饱和包络线 (P-h Dome) 数据，供前端绘制 P-h 压焓图。

### 请求体 (JSON)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `fluid_string` | string | 是 | 工质字符串，同 `/calculate` |

### 响应体 (JSON)

| 字段 | 类型 | 说明 |
|------|------|------|
| `liquid` | array | 饱和液线 (q=0) 的点数组，每项 `{P, H}` |
| `vapor` | array | 饱和气线 (q=1) 的点数组，每项 `{P, H}` |
| `critical` | object | 临界点 `{T, P, H}` |

单位：P [kPa]，H [J/mol]，T [K]。

### 请求示例

```bash
curl -X POST "https://ref.jingyanrong.com/dome" \
  -H "Content-Type: application/json" \
  -d '{"fluid_string": "R32"}'
```

### 响应示例

```json
{
  "liquid": [
    {"P": 82.34, "H": 12345.6},
    {"P": 101.325, "H": 15678.9}
  ],
  "vapor": [
    {"P": 82.34, "H": 45678.9},
    {"P": 101.325, "H": 48901.2}
  ],
  "critical": {
    "T": 351.25,
    "P": 5782.0,
    "H": 32156.7
  }
}
```

---

## GET /

健康检查接口。

**响应示例**:

```json
{
  "status": "ok",
  "api": "REFPROP 热力学计算 API"
}
```

---

## 前端 API 调用规则

### 通用规则

| 项目 | 值 |
|------|-----|
| Base URL | `https://ref.jingyanrong.com` |
| Content-Type | `application/json` |
| CORS | 已配置允许域名，本地开发可用 `http://localhost:5173` |

### 1. 物性计算 `/calculate`（POST）

**请求示例：**

```javascript
fetch('https://ref.jingyanrong.com/calculate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    fluid_string: 'R32',      // 纯工质或 "R32&R125|0.7&0.3" 混合物
    input_type: 'PT',         // PT|PQ|PH|TD|TQ|PS
    value1: 101.325,          // 单位见下表
    value2: 300
  })
})
```

**input_type 与 value1、value2 对应关系：**

| input_type | value1 | value2 |
|------------|--------|--------|
| PT | P [kPa] | T [K] |
| PQ | P [kPa] | Q 干度 0~1 |
| PH | P [kPa] | H [J/mol] |
| TD | T [K] | D [mol/dm³] |
| TQ | T [K] | Q 干度 |
| PS | P [kPa] | S [J/(mol·K)] |

**响应字段：** `T`, `P`, `D`, `H`, `S`, `Q`, `CP`, `CV`, `W`（单位：K, kPa, mol/dm³, J/mol, J/(mol·K), -, J/(mol·K), J/(mol·K), m/s）。两相区时 `CP`、`CV`、`W` 可能为 `null`。

### 2. 饱和包络线 `/dome`（POST）

**请求示例：**

```javascript
fetch('https://ref.jingyanrong.com/dome', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ fluid_string: 'R32' })
})
```

**响应：** `{ liquid: [{P,H},...], vapor: [{P,H},...], critical: {T,P,H} }`，单位 P [kPa]，H [J/mol]，T [K]。

### 3. 健康检查 `/`（GET）

用于检查服务是否可用：

```javascript
fetch('https://ref.jingyanrong.com/')
```

### 错误处理

| 状态码 | 含义 |
|--------|------|
| 400 | 参数格式错误 |
| 500 | REFPROP 计算错误，响应体 `{ detail: "错误信息" }` |

建议前端在 500 时展示 `detail` 中的错误信息。

---

## 部署说明

1. 安装 REFPROP 10.0，确保存在 `librefprop.so` 及 `FLUIDS` 文件夹。
2. 复制 `.env.example` 为 `.env`，配置 `RPPREFIX`、`ALLOWED_ORIGINS`。
3. 生产启动：`./start.sh`（gunicorn + UvicornWorker，4 进程，绑定 0.0.0.0:8003）。
