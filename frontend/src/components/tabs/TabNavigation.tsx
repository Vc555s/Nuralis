import { motion } from 'framer-motion';
import { 
  BarChart3, 
  Brain, 
  Search, 
  TrendingUp, 
  Lightbulb,
  ChevronDown 
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAppStore } from '@/stores/useAppStore';
import { TabType } from '@/types';

const tabs = [
  {
    id: 'advanced-analytics' as TabType,
    label: 'Advanced Analytics',
    icon: BarChart3,
    description: 'Trends & patterns analysis',
    badge: null
  },
  {
    id: 'ai-insights' as TabType,
    label: 'AI Insights',
    icon: Brain,
    description: 'LLM-powered analysis',
    badge: 'AI'
  },
  {
    id: 'paper-explorer' as TabType,
    label: 'Paper Explorer',
    icon: Search,
    description: 'Browse & filter papers',
    badge: null
  },
  {
    id: 'growth-analysis' as TabType,
    label: 'Growth Analysis',
    icon: TrendingUp,
    description: 'Research growth metrics',
    badge: null
  },
  {
    id: 'research-intelligence' as TabType,
    label: 'Research Intelligence',
    icon: Lightbulb,
    description: 'Strategic insights',
    badge: 'Pro'
  }
];

export function TabNavigation() {
  const { activeTab, setActiveTab, analysisData } = useAppStore();

  return (
    <div className="border-b border-border bg-background">
      <div className="flex overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          const isDisabled = !analysisData;
          
          return (
            <motion.button
              key={tab.id}
              whileHover={{ y: isDisabled ? 0 : -1 }}
              whileTap={{ scale: isDisabled ? 1 : 0.98 }}
              onClick={() => !isDisabled && setActiveTab(tab.id)}
              disabled={isDisabled}
              className={`
                relative flex items-center gap-3 px-6 py-4 text-left transition-smooth whitespace-nowrap
                ${isActive 
                  ? 'text-primary bg-primary/5' 
                  : isDisabled 
                    ? 'text-foreground-muted cursor-not-allowed opacity-60' 
                    : 'text-foreground-secondary hover:text-foreground hover:bg-muted/50'
                }
              `}
            >
              <Icon className={`h-5 w-5 ${isActive ? 'text-primary' : ''}`} />
              
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{tab.label}</span>
                  {tab.badge && (
                    <Badge 
                      variant={isActive ? 'default' : 'secondary'} 
                      className="text-xs px-2 py-0.5"
                    >
                      {tab.badge}
                    </Badge>
                  )}
                </div>
                <span className="text-xs text-foreground-muted">{tab.description}</span>
              </div>

              {isActive && (
                <motion.div
                  layoutId="activeTabIndicator"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary"
                  initial={false}
                  transition={{ duration: 0.3, ease: "easeInOut" }}
                />
              )}
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}