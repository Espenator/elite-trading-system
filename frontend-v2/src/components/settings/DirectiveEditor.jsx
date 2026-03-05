// Directive Editor — edit trading directive markdown files.
// Shows global.md, regime_bull.md, regime_bear.md with live editing.

import { useState, useEffect } from 'react';
import { FileText, Save, RefreshCw, Check, AlertTriangle } from 'lucide-react';
import { useCnsDirectives, putDirective } from '../../hooks/useApi';

export default function DirectiveEditor() {
  const { data, loading, refetch } = useCnsDirectives();
  const [activeFile, setActiveFile] = useState(null);
  const [editContent, setEditContent] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null); // 'success' | 'error' | null
  const [dirty, setDirty] = useState(false);

  const directives = data?.directives || [];

  // Set first file as active on load
  useEffect(() => {
    if (directives.length > 0 && !activeFile) {
      setActiveFile(directives[0].filename);
      setEditContent(directives[0].content);
    }
  }, [directives, activeFile]);

  const handleFileSelect = (filename) => {
    if (dirty && !confirm('Unsaved changes will be lost. Continue?')) return;
    const file = directives.find(f => f.filename === filename);
    setActiveFile(filename);
    setEditContent(file?.content || '');
    setDirty(false);
    setSaveStatus(null);
  };

  const handleSave = async () => {
    if (!activeFile) return;
    setSaving(true);
    setSaveStatus(null);
    try {
      await putDirective(activeFile, editContent);
      setSaveStatus('success');
      setDirty(false);
      await refetch();
      setTimeout(() => setSaveStatus(null), 3000);
    } catch (err) {
      console.error('Save failed:', err);
      setSaveStatus('error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-xl border border-secondary/30 bg-surface overflow-hidden">
      <div className="px-4 py-3 border-b border-secondary/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-semibold text-white">Trading Directives</h3>
          <span className="text-xs text-secondary">CLAUDE.md for trading rules</span>
        </div>
        <div className="flex items-center gap-2">
          {saveStatus === 'success' && (
            <span className="flex items-center gap-1 text-xs text-green-400">
              <Check className="w-3 h-3" /> Saved
            </span>
          )}
          {saveStatus === 'error' && (
            <span className="flex items-center gap-1 text-xs text-red-400">
              <AlertTriangle className="w-3 h-3" /> Save failed
            </span>
          )}
          <button
            onClick={handleSave}
            disabled={!dirty || saving}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              dirty
                ? 'bg-primary text-dark hover:bg-primary/80'
                : 'bg-secondary/20 text-secondary cursor-not-allowed'
            }`}
          >
            <Save className="w-3 h-3" />
            {saving ? 'Saving...' : 'Save'}
          </button>
          <button
            onClick={refetch}
            className="p-1.5 rounded-lg bg-secondary/10 hover:bg-secondary/20 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-secondary ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="flex h-[500px]">
        {/* File list */}
        <div className="w-48 border-r border-secondary/30 overflow-y-auto">
          {directives.map((file) => (
            <button
              key={file.filename}
              onClick={() => handleFileSelect(file.filename)}
              className={`w-full text-left px-3 py-2.5 text-sm border-b border-secondary/10 transition-colors ${
                activeFile === file.filename
                  ? 'bg-primary/10 text-primary border-l-2 border-l-primary'
                  : 'text-white hover:bg-white/5'
              }`}
            >
              <div className="font-medium">{file.filename}</div>
              <div className="text-xs text-secondary mt-0.5">
                {(file.size_bytes / 1024).toFixed(1)} KB
              </div>
            </button>
          ))}
          {directives.length === 0 && !loading && (
            <div className="p-4 text-xs text-secondary text-center">
              No directive files found
            </div>
          )}
        </div>

        {/* Editor */}
        <div className="flex-1 flex flex-col">
          {activeFile ? (
            <textarea
              value={editContent}
              onChange={(e) => {
                setEditContent(e.target.value);
                setDirty(true);
              }}
              className="flex-1 w-full bg-transparent text-sm text-white font-mono p-4 resize-none outline-none custom-scrollbar leading-relaxed"
              placeholder="# Trading Directive..."
              spellCheck={false}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center text-secondary text-sm">
              Select a file to edit
            </div>
          )}

          {/* Status bar */}
          <div className="px-4 py-1.5 border-t border-secondary/30 flex items-center justify-between text-xs text-secondary">
            <span>{activeFile || 'No file selected'}</span>
            <span>{dirty ? 'Modified' : 'Saved'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
