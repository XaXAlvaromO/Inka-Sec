// Retos: los tres formatos para el trabajador y su editor para el gestor.
// El reto entrena, no sanciona: se puede repetir y fallar siempre muestra la explicación.
import { useState } from 'react';
import { api } from './api';
import { Icon } from './InkaSecLayout';
import { Feedback, GenericPage, OptionsEditor, STATUS_OPTIONS } from './ui';

export const KIND_LABEL = { quick: 'Reto rápido', steps: 'Escenario por pasos', signals: 'Encuentra las señales' };
const KIND_HELP = {
  quick: 'Un caso y una decisión. Ideal para repasar una regla concreta.',
  steps: 'Una situación en 2 a 5 decisiones seguidas. Cada opción muestra qué pasaría.',
  signals: 'Un correo o mensaje dividido en partes. La persona marca lo sospechoso.',
};
const PLAYER_HELP = {
  quick: 'Lee el caso y elige qué harías. Puedes practicarlo las veces que quieras.',
  steps: 'Decide paso a paso. Después de cada decisión verás qué pasaría.',
  signals: 'Toca las partes del mensaje que te parezcan sospechosas y luego revisa.',
};
const FIELD_LABEL = { from: 'De', subject: 'Asunto', body: 'Texto', link: 'Enlace', attachment: 'Adjunto' };

function ResultBanner({ good, title, detail }) {
  return <div className={`feedback-box ${good ? 'is-correct' : 'is-wrong'}`} role="status"><strong>{title}</strong>{detail && <p>{detail}</p>}</div>;
}

function Actions({ onRetry, onDone }) {
  return <div className="lesson-actions">
    <button className="btn btn-secondary" onClick={onRetry}>Intentar de nuevo</button>
    <button className="btn btn-primary" onClick={onDone}>Volver a mis retos</button>
  </div>;
}

function QuickPlayer({ challenge, onRetry, onDone }) {
  const [choice, setChoice] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true); setError('');
    try { setResult(await api.worker.answerChallenge(challenge.id, { choice })); }
    catch (err) { setError(err.message || 'No se pudo enviar tu respuesta.'); }
    finally { setBusy(false); }
  }

  return <>
    <div className="scenario-box"><Icon name="target" size={20}/><p>{challenge.description}</p></div>
    <div className="choice-list" role="radiogroup" aria-label="Opciones del reto">
      {challenge.options.map((option, index) => {
        const isCorrect = result && result.correct_index === index;
        const isWrong = result && !result.is_correct && choice === index;
        const classes = ['choice', choice === index && 'is-selected', isCorrect && 'is-correct', isWrong && 'is-wrong'].filter(Boolean).join(' ');
        return <button key={index} type="button" role="radio" aria-checked={choice === index} disabled={Boolean(result) || busy} className={classes} onClick={() => setChoice(index)}>
          <span className="choice-letter" aria-hidden="true">{String.fromCharCode(65 + index)}</span>{option}
        </button>;
      })}
    </div>
    {error && <div className="form-error" role="alert">{error}</div>}
    {result
      ? <><Feedback result={result} correctText={result.is_correct ? '' : challenge.options[result.correct_index]}/><Actions onRetry={onRetry} onDone={onDone}/></>
      : <div className="lesson-actions"><button className="btn btn-primary" disabled={choice === null || busy} onClick={submit}>{busy ? 'Enviando…' : 'Enviar respuesta'}</button></div>}
  </>;
}

