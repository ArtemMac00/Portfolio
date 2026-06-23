from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from ai_service import analyze_code
import uvicorn

app = FastAPI(
    title="Code Reviewer API",
    description="ИИ-ревьюер кода на основе Agnes AI",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class CodeRequest(BaseModel):
    code: str
    language: str = "python"

class Issue(BaseModel):
    severity: str
    line: Optional[int] = None
    message: str
    suggestion: str

class ReviewResponse(BaseModel):
    summary: str
    score: float
    issues: list
    best_practices: list
    optimized_code: str
    security: list

@app.get("/")
def root():
    return {"message": "Code Reviewer API", "status": "running", "version": "2.0.0"}

@app.post("/analyze", response_model=ReviewResponse)
def analyze(request: CodeRequest):
    if not request.code or len(request.code.strip()) < 5:
        raise HTTPException(400, "Код слишком короткий или пустой")
    
    result = analyze_code(request.code, request.language)
    
    required_fields = ["summary", "score", "issues", "best_practices", "optimized_code", "security"]
    for field in required_fields:
        if field not in result:
            result[field] = [] if field not in ["summary", "optimized_code"] else "Нет данных"
    
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)