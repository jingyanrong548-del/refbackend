# REFPROP 热力学计算 API 接口规范

本文档供前端 (reffrontend.jingyanrong.com) 对接使用。**接口调用规则完全遵循 NIST REFPROP 10.0 官方规范**，与 REFPROP REFPROPdll 行为保持一致。

参考：[REFPROP 10.0 High-Level API](https://refprop-docs.readthedocs.io/en/latest/DLL/high_level.html)

---

## 单位制（与 REFPROP DEFAULT 一致）

本 API 采用 **NIST REFPROP DEFAULT 单位制**（iUnits = 0），与 REFPROP 官方默认单位完全一致：

| 物理量 | 单位 |
|--------|------|
| 温度 T | K |
| 压力 P | kPa |
| 密度 D | mol/dm³ |
| 焓 H | J/mol |
| 熵 S | J/(mol·K) |
| 干度 Q | 无量纲 (0~1，摩尔基) |
| 定压比热 CP | J/(mol·K) |
| 定容比热 CV | J/(mol·K) |
| 声速 W | m/s |

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
| `fluid_string` | string | 是 | 工质字符串，格式见下文 |
| `input_type` | string | 是 | 两字符输入类型（与 REFPROP hIn 一致） |
| `value1` | number | 是 | 第一个输入参数 `a` 的值 |
| `value2` | number | 是 | 第二个输入参数 `b` 的值 |

### input_type 与 value1、value2 对应关系（REFPROP 官方）

**重要：参数顺序必须与 input_type 的字母顺序一致**。例如 `PT` 表示 `a=P, b=T`，即 `value1` 为压力，`value2` 为温度。

| input_type | value1 (a) | value2 (b) | 说明 |
|------------|------------|------------|------|
| PT / TP | P [kPa] | T [K] | 压力 + 温度 |
| PQ / QP | P [kPa] | Q (0~1) | 压力 + 干度 |
| PH / HP | P [kPa] | H [J/mol] | 压力 + 焓 |
| PS / SP | P [kPa] | S [J/(mol·K)] | 压力 + 熵 |
| PD / DP | P [kPa] | D [mol/dm³] | 压力 + 密度 |
| TQ / QT | T [K] | Q (0~1) | 温度 + 干度 |
| TH / HT | T [K] | H [J/mol] | 温度 + 焓 |
| TS / ST | T [K] | S [J/(mol·K)] | 温度 + 熵 |
| TD / DT | T [K] | D [mol/dm³] | 温度 + 密度 |
| TE / ET | T [K] | E [J/mol] | 温度 + 内能 |
| DE / ED | D [mol/dm³] | E [J/mol] | 密度 + 内能 |
| DH / HD | D [mol/dm³] | H [J/mol] | 密度 + 焓 |
| DS / SD | D [mol/dm³] | S [J/(mol·K)] | 密度 + 熵 |
| DQ / QD | D [mol/dm³] | Q (0~1) | 密度 + 干度 |
| ES / SE | E [J/mol] | S [J/(mol·K)] | 内能 + 熵 |
| EQ / QE | E [J/mol] | Q (0~1) | 内能 + 干度 |
| HS / SH | H [J/mol] | S [J/(mol·K)] | 焓 + 熵 |
| HQ / QH | H [J/mol] | Q (0~1) | 焓 + 干度 |
| SQ / QS | S [J/(mol·K)] | Q (0~1) | 熵 + 干度 |

REFPROP 文档：*"The order of the properties being sent to the routine in the variables a and b has to be the same as the letters sent to hIn; for example, if hIn is 'QT', then a=q and b=T."*

### fluid_string 格式（REFPROP 兼容）

- **纯工质**：`"R32"`, `"R1234ZE"`, `"Water"`, `"CO2"` 等
- **混合工质（本 API 扩展）**：`"R32&R125|0.5&0.5"`
  - `&` 分隔组分名
  - `|` 分隔组分与摩尔分数
  - 比例可自动归一化

示例：

- `"R32"` — 纯 R32
- `"R32&R125|0.5&0.5"` — R32/R125 等摩尔混合物
- `"R32&R125|0.7&0.3"` — R32 70%、R125 30%（摩尔）

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
# PT 输入：P=101.325 kPa, T=300 K（value1=P, value2=T）
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

单位：P [kPa]，H [J/mol]，T [K]（与 REFPROP DEFAULT 一致）。

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

**参数顺序务必与 input_type 对应**：

| input_type | value1 | value2 |
|------------|--------|--------|
| PT | P [kPa] | T [K] |
| PQ | P [kPa] | Q 干度 0~1 |
| PH | P [kPa] | H [J/mol] |
| TD | T [K] | D [mol/dm³] |
| TQ | T [K] | Q 干度 |
| PS | P [kPa] | S [J/(mol·K)] |

**请求示例：**

```javascript
fetch('https://ref.jingyanrong.com/calculate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    fluid_string: 'Water',
    input_type: 'PT',    // P + T
    value1: 1000,       // P [kPa]
    value2: 300         // T [K]
  })
})
```

**响应字段：** `T`, `P`, `D`, `H`, `S`, `Q`, `CP`, `CV`, `W`（单位：K, kPa, mol/dm³, J/mol, J/(mol·K), -, J/(mol·K), J/(mol·K), m/s）。

### 2. 饱和包络线 `/dome`（POST）

```javascript
fetch('https://ref.jingyanrong.com/dome', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ fluid_string: 'R32' })
})
```

**响应：** `{ liquid: [{P,H},...], vapor: [{P,H},...], critical: {T,P,H} }`，单位 P [kPa]，H [J/mol]，T [K]。

### 3. 健康检查 `/`（GET）

```javascript
fetch('https://ref.jingyanrong.com/')
```

### 错误处理

| 状态码 | 含义 |
|--------|------|
| 400 | 参数格式错误 |
| 500 | REFPROP 计算错误，响应体 `{ detail: "错误信息" }` |

---

## 部署说明

1. 安装 REFPROP 10.0，确保存在 `librefprop.so` 及 `FLUIDS` 文件夹。
2. 复制 `.env.example` 为 `.env`，配置 `RPPREFIX`、`ALLOWED_ORIGINS`。
3. 生产启动：`./start.sh`（gunicorn + UvicornWorker，4 进程，绑定 0.0.0.0:8003）。
