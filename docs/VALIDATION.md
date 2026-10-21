# Release validation

- 源码来自当前 ResearchLens 工作目录，不含运行中的数据库和虚拟环境。
- `backend/.env.example` 只包含空值和公开默认地址。
- `.gitignore` 排除 `.env`、SQLite 数据库、上传材料、视频输出、日志和 Python 缓存。
- 发布前应执行 `python -m py_compile *.py` 和离线测试。
- 真实 PubMed/OpenAlex/模型/语音请求需要用户自行配置服务和额度，本包不提供在线服务凭据。

2026-10-20 发行检查：所有 Python 源文件通过语法解析，7 项离线测试通过；缺少商业指标表时正常返回空数据。未验证全新环境安装或真实联网调用。

2026-10-21 原站更新检查：在独立 Python 3.12.14 环境按 backend/requirements.txt 及其锁定约束安装成功；7 项离线回归测试通过，所有后端 Python 文件编译、node --check app.js、sh -n backend/start.sh 通过。线上继续使用既有 Python 3.12.12、原仓库和原 Render 服务配置；入口链接保持 https://researchlens-l1js.onrender.com/ 。未调用付费模型、语音接口，也未将离线模拟测试当作真实检索验证。docs/SHA256.json 对应本次部署源码（不含清单自身）。
