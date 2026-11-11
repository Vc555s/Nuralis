import { 
  SearchConfig, 
  AnalysisResponse, 
  SemanticSearchResult,
  SystemStatus,
  Paper,
  TrendsData,
  AdvancedInsights
} from '@/types';

// Sample data, used only when VITE_MOCK_MODE=true (UI development without a backend)
const generateMockPapers = (count: number): Paper[] => {
  const titles = [
    "Advanced Machine Learning Techniques for Natural Language Processing",
    "Deep Neural Networks in Computer Vision Applications",
    "Quantum Computing Applications in Cryptography",
    "Reinforcement Learning for Autonomous Systems",
    "Transformer Architectures for Large Language Models",
    "Edge Computing in Internet of Things Devices",
    "Blockchain Technology for Secure Data Management",
    "Federated Learning in Privacy-Preserving AI",
    "Graph Neural Networks for Social Network Analysis",
    "Meta-Learning Approaches for Few-Shot Learning"
  ];
  
  const authors = [
    ["John Smith", "Jane Doe"],
    ["Alice Johnson", "Bob Wilson", "Carol Brown"],
    ["David Lee", "Emma Davis"],
    ["Frank Miller", "Grace Taylor", "Henry Anderson"],
    ["Ivy Chen", "Jack Robinson"]
  ];
  
  const categories = [
    ["Computer Science", "Machine Learning"],
    ["Artificial Intelligence", "Deep Learning"],
    ["Quantum Computing", "Cryptography"],
    ["Robotics", "Autonomous Systems"],
    ["Natural Language Processing", "Transformers"]
  ];

  return Array.from({ length: count }, (_, i) => ({
    title: titles[i % titles.length],
    abstract: `This paper presents novel approaches to ${titles[i % titles.length].toLowerCase()}. Our research demonstrates significant improvements over existing methods with comprehensive experimental validation. The proposed framework shows promising results across multiple benchmarks and real-world applications.`,
    authors: authors[i % authors.length],
    categories: categories[i % categories.length],
    date: `2024-${String(Math.floor(i % 12) + 1).padStart(2, '0')}-15`,
    url: `https://arxiv.org/abs/2024.${String(i + 1).padStart(5, '0')}`
  }));
};

const generateMockTrends = (): TrendsData => {
  const years = [2020, 2021, 2022, 2023, 2024];
  const keywords = {
    "machine learning": { 2020: 150, 2021: 180, 2022: 220, 2023: 280, 2024: 340 },
    "deep learning": { 2020: 120, 2021: 160, 2022: 200, 2023: 250, 2024: 300 },
    "natural language processing": { 2020: 80, 2021: 110, 2022: 140, 2023: 180, 2024: 220 },
    "computer vision": { 2020: 90, 2021: 120, 2022: 150, 2023: 190, 2024: 230 },
    "reinforcement learning": { 2020: 60, 2021: 75, 2022: 95, 2023: 120, 2024: 150 }
  };
  
  const growth_analysis = {
    "machine learning": { growth_rate: 22.5, total_papers: 1170 },
    "deep learning": { growth_rate: 25.8, total_papers: 1030 },
    "natural language processing": { growth_rate: 28.2, total_papers: 730 },
    "computer vision": { growth_rate: 26.1, total_papers: 780 },
    "reinforcement learning": { growth_rate: 25.0, total_papers: 500 }
  };
  
  return { years, keywords, growth_analysis };
};