function StepsPlayer({ challenge, onRetry, onDone }) {
  const steps = challenge.steps;
  const [index, setIndex] = useState(0);
  const [choices, setChoices] = useState([]);
  const [pick, setPick] = useState(null);
  const [check, setCheck] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const step = steps[index];
  const last = index === steps.length - 1;

  async function confirm() {
    setBusy(true); setError('');
    try { setCheck(await api.worker.checkStep(challenge.id, { step: index, choice: pick })); }
    catch (err) { setError(err.message || 'No se pudo revisar tu decisión.'); }
    finally { setBusy(false); }
  }

  async function next() {
    const all = [...choices, pick];
    if (!last) { setChoices(all); setIndex(index + 1); setPick(null); setCheck(null); return; }
    setBusy(true); setError('');
    try { setResult(await api.worker.answerChallenge(challenge.id, { choices: all })); }
    catch (err) { setError(err.message || 'No se pudo guardar tu práctica.'); }
    finally { setBusy(false); }
  }

  // Volver un paso recupera la decisión que ya habías tomado ahí, por si quieres cambiarla.
  function stepBack() {
    if (index === 0) return;
    setError('');
    setPick(choices[index - 1]);
    setChoices(choices.slice(0, -1));
    setIndex(index - 1);
    setCheck(null);
  }

  if (result) {
    return <>
      <ResultBanner good={result.is_correct}
        title={result.is_correct ? 'Tomaste todas las decisiones seguras' : `Tomaste ${result.safe_steps} de ${result.total_steps} decisiones seguras`}
        detail={result.is_correct ? result.feedback : 'Revisa qué pasó en cada paso y vuelve a intentarlo cuando quieras.'}/>
      <ol className="steps-summary">
        {result.steps.map((s, i) => <li key={i} className={s.safe ? 'is-safe' : 'is-risky'}>
          <strong>Paso {i + 1}: {steps[i].prompt}</strong>
          <p>Elegiste: {steps[i].options[s.choice]} {s.safe ? '· decisión segura' : '· decisión riesgosa'}</p>
          {!s.safe && <p>Lo seguro era: {steps[i].options[s.safe_index]}. {s.safe_feedback}</p>}
        </li>)}
      </ol>
      {!result.is_correct && result.feedback && <p className="lesson-lead">{result.feedback}</p>}
      <Actions onRetry={onRetry} onDone={onDone}/>
    </>;
  }

  return <>
    {index === 0 && <div className="scenario-box"><Icon name="target" size={20}/><p>{challenge.description}</p></div>}
    <div className="lesson-top-actions">
      <p className="step-counter">Paso {index + 1} de {steps.length}</p>
      {index > 0 && <button className="text-button" onClick={stepBack}>← Paso anterior</button>}
    </div>
    <h2 className="step-prompt">{step.prompt}</h2>
    <div className="choice-list" role="radiogroup" aria-label={`Opciones del paso ${index + 1}`}>
      {step.options.map((option, i) => {
        const classes = ['choice', pick === i && 'is-selected', check && check.safe_index === i && 'is-correct', check && !check.safe && pick === i && 'is-wrong'].filter(Boolean).join(' ');
        return <button key={i} type="button" role="radio" aria-checked={pick === i} disabled={Boolean(check) || busy} className={classes} onClick={() => setPick(i)}>
          <span className="choice-letter" aria-hidden="true">{String.fromCharCode(65 + i)}</span>{option}
        </button>;
      })}
    </div>
    {check && <ResultBanner good={check.safe} title={check.safe ? 'Decisión segura' : 'Esta decisión es riesgosa'}
      detail={check.safe ? check.feedback : `${check.feedback} Lo seguro: ${step.options[check.safe_index]}. ${check.safe_feedback}`}/>}
    {error && <div className="form-error" role="alert">{error}</div>}
    <div className="lesson-actions">
      {!check
        ? <button className="btn btn-primary" disabled={pick === null || busy} onClick={confirm}>{busy ? 'Revisando…' : 'Confirmar decisión'}</button>
        : <button className="btn btn-primary" disabled={busy} onClick={next}>{last ? (busy ? 'Guardando…' : 'Ver resultado') : 'Siguiente paso'}</button>}
    </div>
  </>;
}

function Segment({ segment, marked, review, onToggle, disabled }) {
  let state = marked ? 'is-marked' : '';
  let note = null;
  if (review) {
    if (review.suspicious && review.marked) { state = 'is-found'; note = 'Señal encontrada'; }
    else if (review.suspicious) { state = 'is-missed'; note = 'Se te pasó esta señal'; }
    else if (review.marked) { state = 'is-false'; note = 'No era una señal'; }
    else { state = 'is-normal'; }
  }
  return <div className={`signal-segment field-${segment.field} ${state}`}>
    <button type="button" aria-pressed={marked} disabled={disabled} onClick={onToggle}>
      {['from', 'subject', 'attachment'].includes(segment.field) && <span className="signal-label">{FIELD_LABEL[segment.field]}:</span>}
      <span className="signal-text">{segment.text}</span>
    </button>
    {review && (note || review.explanation) && <p className="signal-note">{note && <strong>{note}. </strong>}{review.explanation}</p>}
  </div>;
}

