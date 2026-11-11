import { motion } from 'framer-motion';
import { MetricsRow } from '@/components/metrics/MetricsRow';
import { TabNavigation } from '@/components/tabs/TabNavigation';
import { AdvancedAnalytics } from '@/components/tabs/AdvancedAnalytics';
import { AIInsights } from '@/components/tabs/AIInsights';
import { PaperExplorer } from '@/components/tabs/PaperExplorer';
import { GrowthAnalysis } from '@/components/tabs/GrowthAnalysis';
import { ResearchIntelligence } from '@/components/tabs/ResearchIntelligence';
import { useAppStore } from '@/stores/useAppStore';

const tabComponents = {
  'advanced-analytics': AdvancedAnalytics,
  'ai-insights': AIInsights,
  'paper-explorer': PaperExplorer,
  'growth-analysis': GrowthAnalysis,
  'research-intelligence': ResearchIntelligence,
};

export function MainContent() {
  const { activeTab } = useAppStore();
  const ActiveTabComponent = tabComponents[activeTab];

  return (
    <motion.main 
      className="flex-1 overflow-hidden flex flex-col"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Metrics Row */}
      <section className="p-6 bg-gradient-background border-b border-border">
        <MetricsRow />
      </section>

      {/* Tab Navigation */}
      <TabNavigation />

      {/* Tab Content */}
      <section className="flex-1 overflow-y-auto p-6">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <ActiveTabComponent />
        </motion.div>
      </section>
    </motion.main>
  );
}