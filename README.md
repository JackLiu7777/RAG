# Local RAG Demo

一个本地通用 RAG 系统：上传 txt/word/pdf/csv → 切分 → 向量化存 FAISS + BM25 → 多路召回 + Rerank → 调 LLM 回答。

## 快速开始（Step 1）

```powershell
# 1. 进入项目目录
cd C:\Users\26819\Desktop\RAG-Demo

# 2. 创建并激活虚拟环境
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. 安装依赖
pip install -r requirements.txt

# 4. 复制环境变量模板
Copy-Item .env.example .env
# 然后编辑 .env，把智谱 API Key 填进去

# 5. 启动服务（注意要先 cd 进 backend）
cd backend
uvicorn app.main:app --reload

# 6. 浏览器打开
#    http://127.0.0.1:8000/health       看健康检查
#    http://127.0.0.1:8000/docs         看自动生成的接口文档
```
