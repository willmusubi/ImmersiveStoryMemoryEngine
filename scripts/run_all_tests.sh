#!/bin/bash
# 运行所有测试

echo "=========================================="
echo "🧪 Immersive Story Memory Engine - 完整测试套件"
echo "=========================================="

cd "$(dirname "$0")/.."
source venv/bin/activate

echo ""
echo "1️⃣  运行单元测试..."
python -m pytest tests/unit/ -v --tb=short

echo ""
echo "2️⃣  运行集成测试..."
python -m pytest tests/integration/ -v --tb=short

echo ""
echo "3️⃣  运行完整工作流测试（需要 LLM）..."
echo "⚠️  这将调用真实的 LLM API，会消耗配额"
read -p "是否继续？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python scripts/test_full_workflow.py
fi

echo ""
echo "=========================================="
echo "✅ 测试完成！"
echo "=========================================="