const generateMockInsights = (): AdvancedInsights => ({
  executive_summary: "The analysis reveals significant growth in AI research, particularly in large language models and multimodal applications. Machine learning continues to dominate with 25% year-over-year growth, while emerging areas like federated learning show promising developments.",
  key_findings: [
    {
      finding: "Transformer architectures have become the dominant paradigm",
      evidence: "67% of papers in NLP and 34% in computer vision utilize transformer-based approaches"
    },
    {
      finding: "Increased focus on AI safety and alignment",
      evidence: "Research in AI safety has grown by 45% year-over-year"
    }
  ],
  research_gaps: [
    {
      description: "Limited research on AI interpretability in production systems",
      opportunity: "Developing practical interpretability tools for deployed models"
    }
  ],
  future_directions: [
    {
      direction: "Multimodal AI systems",
      rationale: "Convergence of text, image, and audio processing capabilities"
    }
  ],
  trend_analysis: {
    emerging_topics: [
      { topic: "Large Language Models", growth_rate: 89.5 },
      { topic: "Federated Learning", growth_rate: 67.2 },
      { topic: "AI Safety", growth_rate: 45.8 }
    ],
    declining_topics: [
      { topic: "Traditional NLP", growth_rate: -12.3 },
      { topic: "Rule-based Systems", growth_rate: -25.1 }
    ]
  },
  collaboration_insights: {
    avg_authors_per_paper: 3.4,
    collaboration_rate: 0.78,
    multi_author_papers: 156
  },
  impact_analysis: {
    research_volume: 1250,
    keyword_diversity: 45,
    temporal_span: 5,
    growth_momentum: 23.7
  }
});

// Mock mode flag - switch via Vite env var
const MOCK_MODE = import.meta.env.VITE_MOCK_MODE === 'true';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export class ApiService {
  private static baseUrl = API_BASE_URL;
  
  static async analyzeResearch(config: SearchConfig): Promise<AnalysisResponse> {
    if (MOCK_MODE) {
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      const papers = generateMockPapers(Math.min(config.maxPapers, 200));
      const trends_data = generateMockTrends();
      const advanced_insights = config.enableLLM ? generateMockInsights() : undefined;
      
      return {
        papers,
        trends_data,
        status: {
          gpu: { device: 'cuda', total: 24000, allocated: 8500 },
          llmAvailable: config.enableLLM,
          embeddingsAvailable: config.enableEmbeddings
        },
        advanced_insights
      };
    }
    
    // Real API call. Failures propagate to the caller, which reports them to the user;
    // sample data is only returned in explicit mock mode (VITE_MOCK_MODE=true).
    const response = await fetch(`${this.baseUrl}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });

    if (!response.ok) {
      throw new Error(`Analysis failed: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }
  
  static async semanticSearch(question: string, k = 3): Promise<SemanticSearchResult[]> {
    if (MOCK_MODE) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      return [
        {
          metadata: {
            title: "Deep Learning Approaches to Natural Language Understanding",
            authors: ["Dr. Sarah Chen", "Prof. Michael Rodriguez"],
            url: "https://arxiv.org/abs/2024.01234"
          },
          distance: 0.15
        },
        {
          metadata: {
            title: "Transformer Networks for Language Model Training",
            authors: "Emily Watson",
            url: "https://arxiv.org/abs/2024.05678"
          },
          distance: 0.23
        },
        {
          metadata: {
            title: "Advanced Techniques in Neural Language Processing",
            authors: ["Prof. David Kim", "Dr. Lisa Park", "James Thompson"],
            url: "https://arxiv.org/abs/2024.09876"
          },
          distance: 0.31
        }
      ];
    }
    
    const response = await fetch(`${this.baseUrl}/semantic-search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, k })
    });

    if (!response.ok) {
      throw new Error(`Semantic search failed: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }
  
  static async getSystemStatus(): Promise<SystemStatus> {
    if (MOCK_MODE) {
      return {
        gpu: { device: 'cuda', total: 24000, allocated: 8500 },
        llmAvailable: true,
        embeddingsAvailable: true
      };
    }
    
    // If the backend is unreachable, report every capability as unavailable.
    try {
      const response = await fetch(`${this.baseUrl}/status`);
      if (!response.ok) {
        throw new Error(`Status check failed: ${response.statusText}`);
      }
      
      return response.json();
    } catch (error) {
      console.warn('Backend unreachable:', error);
      return {
        gpu: { device: 'unknown', total: null, allocated: null },
        llmAvailable: false,
        embeddingsAvailable: false
      };
    }
  }
}