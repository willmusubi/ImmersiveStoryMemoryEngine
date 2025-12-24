"""
启动 FastAPI 服务
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 直接导入 app 对象，避免字符串路径问题
from backend.api.routes import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        app,  # 直接传递 app 对象
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

