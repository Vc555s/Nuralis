import { create } from 'zustand';
import { 
  SearchConfig, 
  SystemStatus, 
  AnalysisResponse, 
  SemanticSearchResult,
  AnalysisProgress,
  AppMetrics,
  TabType
} from '@/types';

interface AppState {
  // UI State
  sidebarCollapsed: boolean;
  activeTab: TabType;
  isAnalyzing: boolean;
  progress: AnalysisProgress | null;
  
  // Configuration
  searchConfig: SearchConfig;
  
  // Data
  systemStatus: SystemStatus;
  analysisData: AnalysisResponse | null;
  semanticResults: SemanticSearchResult[];
  metrics: AppMetrics;
  
  // Actions
  setSidebarCollapsed: (collapsed: boolean) => void;
  setActiveTab: (tab: TabType) => void;
  updateSearchConfig: (config: Partial<SearchConfig>) => void;
  setSystemStatus: (status: SystemStatus) => void;
  setAnalysisData: (data: AnalysisResponse) => void;
  setSemanticResults: (results: SemanticSearchResult[]) => void;
  setIsAnalyzing: (analyzing: boolean) => void;
  setProgress: (progress: AnalysisProgress | null) => void;
  updateMetrics: (metrics: Partial<AppMetrics>) => void;
  resetAnalysis: () => void;
}

// Mock data for development
const mockSystemStatus: SystemStatus = {
  gpu: {
    device: 'cuda',
    total: 24000,
    allocated: 8500
  },
  llmAvailable: true,
  embeddingsAvailable: true
};

const mockMetrics: AppMetrics = {
  papersFound: 0,
  keywordsTracked: 0,
  yearsCovered: 0,
  avgPapersPerYear: 0
};

const defaultSearchConfig: SearchConfig = {
  query: '',
  startYear: 2020,
  endYear: new Date().getFullYear(),
  maxPapers: 500,
  enableLLM: true,
  enableEmbeddings: true
};

export const useAppStore = create<AppState>((set, get) => ({
  // Initial State
  sidebarCollapsed: false,
  activeTab: 'advanced-analytics',
  isAnalyzing: false,
  progress: null,
  
  searchConfig: defaultSearchConfig,
  systemStatus: mockSystemStatus,
  analysisData: null,
  semanticResults: [],
  metrics: mockMetrics,
  
  // Actions
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  
  setActiveTab: (tab) => set({ activeTab: tab }),
  
  updateSearchConfig: (config) => 
    set(state => ({ 
      searchConfig: { ...state.searchConfig, ...config } 
    })),
  
  setSystemStatus: (status) => set({ systemStatus: status }),
  
  setAnalysisData: (data) => {
    // Calculate metrics from data
    const papersFound = data.papers.length;
    const years = data.trends_data.years;
    const yearsCovered = years.length;
    const keywordsTracked = Object.keys(data.trends_data.keywords).length;
    const avgPapersPerYear = yearsCovered > 0 ? Math.round(papersFound / yearsCovered) : 0;
    
    set({ 
      analysisData: data,
      metrics: {
        papersFound,
        keywordsTracked,
        yearsCovered,
        avgPapersPerYear
      }
    });
  },
  
  setSemanticResults: (results) => set({ semanticResults: results }),
  
  setIsAnalyzing: (analyzing) => set({ isAnalyzing: analyzing }),
  
  setProgress: (progress) => set({ progress }),
  
  updateMetrics: (metrics) => 
    set(state => ({ 
      metrics: { ...state.metrics, ...metrics } 
    })),
  
  resetAnalysis: () => set({ 
    analysisData: null, 
    semanticResults: [],
    progress: null,
    isAnalyzing: false,
    metrics: mockMetrics
  })
}));