function SignalsPlayer({ challenge, onRetry, onDone }) {
  const [marked, setMarked] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const toggle = (i) => setMarked((prev) => (prev.includes(i) ? prev.filter((x) => x !== i) : [...prev, i]));
  const segments = challenge.segments.map((s, i) => ({ ...s, index: i }));
  const header = segments.filter((s) => s.field === 'from' || s.field === 'subject');
  const body = segments.filter((s) => s.field !== 'from' && s.field !== 'subject');

  async function submit() {
    setBusy(true); setError('');
    try { setResult(await api.worker.answerChallenge(challenge.id, { marked })); }
    catch (err) { setError(err.message || 'No se pudo revisar el mensaje.'); }
    finally { setBusy(false); }
  }

  const render = (s) => <Segment key={s.index} segment={s} marked={marked.includes(s.index)} review={result?.segments[s.index]}
    disabled={Boolean(result) || busy} onToggle={() => toggle(s.index)}/>;

  return <>
    <div className="scenario-box"><Icon name="target" size={20}/><p>{challenge.description}</p></div>
    <article className="mail-preview" aria-label="Mensaje para revisar">
      <header>{header.map(render)}</header>
      <div className="mail-body">{body.map(render)}</div>
    </article>
    {!result && <p className="muted-text">Marcaste {marked.length} {marked.length === 1 ? 'parte' : 'partes'}. Toca de nuevo para desmarcar.</p>}
    {result && <ResultBanner good={result.is_correct}
      title={result.is_correct ? 'Encontraste todas las señales' : `Encontraste ${result.found} de ${result.total_signals} señales`}
      detail={result.false_marks ? `Marcaste ${result.false_marks} ${result.false_marks === 1 ? 'parte normal' : 'partes normales'} como sospechosa${result.false_marks === 1 ? '' : 's'}. ${result.feedback}` : result.feedback}/>}
    {error && <div className="form-error" role="alert">{error}</div>}
    {result
      ? <Actions onRetry={onRetry} onDone={onDone}/>
      : <div className="lesson-actions"><button className="btn btn-primary" disabled={busy} onClick={submit}>{busy ? 'Revisando…' : 'Revisar mensaje'}</button></div>}
  </>;
}

export function ChallengePlayer({ challenge, onBack, onDone }) {
  const [round, setRound] = useState(0);   // cambiar la clave reinicia el reto para practicar otra vez
  const kind = challenge.kind || 'quick';
  const Player = kind === 'steps' ? StepsPlayer : kind === 'signals' ? SignalsPlayer : QuickPlayer;
  return <GenericPage eyebrow={`${challenge.topic || 'RETO'} · ${KIND_LABEL[kind]}`} title={challenge.title} description={PLAYER_HELP[kind]}>
    <article className="panel lesson-panel">
      <button className="text-button" onClick={onBack}>← Volver a mis retos</button>
      <Player key={round} challenge={challenge} onRetry={() => setRound((r) => r + 1)} onDone={onDone}/>
    </article>
  </GenericPage>;
}

// ---------------------------------------------------------------- Editor del gestor

const blankStep = () => ({ prompt: '', options: [{ text: '', feedback: '', safe: true }, { text: '', feedback: '', safe: false }] });
const blankSegments = () => [
  { field: 'from', text: '', suspicious: false, explanation: '' },
  { field: 'subject', text: '', suspicious: false, explanation: '' },
  { field: 'body', text: '', suspicious: false, explanation: '' },
];

