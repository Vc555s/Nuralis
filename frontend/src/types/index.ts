// Type definitions for Nuralis

export interface SystemStatus {
  gpu: {
    device: 'cuda' | 'cpu';
    total?: number;
    allocated?: number;
  };
  llmAvailable: boolean;
  embeddingsAvailable: boolean;
}

export interface SearchConfig {
  query: string;
  startYear: number;
  endYear: number;
  maxPapers: number;
  enableLLM: boolean;
  enableEmbeddings: boolean;
}

export interface Paper {
  title: string;
  abstract: string;
  authors: string[] | string;
  categories: string[];
  date: string | number;
  url: string;
}

export interface TrendsData {
  years: number[];
  keywords: Record<string, Record<string, number>>;
  growth_analysis?: Record<string, {
    growth_rate: number;
    total_papers: number;
  }>;
  enrichment?: {
    rolling_avg?: Record<string, Record<string, number>>;
    index_base_100?: Record<string, Record<string, number>>;
    year_totals?: Record<string, number>;
  };
}

export interface AdvancedInsights {
  executive_summary?: string;
  key_findings?: Array<{
    finding: string;
    evidence?: string;
  }>;
  research_gaps?: Array<{
    description: string;
    opportunity?: string;
  }>;
  future_directions?: Array<{
    direction: string;
    rationale?: string;
  }>;
  recommendations?: Array<{
    title: string;
    description?: string;
    priority?: 'high' | 'medium' | 'low';
  }>;
  trend_analysis?: {
    emerging_topics?: Array<{
      topic: string;
      growth_rate: number;
    }>;
    declining_topics?: Array<{
      topic: string;
      growth_rate: number;
    }>;
  };
  collaboration_insights?: {
    avg_authors_per_paper: number;
    collaboration_rate: number;
    multi_author_papers: number;
  };
  impact_analysis?: {
    research_volume: number;
    keyword_diversity: number;
    temporal_span: number;
    growth_momentum: number;
  };
}

export interface AnalysisResponse {
  papers: Paper[];
  trends_data: TrendsData;
  status: SystemStatus;
  advanced_insights?: AdvancedInsights;
}

export interface SemanticSearchResult {
  metadata: {
    title: string;
    authors: string | string[];
    url: string;
  };
  distance: number;
}

export interface AppMetrics {
  papersFound: number;
  keywordsTracked: number;
  yearsCovered: number;
  avgPapersPerYear: number;
}

export type AnalysisProgress = {
  step: number;
  total: number;
  message: string;
  percentage: number;
};

export type TabType = 'advanced-analytics' | 'ai-insights' | 'paper-explorer' | 'growth-analysis' | 'research-intelligence';