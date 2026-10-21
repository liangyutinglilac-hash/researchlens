# ResearchLens · 学生科研伙伴

在线工作台：https://researchlens-l1js.onrender.com/ （沿用原 Render 服务；免费实例空闲后首次访问需要等待启动，账号和资料使用临时存储，可能在重启或重新部署后丢失。）

ResearchLens 是一个面向学生的文献理解与科研准备原型：从检索真实文献、阅读文字型 PDF，到证据核对、科研项目整理、站内文献日报和科普视频脚本/动画。

本仓库是可公开发布的源码包，不包含个人数据库、上传材料、生成视频、虚拟环境或任何 API Key。它包含一个无需构建的静态入口，以及 `backend/` 中的 Streamlit/Python 完整工作台。

## 先看静态入口

直接打开 `index.html`，或在项目根目录运行：

```bash
python3 -m http.server 8080
```

然后访问 `http://127.0.0.1:8080`。静态页面只把关键词跳转到 PubMed/OpenAlex，并把草稿保存在当前浏览器，不会调用模型或上传密钥。

## 启动完整工作台

需要 Python 3.12 和可用的 FFmpeg 运行环境（视频功能使用 `imageio-ffmpeg`）：

```bash
cd backend
python3.12 -m venv .venv-py312
source .venv-py312/bin/activate
python -m pip install -r requirements.txt
sh start.sh
```

打开 `http://127.0.0.1:8501`。如果 8501 被占用，可使用 `RESEARCHLENS_PORT=8502 sh start.sh`。

Windows PowerShell：

```powershell
cd backend
py -3.12 -m venv .venv-py312
.venv-py312\Scripts\python.exe -m pip install -r requirements.txt
.venv-py312\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

可以复制 `backend/.env.example` 为 `backend/.env`，或在侧栏填写配置。OpenAI 兼容服务需要同时匹配 API Key、Base URL 和模型名；OpenAlex Key 只用于 OpenAlex 检索，不能替代模型 Key。不要将真实 `.env`、数据库或个人论文提交到仓库。

## 功能和边界

- PubMed/OpenAlex 文献检索、缓存、收藏、文字型 PDF 提取、AI 解读和追问。
- 按账号隔离的项目、证据库、研究概览、方案快照和任务。
- PubMed 站内文献日报；本地进程停止期间不会更新。
- 科普脚本、字幕和轻量内容动画视频；配音取决于配置的语音接口或本机能力。
- 期刊指标需要有权使用的 CSV；期刊指标不等于单篇论文质量。

扫描 PDF 暂无 OCR，检索和模型服务受网络、配额和第三方接口状态影响。模型输出、证据关系和研究建议必须人工核验，不能替代导师审核、伦理审批、生物安全审查或临床决策。

## 数据与部署

默认数据库是 `backend/papers.db`，首次启动自动创建。可以设置 `RESEARCHLENS_DB_PATH` 指向可写目录。现有线上服务沿用仓库根目录的 `render.yaml`；部署说明见 `backend/DEPLOY.md`。公开演示环境由访问者在侧栏填写自己的模型或 OpenAlex Key，不设置共享服务密钥。PubMed 基础检索无需 OpenAlex Key。免费临时实例不适合保存个人或未发表材料，长期使用需要另行配置持久化存储。

## 开源发布清单

1. 在 GitHub/Gitee 创建仓库，把 `ResearchLens/` 内容上传到仓库根目录。
2. 保留 `.gitignore`，确认没有 `.env`、`papers.db`、`uploads/`、`video_outputs/`、日志和 API Key。
3. 保留 MIT `LICENSE`；论文、期刊指标、商标、字体和第三方依赖仍受各自许可约束。
4. 发布前使用自己的服务凭据和数据目录，不要公开活动 API Key 或学生上传的论文。

## 验证

```bash
cd backend
python -m py_compile *.py
python -m unittest discover -s . -p 'test_*.py'
```

测试覆盖离线检索解析和安全边界；不保证外部 API、额度或语音服务在线可用。
