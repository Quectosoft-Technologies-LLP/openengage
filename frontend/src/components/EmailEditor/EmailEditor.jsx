// src/components/EmailEditor/EmailEditor.jsx
// GrapesJS drag-and-drop email editor with AI-generate via Copilot
import React, { useEffect, useRef, useState } from 'react';
import grapesjs from 'grapesjs';
import 'grapesjs/dist/css/grapes.min.css';
import gjsNewsletter from 'grapesjs-preset-newsletter';
import { generateEmail } from '../../api/client';
import { Wand2, Save, Eye, Loader2, ChevronDown } from 'lucide-react';

const DEFAULT_TOKENS = ['{{first_name}}', '{{company}}', '{{industry}}', '{{job_title}}'];

export default function EmailEditor({ templateId, onSave }) {
  const containerRef   = useRef(null);
  const editorRef      = useRef(null);
  const [saving,  setSaving]  = useState(false);
  const [aiOpen,  setAiOpen]  = useState(false);
  const [aiPrompt, setAiPrompt] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [subject, setSubject] = useState('');

  useEffect(() => {
    const editor = grapesjs.init({
      container: containerRef.current,
      height: '100%',
      width: 'auto',
      fromElement: false,
      storageManager: false,
      plugins: [gjsNewsletter],
      pluginsOpts: { [gjsNewsletter]: {} },
      canvas: {
        styles: [
          'https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap',
        ],
      },
      styleManager: {
        sectors: [
          { name: 'Typography', open: false, buildProps: ['font-family','font-size','font-weight','color','text-align','line-height'] },
          { name: 'Spacing',    open: false, buildProps: ['margin','padding'] },
          { name: 'Background', open: false, buildProps: ['background-color','background'] },
        ]
      }
    });
    editorRef.current = editor;

    // Add personalization token panel
    editor.Panels.addPanel({
      id: 'tokens',
      el: '.tokens-panel',
    });

    return () => editor.destroy();
  }, []);

  const handleAiGenerate = async () => {
    if (!aiPrompt.trim()) return;
    setAiLoading(true);
    try {
      const resp = await generateEmail('email_editor', aiPrompt, { campaign: { tone: 'professional' } });
      const data = JSON.parse(resp.data.email_content.match(/\{[\s\S]*\}/)?.[0] || '{}');
      if (data.html_body && editorRef.current) {
        editorRef.current.setComponents(data.html_body);
      }
      if (data.subject_variants?.[0]) {
        setSubject(data.subject_variants[0].subject || data.subject_variants[0]);
      }
    } catch (err) {
      console.error('AI generation failed:', err);
    } finally {
      setAiLoading(false);
      setAiOpen(false);
    }
  };

  const handleSave = async () => {
    if (!editorRef.current) return;
    setSaving(true);
    const payload = {
      id:           templateId,
      subject,
      html_body:    editorRef.current.getHtml(),
      plain_body:   editorRef.current.getHtml().replace(/<[^>]+>/g, ''),
      grapesjs_json: JSON.stringify(editorRef.current.getProjectData()),
    };
    await onSave?.(payload);
    setSaving(false);
  };

  return (
    <div className="flex flex-col h-full bg-gray-950">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800 bg-gray-900 flex-shrink-0">
        <input value={subject} onChange={e => setSubject(e.target.value)}
          placeholder="Email subject line..."
          className="input flex-1 text-sm" />

        {/* Personalization tokens */}
        <div className="flex items-center gap-1">
          {DEFAULT_TOKENS.map(t => (
            <button key={t}
              onClick={() => editorRef.current?.runCommand('core:insert-content', { content: t })}
              className="badge bg-gray-700 text-gray-300 border border-gray-600 hover:bg-brand-600/20 hover:text-brand-300 hover:border-brand-500/40 transition-all cursor-pointer text-xs px-2 py-1">
              {t}
            </button>
          ))}
        </div>

        {/* AI Generate panel toggle */}
        <div className="relative">
          <button onClick={() => setAiOpen(o => !o)}
            className="btn-pri flex items-center gap-2 text-sm">
            <Wand2 className="w-4 h-4" />
            AI Generate
            <ChevronDown className={`w-3.5 h-3.5 transition-transform ${aiOpen ? 'rotate-180' : ''}`} />
          </button>
          {aiOpen && (
            <div className="absolute right-0 top-11 w-80 card z-50 shadow-2xl border border-gray-700">
              <p className="text-sm font-medium text-gray-200 mb-2">Describe the email you need:</p>
              <textarea value={aiPrompt} onChange={e => setAiPrompt(e.target.value)}
                placeholder="e.g. Write a follow-up email for leads who attended our webinar last week..."
                rows={4} className="input w-full text-sm resize-none mb-3" />
              <button onClick={handleAiGenerate} disabled={aiLoading || !aiPrompt.trim()}
                className="btn-pri w-full flex items-center justify-center gap-2 disabled:opacity-40">
                {aiLoading ? <><Loader2 className="w-4 h-4 animate-spin" /> Generating...</> : <><Wand2 className="w-4 h-4" /> Generate Email</>}
              </button>
            </div>
          )}
        </div>

        <button onClick={handleSave} disabled={saving}
          className="btn-sec flex items-center gap-2 text-sm">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Save
        </button>
      </div>

      {/* GrapesJS canvas */}
      <div ref={containerRef} className="flex-1 min-h-0" />
    </div>
  );
}
