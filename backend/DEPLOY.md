# 部署说明

从 backend 目录安装 requirements.txt，然后运行 `python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501`。

部署平台的环境变量中配置模型 Key、Base URL 和模型名，不要提交真实凭据。通过 RESEARCHLENS_DB_PATH 配置持久化 SQLite 路径，数据库和同级 video_outputs 需要持久保存。

现有线上网址为 https://researchlens-l1js.onrender.com/ ，GitHub main 分支更新 backend 后由原 Render 服务自动重新部署。使用仓库根目录 render.yaml，部署根目录设为 backend；本目录 render.yaml 仅为同等启动配置的参考，不需要再创建服务。保持 Python 3.12.12 和现有代理参数。

云端中文动画需要中文字体。临时实例可能休眠或丢失本地数据，日报更新需要持续运行。公开演示环境由访问者输入个人服务 Key，不配置共享模型密钥；长期使用需要持久化存储并审查用户材料权限。
