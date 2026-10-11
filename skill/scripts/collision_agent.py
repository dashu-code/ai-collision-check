#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
撞车检测 Agent
==============

按四步规格运行。**硬性规则：不输出"撞车 / 没撞车"的二值结论。**

  步骤 1  拆主张      把研究方向拆成 3-5 条可检索的 claim（整段描述检索效果很差）
  步骤 2  多路检索    arXiv / OpenAlex / Semantic Scholar
  步骤 3  三栏判定    已被占据 / 部分重叠 / 空白
                      每一栏都必须写清「他们做了什么」和「他们没做什么」
  步骤 4  差异化假设  强制产出"我的差异点落在哪一行"，必须对应到具体证据

设计目的见《下一步_撞车检测的工作流与产品设计.md》第四节。
这条规则存在的唯一原因：防止"只看了标题就放弃"的误杀。

------------------------------------------------------------
环境变量（LLM 部分可选，兼容任何 OpenAI 协议的端点）

  OPENAI_API_KEY      必填才能做判定；不填则退化为"只检索"
  OPENAI_BASE_URL     默认 https://api.openai.com/v1
                      DeepSeek:  https://api.deepseek.com/v1
                      通义:      https://dashscope.aliyuncs.com/compatible-mode/v1
                      智谱:      https://open.bigmodel.cn/api/paas/v4
  COLLISION_MODEL     默认 gpt-4o-mini；DeepSeek 用 deepseek-chat
  OPENALEX_MAILTO     可选，填邮箱可进 OpenAlex 的 polite pool，请求更稳

用法
  python collision_agent.py --idea "把一次提问的用户反馈遮蔽掉，比较动作分布是否改变"
  python collision_agent.py --file direction.md
  python collision_agent.py --idea "..." --no-llm     # 只检索，不判定
  python collision_agent.py --idea "..." --since 2023 # 只看 2023 年以后的文献
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------- 基础工具

UA = "collision-agent/1.0 (research use; contact via OpenAlex mailto)"


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def _post_json(url, payload, headers, timeout=120):
    data = json.dumps(payload).encode("utf-8")
    h = {"Content-Type": "application/json", "User-Agent": UA}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------- 检索源

def arxiv_search(query, max_results=8, since=None):
    """arXiv Atom API。不需要 key。"""
    q = f'all:"{query}"'
    url = (
        "http://export.arxiv.org/api/query?"
        + urllib.parse.urlencode(
            {"search_query": q, "start": 0,
             "max_results": max_results, "sortBy": "relevance"}
        )
    )
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(_get(url))
    out = []
    for e in root.findall("a:entry", ns):
        published = (e.findtext("a:published", "", ns) or "")[:10]
        year = published[:4]
        if since and year.isdigit() and int(year) < since:
            continue
        out.append({
            "source": "arXiv",
            "title": " ".join((e.findtext("a:title", "", ns) or "").split()),
            "year": year,
            "url": e.findtext("a:id", "", ns),
            "abstract": " ".join((e.findtext("a:summary", "", ns) or "").split())[:900],
        })
    return out


def openalex_search(query, max_results=8, since=None):
    """OpenAlex。免费，无需 key；填 mailto 更稳。"""
    params = {
        "search": query,
        "per-page": max_results,
        "sort": "relevance_score:desc",
    }
    if since:
        params["filter"] = f"from_publication_date:{since}-01-01"
    mailto = os.environ.get("OPENALEX_MAILTO")
    if mailto:
        params["mailto"] = mailto
    data = json.loads(_get("https://api.openalex.org/works?" + urllib.parse.urlencode(params)))
    out = []
    for w in data.get("results", []):
        inv = w.get("abstract_inverted_index") or {}
        abstract = ""
        if inv:
            pos = {}
            for word, idxs in inv.items():
                for i in idxs:
                    pos[i] = word
            abstract = " ".join(pos[k] for k in sorted(pos))[:900]
        loc = (w.get("primary_location") or {}).get("source") or {}
        out.append({
            "source": "OpenAlex",
            "title": w.get("title") or "",
            "year": str(w.get("publication_year") or ""),
            "url": w.get("doi") or w.get("id") or "",
            "venue": loc.get("display_name") or "",
            "abstract": abstract,
        })
    return out


