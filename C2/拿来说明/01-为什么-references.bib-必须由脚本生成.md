# 拿来说明 01 · 为什么 `references.bib` 必须由脚本生成

> **一句话**：手写 bib 把「作者」「会议名」变成了没人检查的自由文本。
> 这次差点因此给一条引用挂上一场它根本没发表过的会议。

---

## 一、背景

任务书要求 `references.bib`（≥ 8 篇，含一手文献），红线是「引用造假 → 研究严谨性 0 分」。

**核验标题是容易的**——标题在页面上，一比就知道。
**但作者列表和会议名呢？** 它们同样是引用的一部分，同样可以造假，
而且**更不容易被发现**——因为大多数人核引用只核标题和年份。

## 二、第一版做法（错的）

我写了一个函数 `pick_published()`：
在 OpenAlex 返回的 top-5 候选里，找那条「已正式发表」的记录（类型是
`conference-paper` 或 `article`），拿它的会议名和 DOI 填进 bib。

**逻辑上很自然**：既然 OpenAlex 说这篇论文发表在某某会议，那就用它的。

## 三、产出：一个自相矛盾的结果

生成的 bib 里出现：

```
huang2024selfcorrect       ... doi = {10.18653/v1/2023.findings-acl.67}
stechly2024selfverification ... doi = {10.18653/v1/2023.findings-acl.67}
```

**两条不同的论文，共享同一个 DOI。**

这不可能对。查原始记录才看明白：这两条记录的「已发表版本」都来自
OpenAlex **按标题召回的 top-5 候选列表**——而那些候选里混进了不相关的论文。
`10.18653/v1/2023.findings-acl.67` 是真实存在的 DOI，只是**不属于这两篇**。

## 四、根因

**我拿的是一个「按相似度召回」的字段，却把它当成了「按主键查」的字段。**

这两种字段的可靠性差一个量级：

| 来源 | 检索方式 | 失效模式 |
|---|---|---|
| OpenAlex 搜索接口 | **按标题相似度召回** | 会返回长得像但不相干的记录；同一批候选里可能混入多篇不同论文 |
| Crossref `works/{doi}` | **按 DOI 主键直查** | 只可能有两种结果：查到这个 DOI，或查不到 |

前者返回的是「**可能是**这篇论文的记录」，后者返回的是「**这个 DOI 本身**的元数据」。

## 五、修复

放弃从 OpenAlex 拿出版信息，改成**拿 DOI 回 Crossref 反查**：

```python
def resolve_doi(doi):
    data = get(f"https://api.crossref.org/works/{doi}")
    return {
        "container": data["message"]["container-title"][0],   # 权威会议名
        "type":      data["message"]["type"],
        "year":      ...,
    }
```

效果（bib 中的实际输出）：

```
% 出版信息 Crossref(DOI反查)
@inproceedings{sainz2023contamination,
  booktitle = {Findings of the Association for Computational Linguistics: EMNLP 2023},
  doi       = {10.18653/v1/2023.findings-emnlp.722},
```

会议名 `Findings of ... EMNLP 2023` 是**这个 DOI 自己的**元数据，不可能错配。

## 六、更彻底的一步：bib 是生成物，不是手写物

修完这个 bug 之后，我把规则往前提了一步：

> **`references.bib` 的每一个字段都必须来自核验记录，人工只能显式覆盖且须写明理由。**

于是：

- `02_build_bib.py` 只做格式转换，不做判断；
- bib 文件头写明「**本文件是生成物，请勿手工编辑**」；
- 输出 SHA-256 到 `reports/references_bib_sha256.txt`；
- 跑一遍 `01 && 02` 应该得到**逐字节相同**的 bib。

## 七、对比

| | 手写 bib | 生成 bib |
|---|---|---|
| 作者列表来源 | 记忆／印象 | 核验命中的权威记录 |
| 会议名来源 | 记忆／印象 | Crossref 按 DOI 反查 |
| 出错时表现 | **静默**，没人会发现 | 要么生成不出来，要么留下证据 |
| 可复现性 | 无 | SHA-256 可逐字节复核 |
| 这条引用错没错 | 靠人肉抽查 | 核验记录里写着相似度、来源、DOI |

## 八、带走的一条规则

> **凡是从「搜索接口」来的字段，不得直接进入交付物。
> 必须用主键回到权威源复核。**

这条不限于文献。任何「从 API 拿数据」的场景都适用：

- 把 OpenAlex 的 `cited_by_count` 当作权威引用数（它按标题召回，可能数错篇）；
- 把 GitHub 的 `stars` 当作项目质量指标（它和论文质量无关）；
- 把搜索接口返回的「机构名」直接写进署名。

**判据一句话：这个字段是怎么被召回的？**
