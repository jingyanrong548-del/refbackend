# REFPROP 热力学计算 API

基于 NIST REFPROP 10.0 的热力学性质计算后端，面向高温热泵、新工质开发等高精度工业应用。

- **生产环境**: https://ref.jingyanrong.com
- **接口文档**: [API.md](./API.md)
- **部署说明**: [DEPLOY.md](./DEPLOY.md)

## 前置条件

1. **REFPROP 10.0**：需已安装 NIST REFPROP 10.0，且包含：
   - `REFPRP64.DLL`（Windows）或 `librefprop.so`（Linux）/ `librefprop.dylib`（macOS）
   - `FLUIDS` 文件夹
   - `MIXTURES` 文件夹（混合工质需）

2. **Python 3.10+**

## 安装

```bash
pip install -r requirements.txt
```

## 配置

设置 REFPROP 安装路径（二选一）：

```bash
# 方式 1：环境变量
export RPPREFIX="/path/to/REFPROP"

# 方式 2：修改 config.py 中的 RPPREFIX
```

Windows 若使用默认 MSI 安装，`RPPREFIX` 通常已自动设置。

## 运行

```bash
uvicorn main:app --host 0.0.0.0 --port 8003
```

或：

```bash
python main.py
```

## API 说明

详见 [API.md](./API.md)。

### 快速示例

```bash
# PT 输入：P=101.325 kPa, T=300 K，工质 R32
curl -X POST "http://localhost:8003/calculate" \
  -H "Content-Type: application/json" \
  -d '{"fluid_string":"R32","input_type":"PT","value1":101.325,"value2":300}'
```

## 项目结构

```
refbackend/
├── main.py           # FastAPI 应用入口
├── refprop_service.py # REFPROP 调用封装
├── config.py         # 路径配置
├── requirements.txt
├── API.md            # 接口文档（供前端对接）
└── README.md
```