def s2_search(query, max_results=8, since=None):
    """Semantic Scholar Graph API。免费但会限流。"""
    params = {
        "query": query,
        "limit": max_results,
        "fields": "title,abstract,year,venue,externalIds",
    }
    if since:
        params["year"] = f"{since}-"
    data = json.loads(_get("https://api.semanticscholar.org/graph/v1/paper/search?"
                           + urllib.parse.urlencode(params)))
    out = []
    for p in data.get("data", []):
        ext = p.get("externalIds") or {}
        url = f"https://arxiv.org/abs/{ext['ArXiv']}" if ext.get("ArXiv") else (
            f"https://doi.org/{ext['DOI']}" if ext.get("DOI") else "")
        out.append({
            "source": "S2",
            "title": p.get("title") or "",
            "year": str(p.get("year") or ""),
            "url": url,
            "venue": p.get("venue") or "",
            "abstract": (p.get("abstract") or "")[:900],
        })
    return out


SOURCES = [("arXiv", arxiv_search), ("OpenAlex", openalex_search), ("S2", s2_search)]


def retrieve(query, per_source=8, since=None):
    """多路检索，任一源失败不影响其他源。"""
    hits, seen = [], set()
    for name, fn in SOURCES:
        try:
            for h in fn(query, per_source, since):
                key = re.sub(r"\W+", "", (h.get("title") or "").lower())[:80]
                if key and key not in seen:
                    seen.add(key)
                    hits.append(h)
        except Exception as e:  # noqa: BLE001
            log(f"  ! {name} 检索失败：{e}")
        time.sleep(0.6)  # 对公共 API 客气一点
    return hits


# ---------------------------------------------------------------- LLM

def llm(messages, temperature=0.2):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("COLLISION_MODEL", "gpt-4o-mini")
    resp = _post_json(
        f"{base}/chat/completions",
        {"model": model, "messages": messages, "temperature": temperature},
        {"Authorization": f"Bearer {key}"},
    )
    return resp["choices"][0]["message"]["content"]


def llm_json(messages, temperature=0.2):
    """要 JSON 的地方统一走这里，容忍模型加 markdown 围栏。"""
    raw = llm(messages, temperature)
    if raw is None:
        return None
    txt = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    m = re.search(r"[\[{].*[\]}]", txt, re.S)
    if not m:
        raise ValueError(f"模型没有返回可解析的 JSON：{raw[:300]}")
    return json.loads(m.group(0))


# ---------------------------------------------------------------- 步骤 1：拆主张

DECOMPOSE_SYS = """你是科研选题分析助手。把用户的研究方向拆成 3-5 条**可独立检索**的主张。

要求：
- 每条主张是一个具体的、能被文献检索验证的技术陈述，不是泛泛的方向描述。
- 主张要覆盖：核心方法、评测方式、应用场景、约束条件。
- 为每条主张另给 1-2 条英文检索式（arXiv/OpenAlex 对英文更友好）。

只输出 JSON，格式：
{"claims":[{"id":1,"claim":"中文主张","queries":["english query 1","english query 2"]}]}"""


def decompose(direction):
    data = llm_json([
        {"role": "system", "content": DECOMPOSE_SYS},
        {"role": "user", "content": direction},
    ])
    claims = data.get("claims", []) if isinstance(data, dict) else []
    if not claims:
        raise ValueError("拆解失败：没有拿到任何主张")
    return claims[:5]


# ---------------------------------------------------------------- 步骤 3：三栏判定

ASSESS_SYS = """你是严格但诚实的科研撞车审查员。给你一条研究主张和一批检索到的文献。

**最重要的规则：绝对不要输出"撞车 / 没撞车"这种二值结论。** 必须做三分类：

- "已被占据"：有文献在**同一个问题、同一类方法**上做过了。
- "部分重叠"：主题相关，但**场景 / 数据 / 约束 / 代价 / 评测方式**不同。
- "空白"：检索结果里没有实质相关的工作。

对每一条判定，你**必须**分别写出「他们做了什么」和「他们没做什么」。
"他们没做什么"是这份报告的产出核心——它是作者差异化空间的来源。
如果证据不足以判断，就写"证据不足"，不要硬判。

同时注意：只看了标题/关键词重合**不足以**判定"已被占据"，必须有方法层面的重合。宁可判"部分重叠"。

只输出 JSON：
{"verdict":"已被占据|部分重叠|空白",
 "they_did":"他们做了什么（具体到方法）",
 "they_did_not":"他们没做什么（具体到缺口）",
 "confidence":"高|中|低",
 "evidence_ids":[1,3]}"""


def assess(claim, hits):
    if not hits:
        return {"verdict": "空白", "they_did": "未检索到相关工作",
                "they_did_not": "该主张对应的完整设计空间似乎仍然开放",
                "confidence": "中", "evidence_ids": []}
    listing = []
    for i, h in enumerate(hits, 1):
        listing.append(
            f"[{i}] {h['title']} ({h.get('year','?')}, {h.get('source','')})\n"
            f"    URL: {h.get('url','')}\n"
            f"    摘要: {(h.get('abstract') or '（无摘要）')[:700]}"
        )
    data = llm_json([
        {"role": "system", "content": ASSESS_SYS},
        {"role": "user", "content":
            f"研究主张：{claim}\n\n检索到的文献：\n" + "\n\n".join(listing)},
    ])
    if not isinstance(data, dict):
        raise ValueError("判定返回格式异常")
    data.setdefault("evidence_ids", [])
    return data


