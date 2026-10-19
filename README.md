# ResearchLens · 学生科研伙伴

面向校园生物科研学习与研究准备的开源项目源码包。包含静态入口页和现有 Streamlit 应用源码。

**这是网站项目，不是模型权重包。** AI 能力通过用户自行配置的兼容模型接口提供。此包未将 Streamlit 重写为 JavaScript，也没有虚构 REST API。

## 目录

- `index.html`：网页入口，直接用浏览器打开。
- `styles.css`：响应式浅色界面，无外部字体或 CDN 依赖。
- `app.js`：真实文献平台检索跳转、浏览器本地草稿、Markdown 导出。
- `backend/`：完整 Python 应用源码与依赖、启动脚本。
- `LICENSE`：MIT 项目代码许可证；第三方依赖各自遵循原许可证。

## 两种使用方式

### 只预览静态网页

直接打开 `index.html`，或在项目根目录运行 `python3 -m http.server 8080` 后访问 http://127.0.0.1:8080 。可部署到静态托管平台。网页会把关键词带到 PubMed/OpenAlex 网站，不在浏览器中调用模型，也不保存密钥。草稿只保存在当前浏览器，不与账号同步。

### 运行完整工作台

建议 Python 3.12，macOS / Linux：

```sh
cd backend
python3.12 -m venv .venv-py312
source .venv-py312/bin/activate
python -m pip install -r requirements.txt
sh start.sh
```

打开 http://127.0.0.1:8501 ，首次注册自己的账号（密码至少 12 位）。`sh start.sh` 无需脚本可执行权限。先启动后端，再点击网页右上角“打开完整工作台”。静态入口和工作台是两个界面，入口不会自动调用 Python 函数。

Windows PowerShell：

```powershell
cd backend
py -3.12 -m venv .venv-py312
.venv-py312\Scripts\python.exe -m pip install -r requirements.txt
.venv-py312\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

在应用侧栏填写个人 OpenAlex Key 和模型服务配置；也可把 `backend/.env.example` 复制为 `backend/.env` 后编辑。模型 Key 与 OpenAlex Key 属于不同服务，不能混用。使用兼容网关时，需确认 Base URL、模型名及账户额度；第三方活动额度另受其使用条款限制。不要提交真实 `.env`。

## 完整工作台功能和边界

- OpenAlex 文献检索、收藏、文字型 PDF 提取，模型解读与追问；扫描 PDF 不提供 OCR。
- 个人科研项目、渐进引导、确认写入建议、方案快照、任务状态。
- PubMed 站内日报；`start.sh` 启动独立更新进程，终端停止后更新也停止。没有邮件推送。
- 科普脚本、字幕与轻量动画 MP4。视频渲染依赖 FFmpeg（imageio-ffmpeg），配音依赖可用模型语音接口、本机语音或可选在线服务；音频可用性不能保证，无配音时按应用提示处理。没有虚拟讲解小人或模型权重。
- 账号与 SQLite 持久化；首次运行会创建新数据库。本包没有原用户、收藏或历史项目。
- 不附带 JCR 商业指标表；已修正发行副本的缺表回退。导入有权使用的 CSV 后才能按 JIF 筛选。期刊指标不能替代论文质量判断。
- 检索依赖网络与提供方额度；限流时可使用缓存、PDF、已保存材料。模型未配置时部分功能仅提供基础非 AI 引导。

## 发布为开源项目

1. 创建自己的 GitHub / Gitee 仓库，把本目录内容上传到仓库根目录。
2. 保留 `.gitignore`；确认提交中没有密钥、数据库、日志、上传材料及生成视频。
3. 阅读并确认 `LICENSE` 中的 MIT 代码授权；本许可证不授权第三方文献、数据、商标及依赖。公开前确认你有权发布所包含源码。
4. 如只部署静态页，完整工作台按钮仍指向访问者自己的本机，不能提供远程科研服务。部署完整 Python 应用后，请修改 `index.html` 中的工作台链接。
5. 完整应用公开部署需自行配置持久化磁盘、服务凭据和进程管理；本包不包含生产部署完成的承诺。

### Render 部署

仓库包含 `render.yaml`，可在 Render 创建免费 Web Service 后从该文件导入配置。服务会启动完整 Streamlit 工作台；Render 会自动提供 `PORT`，无需手动设置。免费实例空闲时会休眠，首次访问可能需要等待片刻。

公开演示环境使用临时 SQLite 存储，不应保存真实研究资料、账号密码或任何密钥。请在工作台页面中自行输入模型和 OpenAlex 服务的个人 Key；不要将它们提交到仓库或配置为公开演示环境的共享变量。

科研建议须由导师或专业人员审阅；预期应用成效不代表已完成规模化验证。

## 发行验证

本包按文件白名单构建；Python 语法、静态脚本及交互逻辑检查的范围与限制见 `docs/VALIDATION.md`。不包含在线模型、实际配音或外部检索成功的保证。
