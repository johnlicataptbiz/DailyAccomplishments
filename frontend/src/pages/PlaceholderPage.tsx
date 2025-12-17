import type { ReactNode } from 'react';
import { Construction } from 'lucide-react';

interface Props {
  title: string;
  description?: ReactNode;
}

export default function PlaceholderPage({ title, description }: Props) {
  return (
    <div className="glass-panel p-8 space-y-4 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 text-accent">
        <Construction className="h-5 w-5" />
        <h2 className="text-xl font-semibold">{title}</h2>
      </div>
      <p className="text-muted text-sm">
        {description || 'This view is on the roadmap. Today Brief is ready below—stay tuned for deeper time-series insights!'}
      </p>
    </div>
  );
}
