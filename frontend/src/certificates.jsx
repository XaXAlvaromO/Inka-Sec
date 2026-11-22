// Certificados por tema (RF-07): mi avance, descarga en PDF, renovación y verificación pública.
import { useEffect, useState } from 'react';
import { api } from './api';
import { Icon } from './InkaSecLayout';
import { EmptyState, Feedback, GenericPage, LoadingScreen, ProgressBar } from './ui';

const dateLabel = (value) => (value ? new Date(value).toLocaleDateString('es-PE', { dateStyle: 'long' }) : '—');
const STATUS_CLASS = { active: 'status-publicado', expiring: 'status-borrador', expired: 'status-archivado', superseded: 'status-archivado' };
export const verifyUrl = (code) => `${window.location.origin}/verificar/${code}`;

async function downloadPdf(cert) {
  const blob = await api.worker.certificatePdf(cert.id);
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `certificado-${cert.code}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function CertificateDetail({ cert, onRenew }) {
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  async function download() {
    setBusy(true); setMessage('');
    try { await downloadPdf(cert); }
    catch (err) { setMessage(err.message); }
    finally { setBusy(false); }
  }

  async function copy() {
    try { await navigator.clipboard.writeText(verifyUrl(cert.code)); setMessage('Enlace de verificación copiado.'); }
    catch { setMessage(`Enlace de verificación: ${verifyUrl(cert.code)}`); }
  }

  return <div className="certificate-detail">
    <dl>
      <div><dt>Código</dt><dd><code>{cert.code}</code></dd></div>
      <div><dt>Emitido</dt><dd>{dateLabel(cert.issued_at)}{cert.renewed ? ' (renovación)' : ''}</dd></div>
      <div><dt>{cert.status === 'expired' ? 'Venció' : 'Vence'}</dt><dd>{dateLabel(cert.expires_at)}{cert.status === 'expiring' ? ` · faltan ${Math.max(cert.days_left, 0)} días` : ''}</dd></div>
    </dl>
    <div className="lesson-actions">
      <button className="btn btn-secondary" disabled={busy} onClick={download}>{busy ? 'Preparando…' : 'Descargar PDF'}</button>
      <button className="btn btn-secondary" onClick={copy}>Copiar enlace de verificación</button>
      {cert.can_renew && <button className="btn btn-primary" onClick={() => onRenew(cert)}>Renovar con un repaso</button>}
    </div>
    {message && <p className="form-note" role="status">{message}</p>}
  </div>;
}

function TopicCard({ item, onOpenModule, onRenew }) {
  const cert = item.certificate;
  const percent = item.total ? Math.round((item.passed * 100) / item.total) : 0;
  return <article className="panel topic-certificate">
    <div className="panel-head">
      <div><span className="eyebrow">TEMA</span><h2>{item.topic}</h2></div>
      {cert
        ? <span className={`status ${STATUS_CLASS[cert.status]}`}>{cert.status_label}</span>
        : <span className="status status-borrador">En progreso · {item.passed} de {item.total}</span>}
    </div>
    {cert
      ? <CertificateDetail cert={cert} onRenew={onRenew}/>
      : <>
        <ProgressBar value={percent}/>
        <ul className="certificate-modules">
          {item.modules.map((m) => <li key={m.id}>
            <span className={`module-state ${m.passed ? 'is-done' : m.needs_review ? 'is-review' : ''}`}>
              <Icon name={m.passed ? 'check' : 'book'} size={16}/>
            </span>
            <div>
              <strong>{m.title}</strong>
              <small>{m.passed ? 'Aprobado' : m.needs_review ? 'Terminado: repite la práctica hasta llegar a 80 %' : 'Pendiente'}</small>
            </div>
            {!m.passed && <button className="text-button" onClick={() => onOpenModule(m.id)}>{m.needs_review ? 'Repasar' : 'Abrir'}</button>}
          </li>)}
        </ul>
      </>}
  </article>;
}

function RenewalQuiz({ cert, onBack, onRenewed }) {
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    api.worker.renewalQuiz(cert.id).then((data) => { if (active) setQuiz(data); }).catch((err) => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [cert.id]);

  if (error && !quiz) return <GenericPage eyebrow="RENOVACIÓN" title={`Certificado de ${cert.topic}`} description=""><article className="panel"><p className="form-error">{error}</p><button className="btn btn-secondary" onClick={onBack}>Volver</button></article></GenericPage>;
  if (!quiz) return <LoadingScreen/>;
  const complete = quiz.questions.every((q) => answers[q.key] !== undefined);

  async function submit() {
    setBusy(true); setError('');
    try {
      const data = await api.worker.renew(cert.id, { answers: quiz.questions.map((q) => ({ key: q.key, choice: answers[q.key] })) });
      setResult(data);
      if (data.passed) onRenewed?.();
    } catch (err) { setError(err.message || 'No se pudo enviar el repaso.'); }
    finally { setBusy(false); }
  }

  function retry() { setAnswers({}); setResult(null); }

  const byKey = Object.fromEntries((result?.results || []).map((r) => [r.key, r]));
  return <GenericPage eyebrow="RENOVACIÓN" title={`Repaso de ${cert.topic}`} description={`Responde las preguntas de práctica del tema. Con ${quiz.pass_percent} % o más, tu certificado se renueva por 12 meses.`}>
    <article className="panel lesson-panel">
      <button className="text-button" onClick={onBack}>← Volver a mis certificados</button>
      {quiz.questions.map((q, qi) => <fieldset className="quiz-item" key={q.key}>
        <legend><span className="likert-number">{qi + 1}</span>{q.prompt}</legend>
        <div className="choice-list" role="radiogroup" aria-label={q.prompt}>
          {q.options.map((option, oi) => <button key={oi} type="button" role="radio" aria-checked={answers[q.key] === oi} disabled={Boolean(result) || busy}
            className={`choice ${answers[q.key] === oi ? 'is-selected' : ''}`} onClick={() => setAnswers({ ...answers, [q.key]: oi })}>
            <span className="choice-dot" aria-hidden="true"/>{option}
          </button>)}
        </div>
        {byKey[q.key] && <Feedback result={byKey[q.key]} correctText={q.options[byKey[q.key].correct_index]}/>}
      </fieldset>)}
      {result && (result.passed
        ? <div className="feedback-box is-correct" role="status"><strong>Certificado renovado</strong><p>Nuevo código {result.certificate.code}, válido hasta el {dateLabel(result.certificate.expires_at)}.</p></div>
        : <div className="feedback-box is-wrong" role="status"><strong>Aún no llegas al {quiz.pass_percent} %</strong><p>Respondiste {result.correct} de {result.total}. Revisa las explicaciones y vuelve a intentarlo cuando quieras.</p></div>)}
      {error && <div className="form-error" role="alert">{error}</div>}
      <div className="lesson-actions">
        {!result && <button className="btn btn-primary" disabled={!complete || busy} onClick={submit}>{busy ? 'Revisando…' : 'Enviar repaso'}</button>}
        {result && !result.passed && <button className="btn btn-primary" onClick={retry}>Intentar de nuevo</button>}
        {result?.passed && <button className="btn btn-primary" onClick={onBack}>Ver mis certificados</button>}
      </div>
    </article>
  </GenericPage>;
}

export function CertificatesPage({ onOpenModule, onChanged }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [renewing, setRenewing] = useState(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    api.worker.certificates().then((value) => { if (active) setData(value); }).catch((err) => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [reload]);

  if (renewing) return <RenewalQuiz cert={renewing} onBack={() => { setRenewing(null); setReload((n) => n + 1); }} onRenewed={onChanged}/>;
  if (error) return <div className="fatal-state inside"><h2>No pudimos cargar tus certificados</h2><p>{error}</p></div>;
  if (!data) return <LoadingScreen/>;
  const earned = data.topics.filter((t) => t.certificate);
  const pending = data.topics.filter((t) => !t.certificate);

  return <GenericPage eyebrow="CERTIFICACIÓN" title="Mis certificados" description={`Uno por tema. Se obtiene al completar todos los módulos del tema con al menos ${data.pass_percent} % en sus preguntas de práctica.`}>
    <article className="panel certificate-rules">
      <Icon name="award" size={22}/>
      <p>Cada certificado vale <strong>12 meses</strong>. Desde {data.warning_days} días antes de que venza puedes renovarlo con un repaso corto. Puedes repetir los módulos y el repaso las veces que necesites: se guarda tu mejor resultado y el certificado no muestra puntajes.</p>
    </article>
    {data.new.length > 0 && <div className="feedback-box is-correct" role="status"><strong>¡Nuevo certificado!</strong><p>Obtuviste el certificado de {data.new.join(', ')}.</p></div>}
    {data.topics.length === 0 && <article className="panel"><EmptyState title="Aún no tienes módulos asignados" description="Cuando tengas módulos, aquí verás qué te falta para certificarte en cada tema."/></article>}
    {earned.length > 0 && <h2 className="section-title">Obtenidos</h2>}
    {earned.map((item) => <TopicCard key={item.topic} item={item} onOpenModule={onOpenModule} onRenew={setRenewing}/>)}
    {pending.length > 0 && <h2 className="section-title">En progreso</h2>}
    {pending.map((item) => <TopicCard key={item.topic} item={item} onOpenModule={onOpenModule} onRenew={setRenewing}/>)}
    {data.history.length > 0 && <article className="panel">
      <span className="eyebrow">HISTORIAL</span><h2>Certificados reemplazados por una renovación</h2>
      <ul className="certificate-history">{data.history.map((c) => <li key={c.id}><strong>{c.topic}</strong> · {c.code} · {dateLabel(c.issued_at)} a {dateLabel(c.expires_at)}</li>)}</ul>
    </article>}
  </GenericPage>;
}

export function CertificateHomeCard({ summary, setView }) {
  const expiring = summary?.expiring?.[0] || summary?.expired?.[0];
  let text = 'Completa los módulos de un tema con al menos 80 % en la práctica para obtener su certificado.';
  if (expiring) text = expiring.status === 'expired' ? `Tu certificado de ${expiring.topic} venció. Renuévalo con un repaso corto.` : `Tu certificado de ${expiring.topic} vence en ${Math.max(expiring.days_left, 0)} días.`;
  else if (summary?.next) text = `Te ${summary.next.remaining === 1 ? 'falta 1 módulo' : `faltan ${summary.next.remaining} módulos`} para el certificado de ${summary.next.topic}.`;
  return <article className="panel certificate-card">
    <span className="certificate-mark"><Icon name="award" size={28}/></span>
    <span className="eyebrow">CERTIFICACIÓN</span>
    <h2>{summary?.active ? `${summary.active} de ${summary.topics} temas certificados` : 'Certificados por tema'}</h2>
    <p>{text}</p>
    <button className="btn btn-secondary" onClick={() => setView('certificados')}>Ver mis certificados</button>
  </article>;
}

export function VerifyCertificatePage({ code: initialCode }) {
  const [code, setCode] = useState(initialCode || '');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function check(value) {
    const clean = value.trim().toUpperCase();
    if (!clean) return;
    setBusy(true); setError(''); setResult(null);
    try { setResult(await api.certificates.verify(clean)); }
    catch (err) { setError(err.status === 404 ? 'No existe un certificado con ese código. Revisa que esté bien escrito.' : err.message); }
    finally { setBusy(false); }
  }

  useEffect(() => {
    if (!initialCode) return undefined;
    let active = true;
    api.certificates.verify(initialCode.toUpperCase())
      .then((data) => { if (active) setResult(data); })
      .catch((err) => { if (active) setError(err.status === 404 ? 'No existe un certificado con ese código. Revisa que esté bien escrito.' : err.message); });
    return () => { active = false; };
  }, [initialCode]);

  function submit(e) {
    e.preventDefault();
    window.history.replaceState(null, '', `/verificar/${code.trim().toUpperCase()}`);
    check(code);
  }

  return <main className="inka-app verify-page">
    <article className="panel verify-card">
      <span className="certificate-mark"><Icon name="award" size={28}/></span>
      <span className="eyebrow">INKASEC · VERIFICACIÓN</span>
      <h1>Verificar un certificado</h1>
      <p className="muted-text">Escribe el código que aparece en el certificado, por ejemplo INKA-7KQ2-M9XP-4HTR.</p>
      <form className="verify-form" onSubmit={submit}>
        <input aria-label="Código del certificado" value={code} maxLength={40} placeholder="INKA-XXXX-XXXX-XXXX" onChange={(e) => setCode(e.target.value)}/>
        <button className="btn btn-primary" disabled={busy || !code.trim()}>{busy ? 'Verificando…' : 'Verificar'}</button>
      </form>
      {error && <div className="feedback-box is-wrong" role="alert"><strong>No encontrado</strong><p>{error}</p></div>}
      {result && <div className={`feedback-box ${result.valid ? 'is-correct' : 'is-wrong'}`} role="status">
        <strong>{result.valid ? 'Certificado válido' : `Certificado ${result.status_label.toLowerCase()}`}</strong>
        <p><b>{result.holder}</b>{result.company ? ` (${result.company})` : ''} aprobó el tema <b>{result.topic}</b>.</p>
        <p>Emitido el {dateLabel(result.issued_at)} · {result.valid ? 'válido hasta' : 'vigencia hasta'} el {dateLabel(result.expires_at)}.</p>
        {result.status === 'superseded' && <p>Este certificado fue reemplazado por una renovación con un código nuevo.</p>}
      </div>}
      <a className="text-button" href="/">Ir a InkaSec</a>
    </article>
  </main>;
}
