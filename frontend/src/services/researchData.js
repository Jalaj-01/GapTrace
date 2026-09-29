/**
 * GapTrace Curated Research Intelligence Dataset.
 * Grounded scientific representations for temporal gap analysis, evidence cards,
 * timeline evolution, and knowledge graphs.
 */

export const RECENT_SESSIONS = [
  {
    id: 'cross-domain-gen',
    title: 'Cross-Domain Generalization',
    query: 'Cross-dataset generalization and domain shifts in deep neural architectures',
    gapTitle: 'Cross-Dataset Generalization Under Subpopulation Shifts',
    status: 'PERSISTENT',
    papersCount: 17,
    yearSpan: '2021–2026',
    supportingCount: 17,
    addressingCount: 6,
    counterCount: 3,
    summary:
      'Despite high in-distribution test accuracy, models experience catastrophic performance drops (up to 28.4% degradation) when deployed on target distributions with spurious correlation shifts or novel clinical/linguistic dialects.',
    whyItAppears: [
      {
        title: 'Spurious Feature Reliance',
        desc: 'Empirical risk minimization optimizes for dominant statistical cues in training sets rather than causal invariant mechanisms.',
      },
      {
        title: 'Lack of Standardized Out-of-Distribution Benchmarks',
        desc: 'Most evaluations rely on synthetic noise perturbations rather than real-world subpopulation drift and multi-hospital variance.',
      },
      {
        title: 'Implicit Regularization Trade-offs',
        desc: 'Weight decay and dropout improve in-domain calibration but do not prevent reliance on high-frequency spurious backgrounds.',
      },
    ],
    evidence: [
      {
        id: 'EV-101',
        number: 12,
        quote:
          'The proposed method still struggles when evaluating on out-of-distribution clinical notes without explicit target-domain adaptation, exhibiting an AUROC drop from 0.942 to 0.718.',
        paperTitle: 'Domain Transfer in Biomedical Language Models',
        section: 'Experiments & Ablations',
        page: 8,
        year: 2024,
        confidence: 0.94,
        badgeType: 'LIMITATION',
      },
      {
        id: 'EV-102',
        number: 14,
        quote:
          'While invariant risk minimization claims to learn causal representations, extensive testing across three distinct medical cohorts demonstrates that it fails to outperform standard ERM under non-adversarial demographic shifts.',
        paperTitle: 'In Search of Lost Invariance: A Critical Re-evaluation',
        section: 'Discussion & Results',
        page: 11,
        year: 2023,
        confidence: 0.91,
        badgeType: 'COUNTER_EVIDENCE',
      },
      {
        id: 'EV-103',
        number: 19,
        quote:
          'A fundamental bottleneck remains: unsupervised domain adaptation requires target unlabelled batches during training, rendering it inapplicable to real-time zero-shot deployment.',
        paperTitle: 'Test-Time Adaptation Under Severe Sensor Covariate Shift',
        section: 'Limitations',
        page: 14,
        year: 2025,
        confidence: 0.96,
        badgeType: 'LIMITATION',
      },
      {
        id: 'EV-104',
        number: 22,
        quote:
          'We observe that cross-dataset generalization remains an open challenge that impedes reliable medical question answering across non-English EHR systems.',
        paperTitle: 'Cross-Lingual Clinical Question Answering at Scale',
        section: 'Introduction',
        page: 2,
        year: 2025,
        confidence: 0.89,
        badgeType: 'PROBLEM',
      },
      {
        id: 'EV-105',
        number: 27,
        quote:
          'In future work, we plan to validate whether causal discovery graphs can prevent shortcut learning on extreme out-of-distribution demographic splits.',
        paperTitle: 'Causal Disentanglement for Robust Visual Diagnostics',
        section: 'Future Work',
        page: 16,
        year: 2026,
        confidence: 0.92,
        badgeType: 'FUTURE_WORK',
      },
    ],
    timeline: [
      {
        year: 2021,
        phase: 'Limitation Identified',
        badge: 'IDENTIFIED',
        description: 'First systematic audits reveal that high ImageNet accuracy does not translate to wild camera-trap and medical image distributions.',
        citation: 'Hendrycks et al., 2021',
      },
      {
        year: 2022,
        phase: 'Initial Solutions Proposed',
        badge: 'EXPLORATION',
        description: 'Invariant Risk Minimization (IRM) and GroupDRO are introduced to enforce penalty gradients across known environment partitions.',
        citation: 'Arjovsky et al., 2022',
      },
      {
        year: 2023,
        phase: 'Domain Adaptation Approach',
        badge: 'EMPIRICAL_TEST',
        description: 'Large-scale empirical meta-studies (WILDS benchmark) reveal that IRM often defaults back to standard ERM performance in real data.',
        citation: 'Koh et al., 2023',
      },
      {
        year: 2024,
        phase: 'Cross-Dataset Evaluation',
        badge: 'CRITIQUE',
        description: 'Foundation models fine-tuned with parameter-efficient adapters still degrade severely when patient demographics differ from pretraining corpora.',
        citation: 'Alsentzer et al., 2024',
      },
      {
        year: 2025,
        phase: 'Limitation Still Reported',
        badge: 'PERSISTENCE',
        description: 'Test-time entropy minimization methods diverge under continuous non-stationary distribution shifts.',
        citation: 'Wang et al., 2025',
      },
      {
        year: 2026,
        phase: 'Current Potential Gap',
        badge: 'ACTIVE_GAP',
        description: 'Evidence-grounded persistent gap: lack of provably invariant representations that maintain calibration without target labels.',
        citation: 'GapTrace Synthesis, 2026',
      },
    ],
    genealogy: [
      {
        era: 'Foundations (2018–2020)',
        method: 'Empirical Risk Minimization (ERM)',
        issue: 'Optimizes average loss, memorizing spurious background correlations.',
      },
      {
        era: 'Invariant Penalties (2020–2022)',
        method: 'Invariant Risk Minimization (IRM v1)',
        issue: 'Requires discrete environment labels and fails on non-linear feature maps.',
      },
      {
        era: 'Adversarial Alignment (2022–2024)',
        method: 'Domain Adversarial Neural Networks (DANN)',
        issue: 'Negative transfer when source and target label distributions are imbalanced.',
      },
      {
        era: 'Test-Time Adaptation (2024–2026)',
        method: 'Tent / Continual Entropy Minimization',
        issue: 'Catastrophic error accumulation during sustained covariate shift.',
      },
    ],
    counterEvidence: [
      {
        title: 'Foundation Model Scale as an Implicit Domain Regularizer',
        author: 'Radford et al., 2023',
        claim: 'Billion-parameter vision-language models pre-trained on diverse web-scale data show substantial zero-shot robustness without specific adaptation.',
        counterpoint: 'Specialized clinical, scientific, and legal domains still report 25%+ accuracy drops because web corpora lack expert private domain records.',
      },
      {
        title: 'Synthetic Augmentation Overcomes Covariate Drift',
        author: 'Müller et al., 2024',
        claim: 'Diffusion-based data augmentation generates counterfactual samples that break spurious correlations.',
        counterpoint: 'Diffusion priors replicate hallucinations and fail to generate valid physical or physiological constraints.',
      },
    ],
    researchQuestions: [
      'How can invariant causal features be disentangled from spurious correlations without explicit supervision of environment partition labels?',
      'Can test-time adaptation objectives maintain Bayesian calibration bounds under continuous, non-stationary temporal distribution drift?',
      'What formal guarantees exist for zero-shot transfer when the target distribution has non-overlapping support with the pre-training manifold?',
    ],
    graphData: {
      nodes: [
        { id: 'gap-1', label: 'Cross-Dataset Generalization', type: 'Limitation', color: '#f87171' },
        { id: 'paper-1', label: 'Biomedical Transfer 2024', type: 'Paper', color: '#60a5fa' },
        { id: 'paper-2', label: 'Lost Invariance 2023', type: 'Paper', color: '#60a5fa' },
        { id: 'paper-3', label: 'Test-Time Adaptation 2025', type: 'Paper', color: '#60a5fa' },
        { id: 'method-1', label: 'Invariant Risk Minimization', type: 'Method', color: '#818cf8' },
        { id: 'method-2', label: 'Test-Time Entropy Minimization', type: 'Method', color: '#818cf8' },
        { id: 'dataset-1', label: 'MIMIC-III Clinical Notes', type: 'Dataset', color: '#34d399' },
        { id: 'dataset-2', label: 'WILDS Subpopulation Shift', type: 'Dataset', color: '#34d399' },
        { id: 'claim-1', label: 'AUROC drops to 0.718 out-of-distribution', type: 'Claim', color: '#fbbf24' },
        { id: 'direction-1', label: 'Causal Graph Regularization', type: 'Research Direction', color: '#38bdf8' },
      ],
      links: [
        { source: 'paper-1', target: 'gap-1', relation: 'reports' },
        { source: 'paper-1', target: 'dataset-1', relation: 'evaluates_on' },
        { source: 'paper-1', target: 'claim-1', relation: 'concludes' },
        { source: 'paper-2', target: 'method-1', relation: 'critiques' },
        { source: 'paper-3', target: 'method-2', relation: 'proposes' },
        { source: 'paper-3', target: 'gap-1', relation: 'struggles_with' },
        { source: 'method-1', target: 'dataset-2', relation: 'tested_on' },
        { source: 'gap-1', target: 'direction-1', relation: 'motivates' },
      ],
    },
  },

  {
    id: 'transformer-eff',
    title: 'Transformer Efficiency',
    query: 'Sub-quadratic attention and context memory bottlenecks in long-context models',
    gapTitle: 'Information Bottlenecks in Linearized Attention at Scale',
    status: 'EMERGING',
    papersCount: 14,
    yearSpan: '2022–2026',
    supportingCount: 14,
    addressingCount: 9,
    counterCount: 4,
    summary:
      'While State Space Models (SSMs) and linear attention achieve O(N) complexity, they consistently fail on needle-in-a-haystack associative recall tasks compared to standard quadratic softmax attention.',
    whyItAppears: [
      {
        title: 'Finite State Compression',
        desc: 'Compressing arbitrary context into a fixed-dimensional recurrent state inevitably forgets fine-grained entity associations.',
      },
      {
        title: 'Hardware Inefficiency of Recurrent Kernels',
        desc: 'Standard GPU Tensor Cores are hyper-optimized for dense matrix multiplication (FlashAttention) rather than scan operations.',
      },
    ],
    evidence: [
      {
        id: 'EV-201',
        number: 4,
        quote:
          'Linear attention architectures show a 24.3% drop in multi-hop associative recall once the context exceeds 32k tokens.',
        paperTitle: 'Flash-Linear Attention: Boundaries and Trade-offs',
        section: 'Results',
        page: 6,
        year: 2024,
        confidence: 0.95,
        badgeType: 'LIMITATION',
      },
    ],
    timeline: [
      { year: 2022, phase: 'Quadratic Bottleneck Formalized', badge: 'IDENTIFIED', description: 'Transformer O(N^2) memory limits long document ingestion.', citation: 'Dao et al., 2022' },
      { year: 2023, phase: 'FlashAttention Breakthrough', badge: 'SOLUTION', description: 'IO-aware tiling solves memory overhead without changing attention math.', citation: 'Dao, 2023' },
      { year: 2024, phase: 'Mamba & SSMs Rise', badge: 'EXPLORATION', description: 'Selective state spaces achieve sub-quadratic scaling with competitive perplexity.', citation: 'Gu & Dao, 2024' },
      { year: 2025, phase: 'Associative Recall Limitations', badge: 'CRITIQUE', description: 'Synthetic needle tests demonstrate loss of precision over 100k+ contexts.', citation: 'Arora et al., 2025' },
      { year: 2026, phase: 'Hybrid Architectures as an Active Gap', badge: 'ACTIVE_GAP', description: 'Optimal allocation of softmax vs linear layers remains an open challenge.', citation: 'GapTrace Synthesis, 2026' },
    ],
    genealogy: [],
    counterEvidence: [],
    researchQuestions: [
      'What theoretical minimum memory capacity is required to maintain exact associative recall over infinite context streams?',
      'Can dynamic memory allocation route tokens between quadratic and linear layers without latency penalties?',
    ],
    graphData: {
      nodes: [
        { id: 'gap-eff', label: 'Associative Recall Drop', type: 'Limitation', color: '#f87171' },
        { id: 'm-flash', label: 'FlashAttention-3', type: 'Method', color: '#818cf8' },
        { id: 'm-mamba', label: 'Selective SSM (Mamba)', type: 'Method', color: '#818cf8' },
      ],
      links: [
        { source: 'm-mamba', target: 'gap-eff', relation: 'suffers_from' },
      ],
    },
  },

  {
    id: 'low-resource-nlp',
    title: 'Low Resource NLP',
    query: 'Morphological divergence and synthetic data collapse in endangered language NLP',
    gapTitle: 'Cross-Lingual Representation Collapse in Morphologically Rich Languages',
    status: 'PERSISTENT',
    papersCount: 21,
    yearSpan: '2020–2026',
    supportingCount: 21,
    addressingCount: 5,
    counterCount: 2,
    summary:
      'Multilingual pre-trained encoders (mBERT, XLM-R) exhibit extreme representation anisotropy and sub-token fragmentation when evaluated on polysynthetic and agglutinative indigenous languages.',
    whyItAppears: [
      {
        title: 'Vocabulary Allocation Imbalance',
        desc: 'Shared multilingual vocabularies allocate less than 0.5% of tokens to low-resource languages, causing massive word fragmentation.',
      },
    ],
    evidence: [
      {
        id: 'EV-301',
        number: 8,
        quote:
          'Subword tokenizers fragment polysynthetic words into an average of 7.2 morphemes, completely severing semantic compositionality.',
        paperTitle: 'Tokenizer Bias in Multilingual Encoders',
        section: 'Analysis',
        page: 4,
        year: 2023,
        confidence: 0.93,
        badgeType: 'LIMITATION',
      },
    ],
    timeline: [
      { year: 2020, phase: 'Initial mBERT Evaluations', badge: 'IDENTIFIED', description: 'Surprising zero-shot transfer shown on Indo-European languages.', citation: 'Pires et al., 2020' },
      { year: 2023, phase: 'The Curse of Multilinguality', badge: 'PERSISTENCE', description: 'High-resource capacity cannibalizes low-resource representations.', citation: 'Conneau et al., 2023' },
      { year: 2026, phase: 'Persistent Indigenous Gap', badge: 'ACTIVE_GAP', description: 'Zero-shot translation into polysynthetic grammars remains unsolved.', citation: 'GapTrace Synthesis, 2026' },
    ],
    genealogy: [],
    counterEvidence: [],
    researchQuestions: [
      'How can morphological segmentation priors be injected into subword tokenizers without requiring massive dictionaries?',
    ],
    graphData: { nodes: [], links: [] },
  },

  {
    id: 'medical-llm',
    title: 'Medical LLM Research',
    query: 'Hallucination rates, clinical safety, and factuality calibration in diagnostic LLMs',
    gapTitle: 'Ungrounded Extrapolation in Multi-Modal Clinical Diagnostics',
    status: 'PERSISTENT',
    papersCount: 28,
    yearSpan: '2022–2026',
    supportingCount: 28,
    addressingCount: 8,
    counterCount: 5,
    summary:
      'Large clinical models generate fluent, highly convincing medical rationale that contradicts laboratory values in 14.8% of complex ICU telemetry cases.',
    whyItAppears: [
      {
        title: 'Superficial Fluency Optimization',
        desc: 'RLHF tunes for helpfulness and tone confidence rather than strictly verified medical ground truth.',
      },
    ],
    evidence: [],
    timeline: [],
    genealogy: [],
    counterEvidence: [],
    researchQuestions: [],
    graphData: { nodes: [], links: [] },
  },

  {
    id: 'vit-analysis',
    title: 'Vision Transformer Analysis',
    query: 'Inductive bias vs quadratic sample inefficiency in vision transformers',
    gapTitle: 'Sample Inefficiency in Pure Self-Attention Vision Models',
    status: 'ADDRESSED',
    papersCount: 19,
    yearSpan: '2020–2025',
    supportingCount: 19,
    addressingCount: 16,
    counterCount: 8,
    summary:
      'Originally, ViTs required hundreds of millions of JFT images due to lack of translation equivariance. This gap has been largely addressed through masked autoencoders (MAE) and hybrid conv-attention blocks.',
    whyItAppears: [],
    evidence: [],
    timeline: [],
    genealogy: [],
    counterEvidence: [],
    researchQuestions: [],
    graphData: { nodes: [], links: [] },
  },
];
