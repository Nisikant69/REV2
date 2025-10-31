import React, { useState } from 'react';
import Head from 'next/head';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Save, AlertCircle, CheckCircle } from 'lucide-react';
import api, { type Settings as SettingsType } from '@/lib/api';
import { toast } from 'sonner';

export default function Settings() {
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState<SettingsType | null>(null);

  const {
    data: initialSettings,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['settings'],
    queryFn: () => api.getSettings(),
  });

  React.useEffect(() => {
    if (initialSettings) {
      setSettings(initialSettings);
    }
  }, [initialSettings]);

  const saveMutation = useMutation({
    mutationFn: (newSettings: SettingsType) => api.updateSettings(newSettings),
    onSuccess: () => {
      toast.success('Settings saved successfully');
      setSaving(false);
    },
    onError: () => {
      toast.error('Failed to save settings');
      setSaving(false);
    },
  });

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    saveMutation.mutate(settings);
  };

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-12 h-12 text-danger-600 mx-auto mb-4" />
        <p className="text-gray-700 mb-4">Failed to load settings</p>
      </div>
    );
  }

  return (
    <>
      <Head>
        <title>Settings - REV2</title>
        <meta name="description" content="Configure REV2 settings" />
      </Head>

      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
          <p className="mt-2 text-gray-600">Configure your REV2 instance and preferences</p>
        </div>

        {isLoading ? (
          <div className="bg-white rounded-lg border border-gray-200 p-8 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
            <div className="space-y-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-10 bg-gray-200 rounded"></div>
              ))}
            </div>
          </div>
        ) : settings ? (
          <div className="space-y-6">
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">General Settings</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Default LLM Model
                  </label>
                  <select
                    value={settings.default_model || ''}
                    onChange={(e) => setSettings({ ...settings, default_model: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  >
                    <option value="gpt-4">GPT-4</option>
                    <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                    <option value="claude-3-opus">Claude 3 Opus</option>
                    <option value="gemini-pro">Gemini Pro</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Max Files per Review
                  </label>
                  <input
                    type="number"
                    value={settings.max_files_per_review || 0}
                    onChange={(e) =>
                      setSettings({ ...settings, max_files_per_review: parseInt(e.target.value) })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Max Lines per File
                  </label>
                  <input
                    type="number"
                    value={settings.max_lines_per_file || 0}
                    onChange={(e) =>
                      setSettings({ ...settings, max_lines_per_file: parseInt(e.target.value) })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Review Settings</h2>

              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="enable_caching"
                    checked={settings.enable_caching || false}
                    onChange={(e) => setSettings({ ...settings, enable_caching: e.target.checked })}
                    className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <label htmlFor="enable_caching" className="text-sm font-medium text-gray-700">
                    Enable Caching
                  </label>
                  <p className="text-xs text-gray-500">Cache similar code reviews to improve performance</p>
                </div>

                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="enable_parallel"
                    checked={settings.enable_parallel_processing || false}
                    onChange={(e) =>
                      setSettings({ ...settings, enable_parallel_processing: e.target.checked })
                    }
                    className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <label htmlFor="enable_parallel" className="text-sm font-medium text-gray-700">
                    Enable Parallel Processing
                  </label>
                  <p className="text-xs text-gray-500">Process multiple files in parallel for faster reviews</p>
                </div>

                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="enable_batch"
                    checked={settings.enable_batch_processing || false}
                    onChange={(e) => setSettings({ ...settings, enable_batch_processing: e.target.checked })}
                    className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <label htmlFor="enable_batch" className="text-sm font-medium text-gray-700">
                    Enable Batch Processing
                  </label>
                  <p className="text-xs text-gray-500">Batch API calls to reduce costs</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Rate Limiting</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Max Reviews per Hour
                  </label>
                  <input
                    type="number"
                    value={settings.rate_limit_per_hour || 0}
                    onChange={(e) =>
                      setSettings({ ...settings, rate_limit_per_hour: parseInt(e.target.value) })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Request Timeout (seconds)
                  </label>
                  <input
                    type="number"
                    value={settings.request_timeout_seconds || 0}
                    onChange={(e) =>
                      setSettings({ ...settings, request_timeout_seconds: parseInt(e.target.value) })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">API Keys</h2>
              <p className="text-sm text-gray-600 mb-4">Manage your API credentials</p>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-blue-700">
                  API keys should be configured via environment variables for security.
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
              >
                <Save className="w-4 h-4" />
                {saving ? 'Saving...' : 'Save Settings'}
              </button>
            </div>

            <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-green-700">Settings are automatically validated before saving</p>
            </div>
          </div>
        ) : null}
      </div>
    </>
  );
}
