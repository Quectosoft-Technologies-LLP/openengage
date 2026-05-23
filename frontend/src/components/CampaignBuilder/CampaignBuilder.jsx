// src/components/CampaignBuilder/CampaignBuilder.jsx
// Visual drag-and-drop campaign flow builder
import React, { useState } from 'react';
import { Plus, Play, Pause, Trash2, Mail, Tag, Zap, Clock, ChevronRight } from 'lucide-react';
import { createCampaign, launchCampaign, suggestCampaign } from '../../api/client';
import clsx from 'clsx';

const STEP_TYPES = [
  { type: 'send_email',    label: 'Send Email',    icon: Mail,   color: 'text-sky-400   bg-sky-400/10   border-sky-400/30' },
  { type: 'wait',          label: 'Wait',          icon: Clock,  color: 'text-amber-400 bg-amber-400/10 border-amber-400/30' },
  { type: 'add_tag',       label: 'Add Tag',       icon: Tag,    color: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30' },
  { type: 'adjust_score',  label: 'Score Change',  icon: Zap,    color: 'text-violet-400 bg-violet-400/10 border-violet-400/30' },
];

function FlowStep({ step, index, onRemove, onChange }) {
  const meta = STEP_TYPES.find(s => s.type === step.type) || STEP_TYPES[0];
  const Icon = meta.icon;
  return (
    <div className="flex flex-col items-center">
      <div className={clsx('card border w-72 relative group', meta.color.split(' ').slice(1).join(' '))}>
        <div className="flex items-center gap-3">
          <div className={clsx('p-2 rounded-xl', meta.color.split(' ').slice(1,2).join(' '))}>
            <Icon className={clsx('w-4 h-4', meta.color.split(' ')[0])} />
          </div>
          <div className="flex-1">
            <p className="text-sm font-semibold text-gray-200">{meta.label}</p>
            {step.type === 'send_email' && (
              <input value={step.subject || ''} onChange={e => onChange(index, { ...step, subject: e.target.value })}
                placeholder="Email subject..." className="input text-xs w-full mt-1 py-1" />
            )}
            {step.type === 'wait' && (
              <div className="flex items-center gap-2 mt-1">
                <input type="number" value={step.delay_minutes || 60}
                  onChange={e => onChange(index, { ...step, delay_minutes: +e.target.value })}
                  className="input text-xs w-20 py-1" />
                <span className="text-xs text-gray-400">minutes</span>
              </div>
            )}
            {step.type === 'add_tag' && (
              <input value={step.tag || ''} onChange={e => onChange(index, { ...step, tag: e.target.value })}
                placeholder="Tag name..." className="input text-xs w-full mt-1 py-1" />
            )}
            {step.type === 'adjust_score' && (
              <div className="flex items-center gap-2 mt-1">
                <input type="number" value={step.delta || 10}
                  onChange={e => onChange(index, { ...step, delta: +e.target.value })}
                  className="input text-xs w-20 py-1" />
                <span className="text-xs text-gray-400">points</span>
              </div>
            )}
          </div>
          <button onClick={() => onRemove(index)}
            className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-500/20 rounded-lg text-red-400 transition-all">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
      <div className="flex flex-col items-center my-1">
        <div className="w-0.5 h-5 bg-gray-600" />
        <ChevronRight className="w-3.5 h-3.5 text-gray-500 rotate-90" />
      </div>
    </div>
  );
}

export default function CampaignBuilder() {
  const [name,    setName]    = useState('');
  const [type,    setType]    = useState('trigger');
  const [steps,   setSteps]   = useState([]);
  const [saving,  setSaving]  = useState(false);
  const [aiIdea,  setAiIdea]  = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult,  setAiResult]  = useState('');

  const addStep = (stepType) =>
    setSteps(s => [...s, { type: stepType, id: Date.now() }]);

  const removeStep = (i) =>
    setSteps(s => s.filter((_, idx) => idx !== i));

  const updateStep = (i, updated) =>
    setSteps(s => s.map((step, idx) => idx === i ? updated : step));

  const handleSave = async () => {
    setSaving(true);
    try {
      await createCampaign({ name, type, flow_steps: JSON.stringify(steps), status: 'draft' });
      alert('Campaign saved!');
    } catch(e) { console.error(e); }
    finally { setSaving(false); }
  };

  const handleAISuggest = async () => {
    if (!aiIdea.trim()) return;
    setAiLoading(true);
    try {
      const resp = await suggestCampaign({ industry: 'B2B SaaS', goal: aiIdea });
      setAiResult(resp.data.suggestion);
    } catch(e) { console.error(e); }
    finally { setAiLoading(false); }
  };

  return (
    <div className="flex h-full gap-6 p-6">
      {/* Left panel — AI Assist */}
      <div className="w-80 flex-shrink-0 flex flex-col gap-4">
        <div className="card">
          <h3 className="font-semibold text-gray-100 mb-3 flex items-center gap-2">
            <Zap className="w-4 h-4 text-brand-400" /> AI Campaign Assistant
          </h3>
          <textarea value={aiIdea} onChange={e => setAiIdea(e.target.value)}
            placeholder="Describe your campaign goal..."
            rows={3} className="input w-full text-sm resize-none mb-3" />
          <button onClick={handleAISuggest} disabled={aiLoading}
            className="btn-pri w-full text-sm flex items-center justify-center gap-2">
            {aiLoading ? 'Thinking...' : '✨ Get AI Strategy'}
          </button>
          {aiResult && (
            <div className="mt-3 p-3 bg-gray-800 rounded-xl text-xs text-gray-300 leading-relaxed max-h-64 overflow-y-auto">
              {aiResult}
            </div>
          )}
        </div>

        {/* Add step palette */}
        <div className="card">
          <h3 className="font-semibold text-gray-100 mb-3">Flow Steps</h3>
          <div className="space-y-2">
            {STEP_TYPES.map(s => {
              const Icon = s.icon;
              return (
                <button key={s.type} onClick={() => addStep(s.type)}
                  className={clsx('w-full flex items-center gap-3 p-2.5 rounded-xl border transition-all hover:scale-[1.02]', s.color)}>
                  <Icon className="w-4 h-4" />
                  <span className="text-sm font-medium">{s.label}</span>
                  <Plus className="w-3.5 h-3.5 ml-auto" />
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Center — Flow canvas */}
      <div className="flex-1 flex flex-col">
        <div className="card mb-4 flex items-center gap-4">
          <input value={name} onChange={e => setName(e.target.value)}
            placeholder="Campaign name..." className="input flex-1 font-semibold" />
          <select value={type} onChange={e => setType(e.target.value)}
            className="input text-sm w-36">
            <option value="trigger">Trigger</option>
            <option value="batch">Batch</option>
          </select>
          <button onClick={handleSave} disabled={saving || !name || steps.length === 0}
            className="btn-pri flex items-center gap-2 text-sm">
            <Play className="w-4 h-4" /> Save Campaign
          </button>
        </div>

        <div className="flex-1 overflow-y-auto flex flex-col items-center py-4">
          {/* Trigger entry point */}
          <div className="card border border-brand-500/40 bg-brand-600/10 w-72 text-center mb-1">
            <p className="text-brand-300 font-semibold text-sm">🎯 Campaign Entry</p>
            <p className="text-xs text-gray-400 mt-0.5">Trigger or Batch start</p>
          </div>
          <div className="flex flex-col items-center my-1">
            <div className="w-0.5 h-5 bg-gray-600" />
            <ChevronRight className="w-3.5 h-3.5 text-gray-500 rotate-90" />
          </div>

          {steps.map((step, i) => (
            <FlowStep key={step.id} step={step} index={i}
              onRemove={removeStep} onChange={updateStep} />
          ))}

          {steps.length === 0 && (
            <div className="text-center py-16 text-gray-500">
              <p className="text-sm">Add flow steps from the left panel</p>
              <p className="text-xs mt-1">or ask AI to suggest a campaign strategy</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
