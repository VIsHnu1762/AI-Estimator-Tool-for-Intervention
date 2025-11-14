import { useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { UploadCard } from './components/UploadCard';
import { AnalysisTimeline } from './components/AnalysisTimeline';
import { ReportPreview } from './components/ReportPreview';

function App() {
    const [analysisId, setAnalysisId] = useState<number | null>(null);

    return (
        <div className="min-h-screen bg-slate-50 text-slate-900">
            <header className="border-b border-slate-200 bg-white">
                <div className="mx-auto flex max-w-6xl items-center gap-4 px-6 py-4">
                    <img src="/gov-emblem.svg" alt="Gov Emblem" className="h-10 w-10" />
                    <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                            Ministry of Road Transport & Highways
                        </p>
                        <h1 className="text-xl font-semibold text-slate-900">
                            Road Safety Intervention Intelligence Console
                        </h1>
                    </div>
                </div>
            </header>

            <main className="mx-auto grid max-w-6xl gap-6 px-6 py-8 grid-cols-420-1fr">
                <div className="space-y-6">
                    <UploadCard onAnalysisStarted={setAnalysisId} />
                    <AnalysisTimeline analysisId={analysisId} />
                </div>
                <div className="space-y-6">
                    <ReportPreview analysisId={analysisId} />
                    <section className="rounded-2xl border border-slate-200 bg-white p-5">
                        <div className="flex items-center gap-3">
                            <ShieldCheck className="h-5 w-5 text-slate-500" />
                            <div>
                                <p className="text-sm font-semibold text-slate-900">Security & Compliance</p>
                                <p className="text-xs text-slate-500">Documents never leave secured government infrastructure</p>
                            </div>
                        </div>
                        <div className="mt-4 grid gap-3 text-sm text-slate-600">
                            <p>• SHA-256 document fingerprinting & encrypted blob storage</p>
                            <p>• Automated IRC mapping via auditable RAG pipelines</p>
                            <p>• CPWD / GeM rate verification with caching & timestamps</p>
                            <p>• Accessible UI compliant with GIGW / WCAG 2.1 AA</p>
                        </div>
                    </section>
                </div>
            </main>
        </div>
    );
}

export default App;
