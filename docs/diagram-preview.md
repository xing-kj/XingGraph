# 能力图预览 · Diagram Preview

> 五种方案的预览集合。方案 C/D/E 是 SVG 文件（`assets/`），A/B 是 Mermaid 代码块。
> 看完后告诉我保留哪些、替换 README 里哪一节。

## 方案 A · Mermaid 七叶图（代码块）

```mermaid
flowchart LR
    XG["XingGraph<br/>七项能力"] --> A["可观测<br/>每步结构化 trace"]
    XG --> B["可回溯<br/>标题归因 + references"]
    XG --> C["可控制<br/>路由 / scope / 开关"]
    XG --> D["可扩展<br/>RDF 本体即扩展点"]
    XG --> E["可进化<br/>prompt/chunker + 反馈"]
    XG --> F["省 token<br/>白名单硬过滤 + 渐进式"]
    XG --> G["少幻觉<br/>原文 chunk + 证据绑定"]
```

## 方案 B · Mermaid 升级版（classDef 主题色）

```mermaid
flowchart TB
    classDef anchor fill:#2a1a55,stroke:#8b6bff,color:#fff
    classDef step   fill:#1a1530,stroke:#6b4fb0,color:#e6ddf9
    classDef filter fill:#233a2a,stroke:#4fb080,color:#fff
    classDef answer fill:#3a2a18,stroke:#d09a4f,color:#fff
    Q["用户提问 (多主体)"] --> S0
    subgraph L0["Step 0–1 理解与锚定"]
        S0["Step 0 LLM 抽取 subjects+attributes"]:::anchor
        S1["Step 1 实体锚定 · subject 永不过滤"]:::anchor
        S0 --> S1
        S1 -.->|model_hop 产品→型号| M["定向跳转不扩散"]:::anchor
    end
    S1 --> S2["Step 2 图遍历 Entity→Chunk→Wiki"]:::step
    subgraph L1["Step 2–5 检索与回答"]
        S2 --> S3["Step 3 Wiki 向量扩展 (可选)"]:::step
        S3 --> S4["Step 4 LLM 筛选 · 够答才留"]:::filter
        S4 --> S5["Step 5 回答 + 标题归因"]:::answer
    end
    S5 --> O["输出 trace + 引用来源"]:::answer
```

## 方案 C · SVG 真雷达图

`assets/principles-radar.svg` — 七边形能力雷达，深色紫调，带分值进度。

![七项能力雷达](assets/principles-radar.svg)

## 方案 D · SVG 星形能力环图

`assets/principles-star.svg` — 中心 XingGraph 节点，七叶能力环，脉冲动画。

![七项能力星环](assets/principles-star.svg)

## 方案 E · SVG 架构总览图

`assets/architecture-overview.svg` — 建图 + 知识图谱 + WIKI 渐进式检索 + 七项能力栏一体大图。

![架构总览](assets/architecture-overview.svg)
