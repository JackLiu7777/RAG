@echo off
cd /d C:\Users\26819\Desktop\RAG-Demo
call .venv\Scripts\activate.bat
cd backend
uvicorn app.main:app --reload
pause
