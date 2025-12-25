"""
启动 FastAPI 服务
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import uvicorn

if __name__ == "__main__":
    # 使用导入字符串以支持 reload 功能
    uvicorn.run(
        "backend.api.routes:app",  # 导入字符串格式
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