function StepsEditor({ steps, onChange }) {
  const setStep = (i, patch) => onChange(steps.map((s, j) => (j === i ? { ...s, ...patch } : s)));
  const setOption = (i, o, patch) => setStep(i, { options: steps[i].options.map((x, k) => (k === o ? { ...x, ...patch } : x)) });
  const makeSafe = (i, o) => setStep(i, { options: steps[i].options.map((x, k) => ({ ...x, safe: k === o })) });
  function removeOption(i, o) {
    const options = steps[i].options.filter((_, k) => k !== o);
    if (!options.some((x) => x.safe)) options[0] = { ...options[0], safe: true };
    setStep(i, { options });
  }
  return <>
    {steps.map((step, i) => <fieldset className="question-card" key={i}>
      <legend>Paso {i + 1}</legend>
      <label>¿Qué pasa en este momento?<textarea rows={2} maxLength={400} required value={step.prompt} onChange={(e) => setStep(i, { prompt: e.target.value })}/></label>
      {step.options.map((option, o) => <div className="step-option" key={o}>
        <div className="option-row">
          <label className="option-pick"><input type="radio" name={`safe-${i}`} checked={option.safe} onChange={() => makeSafe(i, o)}/><span>Segura</span></label>
          <input value={option.text} placeholder={`Opción ${o + 1}`} maxLength={200} required aria-label={`Paso ${i + 1}, opción ${o + 1}`} onChange={(e) => setOption(i, o, { text: e.target.value })}/>
          {step.options.length > 2 && <button type="button" className="text-button danger-text" onClick={() => removeOption(i, o)}>Quitar</button>}
        </div>
        <input className="option-feedback" value={option.feedback} placeholder="Qué pasaría si elige esta opción" maxLength={300} required aria-label={`Consecuencia de la opción ${o + 1}`} onChange={(e) => setOption(i, o, { feedback: e.target.value })}/>
      </div>)}
      {step.options.length < 4 && <button type="button" className="text-button" onClick={() => setStep(i, { options: [...step.options, { text: '', feedback: '', safe: false }] })}>+ Agregar opción</button>}
      {steps.length > 2 && <button type="button" className="text-button danger-text" onClick={() => onChange(steps.filter((_, j) => j !== i))}>Quitar paso</button>}
    </fieldset>)}
    {steps.length < 5 && <button type="button" className="btn btn-secondary" onClick={() => onChange([...steps, blankStep()])}>Agregar paso</button>}
  </>;
}