# ---------------------------------------------------------------- 步骤 4：差异化假设

DIFF_SYS = """你是科研选题策略顾问。基于逐条判定结果，给出**差异化假设**。

要求：
1. 明确指出：如果作者要推进这个方向，差异点应该落在哪一条主张上，以及为什么。
2. 差异点必须对应到具体的证据（哪篇文献"没做什么"）。
3. 给出 2-3 个**可执行的下一步**（例如"先核实 X 是否真的没做"）。
4. 诚实标注风险：如果整个方向已经被做透，就直接说，并建议转向。

不要写鼓励的话。只输出 JSON：
{"differentiation":"差异化假设（一段话）",
 "anchor_claim":"主要落点对应的主张 id 或编号",
 "next_steps":["...","..."],
 "risk":"低|中|高：整个方向被做透的程度",
 "risk_note":"一句话说明"}"""


def differentiate(direction, claims, assessments):
    blocks = []
    for c, a in zip(claims, assessments):
        blocks.append(
            f"主张 {c.get('id')}：{c.get('claim')}\n"
            f"  判定：{a.get('verdict')}\n"
            f"  他们做了什么：{a.get('they_did')}\n"
            f"  他们没做什么：{a.get('they_did_not')}"
        )
    data = llm_json([
        {"role": "system", "content": DIFF_SYS},
        {"role": "user", "content":
            f"研究方向：\n{direction}\n\n逐条判定：\n" + "\n\n".join(blocks)},
    ])
    return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------- 报告

