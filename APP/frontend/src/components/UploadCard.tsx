import { ChangeEvent, useState } from 'react';
import { UploadCloud } from 'lucide-react';
import { apiClient } from '../api/client';

interface UploadCardProps {
  onAnalysisStarted: (documentId: number | null) => void;
}

export function UploadCard({ onAnalysisStarted }: UploadCardProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function handleUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setError(null);
    setSuccess(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await apiClient.post('/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setSuccess('Document uploaded. Analysis will start momentarily.');
      onAnalysisStarted(response.data.id);
    } catch (err: any) {
      const message = err.response?.data?.detail ?? err.message ?? 'Upload failed. Please try again.';
      setError(message);
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-start gap-4">
        <div className="rounded-full bg-slate-100 p-3 text-slate-600">
          <UploadCloud className="h-5 w-5" />
        </div>
        <div className="flex-1">
          <h2 className="text-lg font-semibold text-slate-900">Upload intervention dossier</h2>
          <p className="text-sm text-slate-500">
            Accepts PDF, DOCX, TXT, and scanned images up to 50MB. Data is processed securely within the GovCloud
            enclave.
          </p>

          <label className="mt-4 inline-flex cursor-pointer items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover-bg-slate-800">
            <input type="file" hidden onChange={handleUpload} accept=".pdf,.docx,.txt,.png,.jpg,.jpeg" />
            {isUploading ? 'Uploading…' : 'Select file'}
          </label>

          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
          {success && <p className="mt-3 text-sm text-emerald-600">{success}</p>}
        </div>
      </div>
    </section>
  );
}
