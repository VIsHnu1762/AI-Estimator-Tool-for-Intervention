import { useEffect, useState } from 'react';
import { FileText, ArrowRight } from 'lucide-react';
import { apiClient } from '../api/client';

interface ReportPreviewProps {
  analysisId: number | null;
}

interface ReportSummary {
  total_interventions: number;
  total_cost: number;
  analysis_started_at: string;
  report_generated_at?: string;
}

export function ReportPreview({ analysisId }: ReportPreviewProps) {
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!analysisId) return;

    async function fetchSummary() {
      setLoading(true);
      try {
        const { data } = await apiClient.get(`/documents/${analysisId}/analysis`);
        setSummary(data);
      } catch (error) {
        console.error('Failed to load analysis summary', error);
      } finally {
        setLoading(false);
      }
    }

    fetchSummary();
  }, [analysisId]);

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6">
      <div className="flex items-center gap-3">
        <FileText className="h-5 w-5 text-slate-500" />
        <div>
          <p className="text-sm font-semibold text-slate-900">Report preview</p>
          <p className="text-xs text-slate-500">
            {summary ? 'Ready for download' : loading ? 'Analyzing document…' : 'Upload a document to begin'}
          </p>
        </div>
      </div>

      {summary && (
        <div className="mt-5 space-y-4">
          <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
            <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Total material cost</p>
            <p className="text-2xl font-semibold text-slate-900">{formatCurrency(summary.total_cost)}</p>
            <p className="text-xs text-slate-500">
              {summary.total_interventions} intervention(s) processed ·{' '}
              {new Date(summary.analysis_started_at).toLocaleString('en-IN', {
                weekday: 'short',
                day: 'numeric',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </p>
          </div>

          <a
            href={`/api/documents/${analysisId}/report`}
            target="_blank"
            className="group inline-flex items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover-bg-slate-800"
          >
            Download official PDF
            <ArrowRight className="h-4 w-4 transition group-hover-translate-x-0_5" />
          </a>
        </div>
      )}
    </section>
  );
}