def render(direction, claims, evidence, assessments, diff, since, used_llm):
    now = datetime.now()
    rid = f"CC-{now:%Y%m%d-%H%M}"
    L = [f"# 撞车检测报告 {rid}", "",
         f"生成时间：{now:%Y-%m-%d %H:%M}　|　文献窗口：{since or '不限'} 年至今　|　"
         f"LLM 判定：{'开启' if used_llm else '关闭（仅检索）'}", "",
         "> 本报告不输出“撞车 / 没撞车”的二值结论。每条判定都必须写明「他们做了什么」和「他们没做什么」。",
         "", "## 输入：研究方向", "", "```", direction.strip(), "```", ""]

    if used_llm and claims:
        L += ["## 一、拆解出的主张", ""]
        for c in claims:
            L.append(f"{c.get('id')}. **{c.get('claim')}**")
            for q in c.get("queries", []):
                L.append(f"   - 检索式：`{q}`")
        L.append("")

        L += ["## 二、逐条判定", ""]
        for c, a in zip(claims, assessments):
            L += [f"### 主张 {c.get('id')}：{c.get('claim')}", "",
                  f"**判定：`{a.get('verdict','?')}`**（置信度：{a.get('confidence','?')}）", "",
                  f"- **他们做了什么**：{a.get('they_did','')}",
                  f"- **他们没做什么**：{a.get('they_did_not','')}", ""]
            ids = a.get("evidence_ids") or []
            ev = evidence.get(c.get("id"), [])
            if ids:
                L.append("证据：")
                for i in ids:
                    if isinstance(i, int) and 1 <= i <= len(ev):
                        h = ev[i - 1]
                        L.append(f"  - [{h['title']}]({h.get('url','')}) "
                                 f"({h.get('year','?')}, {h.get('source','')})")
                L.append("")

        L += ["## 三、差异化假设", "",
              f"**{diff.get('differentiation','（未生成）')}**", "",
              f"- 主要落点：主张 {diff.get('anchor_claim','?')}",
              f"- 整体风险：**{diff.get('risk','?')}** —— {diff.get('risk_note','')}", "",
              "下一步："]
        for s in diff.get("next_steps", []) or ["（未生成）"]:
            L.append(f"1. {s}")
        L.append("")
    else:
        L += ["## 检索结果（未做判定）", ""]
        for c in claims:
            L.append(f"### 主张 {c.get('id')}：{c.get('claim')}")
            qs = "、".join(f"`{q}`" for q in c.get("queries", []))
            L.append(f"检索式：{qs}")
            L.append("")
            for h in evidence.get(c.get("id"), []):
                L.append(f"- [{h['title']}]({h.get('url','')}) "
                         f"({h.get('year','?')}, {h.get('source','')})")
            L.append("")

    L += ["## 四、回填想法日志", "",
          "把下面这一行填进 `想法日志.md`（`检查结论` 一列按三栏判定填写，"
          "**不要**把“部分重叠”归成“真撞车”）：", "",
          "| 编号 | 日期 | 想法一句话 | 类型 | 撞车检查方式 | 检查结论 | 当时的情绪 | "
          "决定 | 回访日期 | 回访结论 | 备注 |",
          "|---|---|---|---|---|---|---|---|---|---|---|",
          f"| IL-XXX | {now:%Y-%m-%d} | （一句话） | | 本报告 {rid}"
          f"（arXiv/OpenAlex/S2，窗口 {since or '不限'}） | （真撞车/看起来像/没查到） | | | "
          f"{(now + timedelta(days=90)):%Y-%m-%d} | | |", "",
          "## 五、检索记录（复现用）", ""]
    for c in (claims or []):
        for q in c.get("queries", []):
            n = len(evidence.get(c.get("id"), []))
            L.append(f"- 主张 {c.get('id')} `{q}` → {n} 条")
    L.append("")
    return rid, "\n".join(L)


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser(description="撞车检测 Agent（不输出二值结论）")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--idea", help="直接给研究方向描述")
    src.add_argument("--file", help="从文件读取研究方向描述")
    ap.add_argument("--since", type=int, default=None,
                    help="只看该年份以后的文献，例如 2023")
    ap.add_argument("--per-source", type=int, default=8, help="每个源取几条，默认 8")
    ap.add_argument("--query", action="append", default=[],
                    help="手写英文检索式（可重复）。不接 LLM 时强烈建议提供——"
                         "arXiv / OpenAlex 对中文检索式几乎无效")
    ap.add_argument("--no-llm", action="store_true", help="只检索，不做判定")
    ap.add_argument("--outdir", default="reports", help="报告输出目录")
    args = ap.parse_args()

    direction = args.idea if args.idea else Path(args.file).read_text(encoding="utf-8")
    used_llm = (not args.no_llm) and bool(os.environ.get("OPENAI_API_KEY"))
    if not args.no_llm and not used_llm:
        log("未设置 OPENAI_API_KEY，降级为「只检索」模式")

    claims = None
    if used_llm and args.query:
        claims = [{"id": 1, "claim": direction.strip()[:200], "queries": args.query}]
        log(f"使用手写检索式，跳过拆解：{args.query}")
    elif used_llm:
        log("步骤 1：拆解主张 …")
        try:
            claims = decompose(direction)
            for c in claims:
                log(f"  - {c.get('id')}. {c.get('claim')}")
        except Exception as e:  # noqa: BLE001
            log(f"拆解失败，降级为只检索：{e}")
            used_llm = False

    if not used_llm:
        if args.query:
            claims = [{"id": 1, "claim": direction.strip()[:200],
                       "queries": args.query}]
        else:
            claims = [{"id": 1, "claim": direction.strip()[:200],
                       "queries": [" ".join(direction.split())[:180]]}]
            log("提示：未提供 --query 且输入为中文时，arXiv/OpenAlex 检索效果会很差"
                "（这两个源以英文为主）")

    log("步骤 2：多路检索 …")
    evidence, all_hits = {}, {}
    for c in claims:
        cid = c.get("id")
        bucket = []
        for q in c.get("queries", [])[:2]:
            hits = retrieve(q, args.per_source, args.since)
            log(f"  - 主张 {cid} `{q[:48]}…` → {len(hits)} 条")
            bucket.extend(hits)
        # 去重
        seen, uniq = set(), []
        for h in bucket:
            k = re.sub(r"\W+", "", (h.get("title") or "").lower())[:80]
            if k and k not in seen:
                seen.add(k)
                uniq.append(h)
        evidence[cid] = uniq
        all_hits[cid] = uniq

    assessments, diff = [], {}
    if used_llm:
        log("步骤 3：三栏判定 …")
        for c in claims:
            try:
                a = assess(c.get("claim"), evidence.get(c.get("id"), []))
            except Exception as e:  # noqa: BLE001
                log(f"  ! 主张 {c.get('id')} 判定失败：{e}")
                a = {"verdict": "证据不足", "they_did": "", "they_did_not": "",
                     "confidence": "低", "evidence_ids": []}
            assessments.append(a)
            log(f"  - 主张 {c.get('id')} → {a.get('verdict')}")

        log("步骤 4：差异化假设 …")
        try:
            diff = differentiate(direction, claims, assessments)
        except Exception as e:  # noqa: BLE001
            log(f"  ! 差异化假设生成失败：{e}")

    rid, text = render(direction, claims, evidence, assessments, diff,
                       args.since, used_llm)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"{rid}.md"
    path.write_text(text, encoding="utf-8")
    print(text)
    log(f"报告已写入：{path}")


if __name__ == "__main__":
    main()
