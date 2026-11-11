import { motion } from 'framer-motion';
import { FileText, Hash, Calendar, TrendingUp } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { useAppStore } from '@/stores/useAppStore';
import { useEffect, useState } from 'react';

interface MetricCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  gradient: string;
  delay: number;
}

function MetricCard({ title, value, icon, gradient, delay }: MetricCardProps) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => {
      const duration = 1000;
      const steps = 60;
      const increment = value / steps;
      let current = 0;

      const counter = setInterval(() => {
        current += increment;
        if (current >= value) {
          setDisplayValue(value);
          clearInterval(counter);
        } else {
          setDisplayValue(Math.floor(current));
        }
      }, duration / steps);

      return () => clearInterval(counter);
    }, delay);

    return () => clearTimeout(timer);
  }, [value, delay]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: delay / 1000 }}
    >
      <Card className="border border-border shadow-soft card-hover transition-smooth">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-sm font-medium text-foreground-secondary">{title}</p>
              <p className="text-3xl font-bold text-foreground tracking-tight">
                {displayValue.toLocaleString()}
              </p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-gradient-primary flex items-center justify-center shadow-soft">
              {icon}
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

export function MetricsRow() {
  const { metrics, analysisData } = useAppStore();

  const metricCards = [
    {
      title: "Papers Found",
      value: metrics.papersFound,
      icon: <FileText className="h-6 w-6 text-white" />,
      gradient: "",
      delay: 0
    },
    {
      title: "Keywords Tracked",
      value: metrics.keywordsTracked,
      icon: <Hash className="h-6 w-6 text-white" />,
      gradient: "",
      delay: 200
    },
    {
      title: "Years Covered",
      value: metrics.yearsCovered,
      icon: <Calendar className="h-6 w-6 text-white" />,
      gradient: "",
      delay: 400
    },
    {
      title: "Avg Papers/Year",
      value: metrics.avgPapersPerYear,
      icon: <TrendingUp className="h-6 w-6 text-white" />,
      gradient: "",
      delay: 600
    }
  ];

  if (!analysisData) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {metricCards.map((metric, index) => (
          <Card key={index} className="border border-border shadow-soft">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="text-sm font-medium text-foreground-muted">{metric.title}</p>
                  <p className="text-3xl font-bold text-foreground-muted tracking-tight">-</p>
                </div>
                <div className="w-12 h-12 rounded-xl bg-muted flex items-center justify-center">
                  <div className="opacity-50">{metric.icon}</div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {metricCards.map((metric, index) => (
        <MetricCard key={index} {...metric} />
      ))}
    </div>
  );
}