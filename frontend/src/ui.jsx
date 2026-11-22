// Piezas de interfaz compartidas por las vistas de InkaSec.
import { Icon } from './InkaSecLayout';

export const STATUS_OPTIONS = [{ value: 'draft', label: 'Borrador' }, { value: 'published', label: 'Publicado' }, { value: 'archived', label: 'Archivado' }];

export function ProgressBar({ value, danger = false }) {
  return <div className={`progress-track ${danger ? 'is-danger' : ''}`} aria-label={`${value}%`}><span style={{ width: `${Math.max(0, Math.min(100, value))}%` }}/></div>;
}

export function EmptyState({ title, description }) {
  return <div className="empty-state"><span><Icon name="shield" size={28}/></span><h3>{title}</h3><p>{description}</p></div>;
}

export function LoadingScreen() {
  return <div className="inka-loading"><span className="inka-brand-mark"><Icon name="shield" size={22}/></span><div className="loading-bar"><span/></div><p>Preparando tu espacio seguro…</p></div>;
}

export function Feedback({ result, correctText }) {
  return (
    <div className={`feedback-box ${result.is_correct ? 'is-correct' : 'is-wrong'}`} role="status">
      <strong>{result.is_correct ? '¡Correcto!' : 'Revisa esta respuesta'}</strong>
      {!result.is_correct && correctText && <p>Respuesta correcta: {correctText}</p>}
      {result.feedback && <p>{result.feedback}</p>}
    </div>
  );
}

export function GenericPage({ eyebrow, title, description, children }) {
  return <><section className="simple-heading"><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></section>{children}</>;
}

export function OptionsEditor({ name, options, correct, onText, onCorrect, onAdd, onRemove }) {
  return <div className="option-editor">
    {options.map((option, index) => <div className="option-row" key={index}>
      <label className="option-pick"><input type="radio" name={name} checked={correct === index} onChange={() => onCorrect(index)}/><span>Correcta</span></label>
      <input value={option} placeholder={`Opción ${index + 1}`} maxLength={200} aria-label={`Opción ${index + 1}`} onChange={(e) => onText(index, e.target.value)}/>
      {options.length > 2 && <button type="button" className="text-button danger-text" onClick={() => onRemove(index)}>Quitar</button>}
    </div>)}
    {options.length < 4 && <button type="button" className="text-button" onClick={onAdd}>+ Agregar opción</button>}
  </div>;
}
