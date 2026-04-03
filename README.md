# 面试 Markdown 整理助手

面试 Markdown 整理助手是一个面向技术面试场景的本地化工具，用于将面试音频或视频自动转写并整理为结构化 Markdown 文档。项目基于 `faster-whisper` 完成语音识别，并结合 LLM 对转写结果进行角色区分、识别纠错、文本整理、面试总结与改进建议生成，输出适合复盘、归档与分享的面试记录。

## 项目简介

本项目聚焦“技术面试内容整理”这一明确场景，提供从音视频上传、音频提取、语音转写到 Markdown 成稿的完整处理链路。当前版本主要面向中文技术面试，支持本地运行、前后端分离、任务轮询、进度展示、结果预览与文件下载。

## 仓库地址

- GitHub: [https://github.com/hbx2004/interview-markdown-agent](https://github.com/hbx2004/interview-markdown-agent)



## 核心功能

- 支持常见音频、视频文件上传
- 基于 `ffmpeg` 自动提取和规范化音频
- 基于 `faster-whisper` 完成语音识别
- 支持 CPU 与 CUDA GPU 推理
- 结合 LLM 区分 `面试官` / `候选人`
- 修正明显错别字与 ASR 误识别
- 输出结构化 Markdown 面试记录
- 自动补充“面试总结”和“可提升点”
- 支持长文本分块整理，降低 LLM 输出截断风险
- 前端支持进度条、状态轮询、结果预览与文件下载
- 浏览器刷新后可恢复最近任务状态

## 项目结构

```text
.
├─ backend/        FastAPI 后端、任务管理、音频处理、转写与格式化
├─ frontend/       Vue 3 + Vite 前端页面
└─ 运行全部.bat    一键启动前后端开发环境
```

## 技术栈

- 后端：FastAPI
- 前端：Vue 3 + Vite
- 语音识别：faster-whisper
- 音频处理：ffmpeg
- LLM：支持 `mock`、OpenAI 兼容接口、DeepSeek

## 快速开始

### 1. 克隆项目

HTTPS：

```bash
git clone https://github.com/hbx2004/interview-markdown-agent.git
cd interview-markdown-agent
```

SSH：

```bash
git clone git@github.com:hbx2004/interview-markdown-agent.git
cd interview-markdown-agent
```

### 2. 安装系统前置环境

在运行本项目之前，请确保本机已经安装以下环境：

- `Python 3.11+`
- `Node.js 18+`
- `ffmpeg`
- 可选：NVIDIA 驱动与 CUDA 运行环境（仅在使用 GPU 转写时需要）

说明：

- `Python` 和 `Node.js` 不会由项目脚本自动安装
- `ffmpeg` 也需要提前安装并加入系统环境变量
- 项目脚本只负责安装“项目依赖”，不会安装系统级运行环境

### 3. 启动后端

推荐使用后端封装脚本：

```powershell
cd backend
.\scripts\backend.ps1 install
.\scripts\backend.ps1 dev
```

如果更习惯双击运行，也可以直接使用以下脚本：

- [install.bat](/Users/hbx/Desktop/面试agent/backend/scripts/install.bat)
- [dev.bat](/Users/hbx/Desktop/面试agent/backend/scripts/dev.bat)
- [test.bat](/Users/hbx/Desktop/面试agent/backend/scripts/test.bat)

后端默认地址：

```text
http://127.0.0.1:8000
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

后端脚本会自动完成以下内容：

- 创建 `.venv` 虚拟环境
- 安装后端 Python 依赖
- 在需要时补装缺失依赖
- 自动准备 `.env` 文件模板

### 4. 启动前端

```powershell
cd frontend
npm install
npm run dev
```

也可以直接双击根目录下的 [运行全部.bat](/Users/hbx/Desktop/面试agent/运行全部.bat) 同时启动前后端开发环境。

前端命令会自动完成以下内容：

- 安装前端 `node_modules`
- 启动 Vite 开发服务器

## 环境配置

环境变量模板：

- [backend/.env.example](/Users/hbx/Desktop/面试agent/backend/.env.example)

首次使用时可以复制生成：

```powershell
cd backend
copy .env.example .env
```

### DeepSeek 配置示例

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

### OpenAI 配置示例

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key
LLM_MODEL=gpt-4o-mini
```

### GPU 转写配置示例

```env
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
WHISPER_MODEL_SIZE=small
```

如果不使用 GPU，可改为：

```env
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

## 运行要求

### 系统前置要求

- 已安装 `Python 3.11+`
- 已安装 `Node.js 18+`
- 已安装 `ffmpeg`
- 如需 GPU 转写，需正确安装 NVIDIA 驱动与 CUDA 运行环境
- 如需使用真实 LLM，需在 `.env` 中配置对应的 API Key

### 项目脚本会自动完成的内容

- 创建后端虚拟环境 `.venv`
- 安装后端 Python 依赖
- 安装前端依赖
- 初始化 `.env` 模板文件

### 项目脚本不会自动完成的内容

- 安装 `Python`
- 安装 `Node.js`
- 安装 `ffmpeg`
- 安装显卡驱动和 CUDA
- 申请或配置 DeepSeek / OpenAI API Key

## 处理流程

系统整体处理流程如下：

1. 前端上传音频或视频文件
2. 后端校验文件类型与大小
3. 使用 `ffmpeg` 提取并规范化音频
4. 使用 `faster-whisper` 生成原始转写文本
5. 使用 LLM 对文本进行角色区分、纠错和 Markdown 整理
6. 基于整理后的正文补充“面试总结”和“可提升点”
7. 保存中间产物与最终结果文件
8. 前端轮询任务状态并展示结果

## 输出内容

每个任务通常会生成以下产物：

- 原始上传文件
- 规范化后的音频文件
- 原始转写文本 `transcript.txt`
- 整理后的 Markdown 文档 `interview.md`
- 任务元数据 `job.json`
- 失败时的错误日志 `error.log`

默认存储目录位于：

- [backend/data/jobs](/Users/hbx/Desktop/面试agent/backend/data/jobs)

最终生成的 Markdown 一般包含以下内容：

- 按主题整理后的面试正文
- `## 面试总结`
- `## 可提升点`

## 测试

执行后端测试：

```powershell
cd backend
.\scripts\backend.ps1 test
```

或直接双击：

- [test.bat](/Users/hbx/Desktop/面试agent/backend/scripts/test.bat)

## 当前范围

- 当前版本主要优化中文技术面试场景
- 当前角色区分依赖 LLM 基于上下文推断，不包含真正的 diarization 说话人分离模型
- 当前重点是“整理成稿 + 总结建议”，不包含自动打分或正式面试评估结论

## 规划方向

- 原始转写稿 / 整理稿双视图
- 更细粒度的任务阶段和状态提示
- 更稳定的主题聚合与段落整理策略
- 面试摘要、问题分类与亮点提取
- 人工校对与角色修正能力
