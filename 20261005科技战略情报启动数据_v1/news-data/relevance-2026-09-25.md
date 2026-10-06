# 与当前01专项工作的相关性（9.25）

- 英伟达在 [Efficient MoE Training for Biological Foundation Models](https://developer.nvidia.com/blog/efficient-moe-training-for-biological-foundation-models) 中通过分组专家计算等内核优化显著加速超大生物序列模型训练，暴露出我方在面向生命科学基础模型底层稀疏算子与训推协同上的优化差距。**我方在超智融合平台的专用算子库与统一编译器研发中，需尽快补齐针对生物 MoE 架构的高性能计算内核与通信重叠优化。**
- 谷歌与 DeepMind 在 [AI saves scientists time but adds 'verification tax'](https://www.researchprofessionalnews.com/rr-news-world-2026-9-ai-saves-scientists-time-but-adds-verification-tax-paper-finds) 中指出 AI 科研工具因激增的假阳性验证成本正在形成新的科研瓶颈，暴露了我方智能体输出端缺乏高置信度自动筛查与机理核验闭环的短板。**我方在科学发现安全可信服务中台中，需重点攻关自动化证据链前置校验与机理一致性预筛工具，明确将压降人工复核成本纳入核心评测指标。**
- Nature 刊发综述 [AI co-scientists are revolutionizing how research is done](https://www.nature.com/articles/d41586-026-02931-5) 阐述了多智能体协同在多路径假说探索与科研推演中的范式演进，暴露出我方科学智能体仍多偏向单点工具调用、缺乏多智能体竞争与群体探索机制的设计空白。**我方在跨学科科学发现系统建设中，需加速引入群体智能协同编排与多假设对抗验证架构，增强复杂科学假设空间的自主推演能力。**
