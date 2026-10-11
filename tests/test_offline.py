# -*- coding: utf-8 -*-
"""
离线端到端测试。

不联网、不需要 API key：把 LLM 与检索都 mock 掉，跑通完整四步流程，
然后对生成的报告内容做断言。

运行：
    python tests/test_offline.py
"""
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "skill" / "scripts" / "collision_agent.py"
OUT = ROOT / "tests" / "_out"

spec = importlib.util.spec_from_file_location("collision_agent", SRC)
ca = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ca)

# ---------------------------------------------------------------- mock 数据

CLAIMS = {"claims": [
    {"id": 1, "claim": "用遮蔽反馈判定某次提问是否冗余",
     "queries": ["masked feedback redundancy", "counterfactual question necessity"]},
    {"id": 2, "claim": "在硬预算约束下选择何时提问",
     "queries": ["budget constrained clarification"]},
]}
ASSESS_1 = {"verdict": "部分重叠",
            "they_did": "生成两个自造答案条件下的程序，比较执行输出差异",
            "they_did_not": "没有遮蔽真实用户反馈；判定的是候选问题而非已发生的提问",
            "confidence": "中", "evidence_ids": [1, 2]}
ASSESS_2 = {"verdict": "已被占据",
            "they_did": "CMDP + 期望提问预算 + Pareto 前沿",
            "they_did_not": "预算只在训练期施加，评测时自由生成；需要 PPO 训练",
            "confidence": "高", "evidence_ids": [1, 99]}   # 99 越界，测防护
DIFF = {"differentiation": "差异点落在主张 1：用真实用户反馈做遮蔽，判定对象是已发生的提问",
        "anchor_claim": "1",
        "next_steps": ["先核实被引论文是否真没做遮蔽反馈", "确认评测数据可用"],
        "risk": "中", "risk_note": "约束形式不同，硬 k + 免训练仍开放"}

calls = []


def fake_llm(messages, temperature=0.2):
    sp = messages[0]["content"]
    if "可独立检索" in sp:
        calls.append("decompose")
        return json.dumps(CLAIMS, ensure_ascii=False)
    if "审查员" in sp:
        calls.append("assess")
        return json.dumps(ASSESS_1 if "遮蔽反馈" in messages[1]["content"] else ASSESS_2,
                          ensure_ascii=False)
    if "策略顾问" in sp:
        calls.append("differentiate")
        return json.dumps(DIFF, ensure_ascii=False)
    raise AssertionError("收到未预期的 prompt")


def fake_retrieve(query, per_source=8, since=None):
    # 标题里故意放方括号，测 markdown 转义
    return [
        {"source": "arXiv", "title": "CONTRA: Behavior-Changing Questions [v1]",
         "year": "2026", "url": "https://arxiv.org/abs/2610.01769", "abstract": "a" * 40},
        {"source": "OpenAlex", "title": "Pareto-Dominant Clarification",
         "year": "2026", "url": "https://arxiv.org/abs/2610.04089", "abstract": "b" * 40},
    ]


def main():
    ca.llm = fake_llm
    ca.retrieve = fake_retrieve
    os.environ["OPENAI_API_KEY"] = "test-key"
    if OUT.exists():
        shutil.rmtree(OUT)
    sys.argv = ["collision_agent.py", "--outdir", str(OUT), "--since", "2024",
                "--idea", "把一次提问的用户反馈遮蔽掉，比较 agent 动作分布是否改变"]

    ca.main()

    reports = sorted(OUT.glob("CC-*.md"))
    assert reports, "没有生成报告文件"
    text = reports[-1].read_text(encoding="utf-8")
    next_steps_block = text.split("下一步：")[-1] if "下一步：" in text else ""

    checks = [
        ("拆解被调用", calls.count("decompose") == 1),
        ("两条主张各判定一次", calls.count("assess") == 2),
        ("差异化假设被调用", calls.count("differentiate") == 1),
        ("顶部禁令在位", "二值结论" in text),
        ("三栏判定出现在报告里", "部分重叠" in text and "已被占据" in text),
        ("他们做了什么/没做什么都在", "他们做了什么" in text and "他们没做什么" in text),
        ("差异化假设已写入", "差异点落在主张 1" in text),
        ("方括号被转义", r"\[v1\]" in text),
        ("越界的 evidence_id 被忽略且不崩", "99" not in text),
        ("回访日期为 +90 天", "2027-01-09" in text),
        ("报告编号精确到秒", len(reports[-1].stem) == len("CC-20261011-123456")),
        ("检索记录分检索式报数", "counterfactual question necessity" in text),
        ("下一步序号递增", "1. 先核实" in next_steps_block and "2. 确认" in next_steps_block),
    ]
    bad = [n for n, okv in checks if not okv]
    for n, okv in checks:
        print(("  OK   " if okv else "  FAIL ") + n)
    print()
    if bad:
        print("失败项：", bad)
        return 1
    print("全部通过。报告：%s（%d 字节）" % (reports[-1].name, len(text.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    code = main()
    if OUT.exists():
        shutil.rmtree(OUT, ignore_errors=True)
    sys.exit(code)
