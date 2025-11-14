import { Activity } from 'lucide-react';

const steps = [
  {
    title: 'Secure ingestion',
    description: 'Virus scan, format validation, OCR for scanned pages',
  },
  {
    title: 'AI interpretation',
    description: 'Hybrid spaCy + transformer pipeline extracts interventions',
  },
  {
    title: 'Cost synthesis',
    description: 'IRC mapping, CPWD/GeM rate lookup, quantity takeoff',
  },
  {
    title: 'Audit report',
    description: 'Official PDF with lineage, formulas, and references',
  },
];

interface TimelineProps {
  analysisId: number | null;
}

export function AnalysisTimeline({ analysisId }: TimelineProps) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6">
      <div className="flex items-center gap-3">
        <Activity className="h-5 w-5 text-slate-500" />
        <div>
          <p className="text-sm font-semibold text-slate-900">Processing pipeline</p>
          <p className="text-xs text-slate-500">
            {analysisId ? `Tracking document #${analysisId}` : 'Awaiting upload'}
          </p>
        </div>
      </div>

      <ol className="mt-6 space-y-4">
        {steps.map((step, index) => (
          <li key={step.title} className="flex gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 text-xs font-semibold text-slate-600">
              {index + 1}
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-900">{step.title}</p>
              <p className="text-xs text-slate-500">{step.description}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