function SignalsEditor({ segments, onChange }) {
  const setSegment = (i, patch) => onChange(segments.map((s, j) => (j === i ? { ...s, ...patch } : s)));
  return <>
    <p className="form-note">Divide el mensaje en partes. Debe tener un remitente («De») y un asunto, al menos una parte sospechosa y al menos una normal.</p>
    {segments.map((segment, i) => <fieldset className="question-card segment-card" key={i}>
      <legend>Parte {i + 1}</legend>
      <div className="form-grid">
        <label>Tipo<select value={segment.field} onChange={(e) => setSegment(i, { field: e.target.value })}>{Object.entries(FIELD_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label className="admin-checkbox"><input type="checkbox" checked={segment.suspicious} onChange={(e) => setSegment(i, { suspicious: e.target.checked })}/>Es una señal sospechosa</label>
      </div>
      <label>Texto<input value={segment.text} maxLength={300} required onChange={(e) => setSegment(i, { text: e.target.value })}/></label>
      <label>Explicación que verá al revisar<input value={segment.explanation} maxLength={300} required onChange={(e) => setSegment(i, { explanation: e.target.value })}/></label>
      {segments.length > 3 && <button type="button" className="text-button danger-text" onClick={() => onChange(segments.filter((_, j) => j !== i))}>Quitar parte</button>}
    </fieldset>)}
    {segments.length < 12 && <button type="button" className="btn btn-secondary" onClick={() => onChange([...segments, { field: 'body', text: '', suspicious: false, explanation: '' }])}>Agregar parte</button>}
  </>;
}

export function ChallengeEditor({ initial, topics, onDone, onClose }) {
  const [form, setForm] = useState(() => {
    const base = { title: '', topic: topics[0] || '', kind: 'quick', scenario: '', options: ['', ''], correct_index: 0, feedback: '', status: 'draft', steps: [], segments: [] };
    const merged = { ...base, ...initial };
    if (!merged.options.length) merged.options = ['', ''];
    if (!merged.steps.length) merged.steps = [blankStep(), blankStep()];
    if (!merged.segments.length) merged.segments = blankSegments();
    return merged;
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const topicOptions = form.topic && !topics.includes(form.topic) ? [form.topic, ...topics] : topics;
  const set = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));
  function removeOption(oIndex) {
    setForm((prev) => ({ ...prev, options: prev.options.filter((_, j) => j !== oIndex),
      correct_index: prev.correct_index === oIndex ? 0 : prev.correct_index > oIndex ? prev.correct_index - 1 : prev.correct_index }));
  }

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError('');
    const payload = { title: form.title.trim(), topic: form.topic, kind: form.kind, scenario: form.scenario.trim(),
      feedback: form.feedback.trim(), status: form.status };
    if (form.kind === 'quick') Object.assign(payload, { options: form.options.map((o) => o.trim()), correct_index: form.correct_index });
    if (form.kind === 'steps') payload.steps = form.steps.map((s) => ({ prompt: s.prompt.trim(), options: s.options.map((o) => ({ text: o.text.trim(), feedback: o.feedback.trim(), safe: o.safe })) }));
    if (form.kind === 'signals') payload.segments = form.segments.map((s) => ({ ...s, text: s.text.trim(), explanation: s.explanation.trim() }));
    try {
      if (initial) await api.manager.updateChallenge(initial.id, payload);
      else await api.manager.createChallenge(payload);
      onDone();
    } catch (err) { setError(err.message || 'No se pudo guardar el reto.'); }
    finally { setBusy(false); }
  }

  return <form className="modal-form manager-editor" onSubmit={submit}>
    <fieldset className="kind-picker">
      <legend>Formato del reto</legend>
      {Object.entries(KIND_LABEL).map(([value, label]) => <label key={value} className={form.kind === value ? 'is-selected' : ''}>
        <input type="radio" name="kind" value={value} checked={form.kind === value} onChange={() => set('kind', value)}/>
        <strong>{label}</strong><small>{KIND_HELP[value]}</small>
      </label>)}
    </fieldset>
    <label>Título<input value={form.title} maxLength={180} required onChange={(e) => set('title', e.target.value)}/></label>
    <div className="form-grid">
      <label>Tema<select value={form.topic} onChange={(e) => set('topic', e.target.value)}>{topicOptions.map((t) => <option key={t}>{t}</option>)}</select></label>
      <label>Estado<select value={form.status} onChange={(e) => set('status', e.target.value)}>{STATUS_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}</select></label>
    </div>
    <label>{form.kind === 'signals' ? 'Contexto (cuándo y cómo llegó el mensaje)' : 'Escenario'}<textarea rows={3} maxLength={1000} required value={form.scenario} onChange={(e) => set('scenario', e.target.value)}/></label>
    {form.kind === 'quick' && <>
      <h3 className="editor-heading">Opciones de respuesta</h3>
      <OptionsEditor name="correct-challenge" options={form.options} correct={form.correct_index}
        onText={(o, value) => set('options', form.options.map((x, j) => (j === o ? value : x)))}
        onCorrect={(c) => set('correct_index', c)}
        onAdd={() => set('options', [...form.options, ''])}
        onRemove={removeOption}/>
    </>}
    {form.kind === 'steps' && <><h3 className="editor-heading">Pasos (2 a 5)</h3><StepsEditor steps={form.steps} onChange={(steps) => set('steps', steps)}/></>}
    {form.kind === 'signals' && <><h3 className="editor-heading">Partes del mensaje (3 a 12)</h3><SignalsEditor segments={form.segments} onChange={(segments) => set('segments', segments)}/></>}
    <label>Mensaje final para recordar<textarea rows={2} maxLength={300} value={form.feedback} onChange={(e) => set('feedback', e.target.value)}/></label>
    {error && <div className="form-error" role="alert">{error}</div>}
    <div className="modal-actions"><button type="button" className="btn btn-secondary" onClick={onClose}>Cancelar</button><button type="submit" className="btn btn-primary" disabled={busy}>{busy ? 'Guardando…' : 'Guardar reto'}</button></div>
  </form>;
}
