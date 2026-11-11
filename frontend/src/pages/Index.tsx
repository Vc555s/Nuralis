import { AppHeader } from '@/components/layout/AppHeader';
import { AppSidebar } from '@/components/layout/AppSidebar';
import { MainContent } from '@/components/layout/MainContent';
import { ProgressOverlay } from '@/components/layout/ProgressOverlay';

const Index = () => {
  return (
    <div className="min-h-screen bg-background text-foreground w-full">
      {/* Progress Overlay */}
      <ProgressOverlay />
      
      {/* App Header */}
      <AppHeader />
      
      {/* Main Layout */}
      <div className="flex w-full">
        <AppSidebar />
        <MainContent />
      </div>
    </div>
  );
};

export default Index;
