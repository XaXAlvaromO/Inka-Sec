import { Component, Fragment, useEffect, useState } from 'react';
import { AuthProvider, useAuth } from './AuthContext';
import InkaSecLayout, { Icon } from './InkaSecLayout';
import { api } from './api';
import { ADMIN_PATHS, adminViewFromPath } from './adminRoutes';
import ParticleNetwork from './ParticleNetwork';
import { EmptyState, Feedback, GenericPage, LoadingScreen, OptionsEditor, ProgressBar, STATUS_OPTIONS } from './ui';
import { ChallengeEditor, ChallengePlayer, KIND_LABEL } from './challenges';
import { CertificateHomeCard, CertificatesPage, VerifyCertificatePage } from './certificates';
import './inka-sec.css';

function StatCard({ item }) {
  return <article className="stat-card"><span className={`stat-icon tone-${item.tone || 'violet'}`}><Icon name={item.icon}/></span><div><small>{item.label}</small><strong>{item.value}</strong><p>{item.helper}</p></div></article>;
}

function LoginPage() {
  const { login, verify2FA } = useAuth();
  const [step, setStep] = useState('credentials');
  const [form, setForm] = useState({ email: '', password: '', code: '' });
  const [challenge, setChallenge] = useState(null);
  const [emailHint, setEmailHint] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submitCredentials(e) {
    e.preventDefault(); setError(''); setBusy(true);
    try {
      const result = await login({ email: form.email.trim(), password: form.password });
      if (result?.requires_2fa) { setChallenge(result.challenge_id); setEmailHint(result.email_hint || 'tu correo'); setStep('2fa'); }
    } catch (err) { setError(err.message || 'No se pudo iniciar sesión.'); }
    finally { setBusy(false); }
  }

  async function submit2FA(e) {
    e.preventDefault(); setError(''); setBusy(true);
    try { await verify2FA({ challenge_id: challenge, code: form.code.trim() }); }
    catch (err) { setError(err.message || 'No se pudo verificar el código.'); }
    finally { setBusy(false); }
  }

  return (
    <div className="login-page">
      <ParticleNetwork maxParticles={120} />
      <section className="login-brand-panel">
        <div className="login-brand"><span className="inka-brand-mark"><Icon name="shield" size={20}/></span><span className="inka-brand-word">Inka<span>Sec</span></span></div>
        <div className="login-message"><span className="eyebrow">CAPACITACIÓN</span><h1>Seguridad digital, <em>sin complicaciones.</em></h1><p>Aprende a reconocer riesgos reales, practica con escenarios breves y fortalece la seguridad de tu organización.</p></div>
        <div className="login-trust"><div><Icon name="lock" size={18}/><span><strong>Acceso protegido</strong><small>Sesión corporativa y código al correo para roles críticos</small></span></div><div><Icon name="shield" size={18}/><span><strong>Privacidad por diseño</strong><small>El navegador no almacena tokens de producción</small></span></div></div>
      </section>

      <section className="login-form-panel">
        <div className="login-card">
          {step === 'credentials' ? (
            <form onSubmit={submitCredentials}>
              <span className="eyebrow">BIENVENIDO</span><h2>Inicia sesión</h2><p className="form-intro">Usa tus credenciales corporativas para acceder a tu panel.</p>
              <label>Correo corporativo<input type="email" autoComplete="username" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required /></label>
              <label>Contraseña<input type="password" autoComplete="current-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} minLength={8} required /></label>
              {error && <div className="form-error" role="alert">{error}</div>}
              <button className="btn btn-primary btn-block btn-lg" disabled={busy}>{busy ? 'Verificando…' : 'Continuar'} <Icon name="chevron" size={18}/></button>
            </form>
          ) : (
            <form onSubmit={submit2FA}>
              <span className="security-seal"><Icon name="lock" size={25}/></span><span className="eyebrow">VERIFICACIÓN EN DOS PASOS</span><h2>Confirma que eres tú</h2><p className="form-intro">Enviamos un código de 6 dígitos a <strong>{emailHint}</strong>. Vence en 5 minutos.</p>
              <label>Código de seguridad<input className="otp-input" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.replace(/\D/g, '') })} placeholder="000000" required /></label>
              {error && <div className="form-error" role="alert">{error}</div>}
              <button className="btn btn-primary btn-block btn-lg" disabled={busy || form.code.length !== 6}>{busy ? 'Verificando…' : 'Verificar y entrar'}</button>
              <p className="form-note">¿No llegó? Revisa spam o vuelve a iniciar sesión para recibir uno nuevo.</p>
              <button className="text-link" type="button" onClick={() => { setStep('credentials'); setError(''); setForm({ ...form, code: '' }); }}>Volver al inicio de sesión</button>
            </form>
          )}
        </div>
      </section>
    </div>
  );
}

function WorkerHome({ data, setView, onOpen, onChallenge }) {
  return <>
    <section className="page-hero compact-hero"><div><span className="eyebrow">TU RUTA DE APRENDIZAJE</span><h1>Aprende a protegerte <span>con decisiones simples.</span></h1><p>Continúa donde lo dejaste y practica con situaciones reales de tu trabajo.</p><div className="hero-actions"><button className="btn btn-primary" onClick={() => setView('modulos')}>Continuar aprendiendo <Icon name="chevron" size={17}/></button><button className="btn btn-secondary" onClick={() => setView('progreso')}>Ver mi progreso</button></div></div><article className="progress-summary"><div className="progress-ring" style={{ '--value': `${data.progress * 3.6}deg` }}><span><strong>{data.progress}%</strong><small>completado</small></span></div><div><small>Avance general</small><h3>Tu constancia está dando resultados</h3><p>Completa 2 módulos más para finalizar la ruta básica.</p></div></article></section>
    <section className="stats-grid">{data.stats.map((item) => <StatCard key={item.label} item={item}/>)}</section>
    <section className="two-col-grid"><article className="panel"><div className="panel-head"><div><span className="eyebrow">ASIGNADOS A TI</span><h2>Continúa aprendiendo</h2></div><button className="text-button" onClick={() => setView('modulos')}>Ver todos</button></div><ModuleList modules={data.modules} onOpen={onOpen} /></article><ChallengeCard challenge={data.challenge} onResolve={onChallenge}/></section>
    <section className="two-col-grid lower"><article className="panel"><div className="panel-head"><div><span className="eyebrow">MEJORA CONTINUA</span><h2>Temas a reforzar</h2></div></div><div className="topic-list">{data.weakTopics.map((item) => <div key={item.name}><span className="topic-icon"><Icon name={item.icon}/></span><div><strong>{item.name}</strong><small>{item.errors} errores recientes</small></div><div className="topic-score"><b>{item.score}%</b><ProgressBar value={item.score}/></div></div>)}</div></article><CertificateHomeCard summary={data.certificates} setView={setView}/></section>
  </>;
}

function ModuleList({ modules, onOpen }) {
  return (
    <div className="module-list">
      {modules.map((module) => (
        <article className="module-row" key={module.id}>
          <span className="module-icon">
            <Icon name={module.icon}/>
          </span>

          <div className="module-copy">
            <div className="module-topline">
              <span>{module.topic}</span>
              <small>{module.due}</small>
            </div>

            <h3>{module.title}</h3>

            <div className="module-meta">
              <span>{module.time}</span>
              <b>{module.progress}%</b>
            </div>

            <ProgressBar value={module.progress}/>
          </div>

          <button
            className="round-button"
            aria-label={`Abrir ${module.title}`}
            onClick={() => onOpen(module.id)}
          >
            <Icon name="chevron" size={17}/>
          </button>
        </article>
      ))}
    </div>
  );
}

function ChallengeCard({ challenge, onResolve }) {
  if (!challenge) return <article className="panel challenge-card"><EmptyState title="Sin retos pendientes" description="Cuando haya un nuevo reto asignado aparecerá aquí."/></article>;
  return <article className="panel challenge-card"><div className="challenge-tag"><Icon name="target" size={16}/> {KIND_LABEL[challenge.kind] || 'Reto de la semana'}</div><span className="challenge-icon"><Icon name="shield" size={34}/></span><h2>{challenge.title}</h2><p>{challenge.description}</p><div className="challenge-meta"><span>{challenge.time}</span><span>{challenge.due}</span></div><button className="btn btn-primary btn-block" onClick={() => onResolve?.(challenge)}>Practicar reto</button></article>;
}

const LESSON_STEPS = ['Diagnóstico', 'Aprende', 'Practica', 'Oportunidad', 'Motivación', 'Acción'];
const LIKERT = [
  { value: 1, label: 'Totalmente en desacuerdo' },
  { value: 2, label: 'En desacuerdo' },
  { value: 3, label: 'Neutral' },
  { value: 4, label: 'De acuerdo' },
  { value: 5, label: 'Totalmente de acuerdo' },
];
const MIN_REFLECTION = 5;

function LessonStepper({ step }) {
  return (
    <ol className="lesson-stepper" aria-label="Pasos del módulo">
      {LESSON_STEPS.map((label, index) => (
        <li key={label} className={index < step ? 'is-done' : index === step ? 'is-current' : ''} aria-current={index === step ? 'step' : undefined}>
          <span>{index < step ? '✓' : index + 1}</span>
          {label}
        </li>
      ))}
    </ol>
  );
}

function ModulePlayer({ moduleId, onBack, onChanged, backLabel = 'Volver a mis módulos' }) {
  const [module, setModule] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [step, setStep] = useState(0);
  const [diagnostic, setDiagnostic] = useState({});
  const [answers, setAnswers] = useState({});
  const [grade, setGrade] = useState(null);
  const [reflections, setReflections] = useState({ oportunidad: '', motivacion: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [newCertificates, setNewCertificates] = useState([]);

  useEffect(() => {
    let active = true;
    api.worker.module(moduleId)
      .then((data) => {
        if (!active) return;
        setModule(data);
        setReflections({ oportunidad: data.saved_reflections?.oportunidad || '', motivacion: data.saved_reflections?.motivacion || '' });
      })
      .catch((err) => { if (active) setLoadError(err.message); });
    return () => { active = false; };
  }, [moduleId]);

  if (loadError) {
    return (
      <div className="fatal-state inside">
        <h2>No se pudo cargar el módulo</h2>
        <p>{loadError}</p>
        <button className="btn btn-secondary" onClick={onBack}>Volver</button>
      </div>
    );
  }
  if (!module) return <LoadingScreen/>;

  async function run(action, nextStep) {
    setBusy(true); setError('');
    try {
      await action();
      if (nextStep !== undefined) setStep(nextStep);
    } catch (err) {
      setError(err.message || 'No se pudo guardar. Intenta de nuevo.');
    } finally {
      setBusy(false);
    }
  }

  const diagnosticComplete = module.diagnostic.every((item) => diagnostic[item.code]);
  const capacityComplete = module.capacity_questions.every((_, index) => answers[index] !== undefined);
  const reflectionOk = (key) => reflections[key].trim().length >= MIN_REFLECTION;

  function saveDiagnostic() {
    if (!diagnosticComplete) return setError('Responde todas las afirmaciones para continuar.');
    return run(() => api.worker.saveComb(moduleId, {
      phase: 'pre',
      responses: module.diagnostic.map((item) => ({ dimension: item.dimension, code: item.code, value: Number(diagnostic[item.code]) })),
    }), 1);
  }

  function checkCapacity() {
    return run(async () => {
      const result = await api.worker.gradeCapacity(moduleId, {
        answers: module.capacity_questions.map((_, index) => ({ index, choice: Number(answers[index]) })),
      });
      setGrade(result);
      if (result.new_certificates?.length) { setNewCertificates(result.new_certificates); await onChanged?.(); }
    });
  }

  function saveReflection(key, nextStep) {
    if (!reflectionOk(key)) return setError(`Escribe al menos ${MIN_REFLECTION} caracteres para continuar.`);
    return run(() => api.worker.saveReflections(moduleId, {
      responses: [{ prompt_code: key, text: reflections[key].trim() }],
    }), nextStep);
  }

  function finishModule() {
    return run(async () => {
      const result = await api.worker.completeModule(moduleId);
      if (result?.new_certificates?.length) setNewCertificates(result.new_certificates);
      await onChanged?.();
    }, 6);
  }

  // Repetir la práctica vuelve a la microlección: así el segundo intento es repaso, no adivinar.
  function retryPractice() { setAnswers({}); setGrade(null); setError(''); setStep(1); }

  const alert = error && <div className="form-error" role="alert">{error}</div>;

  return (
    <GenericPage eyebrow={module.topic} title={module.title} description={module.behavior_objective}>
      <article className="panel lesson-panel">
        <button className="text-button" onClick={onBack}>← {backLabel}</button>

        {step < 6 && <>
          <LessonStepper step={step}/>
          <ProgressBar value={((step + 1) / LESSON_STEPS.length) * 100}/>
        </>}

        {step === 0 && (
          <section className="lesson-step">
            <span className="eyebrow">DIAGNÓSTICO INICIAL</span>
            <h2>¿Qué tan seguro te sientes hoy?</h2>
            <p className="lesson-lead">Indica qué tanto te identificas con cada afirmación. No hay respuestas buenas ni malas.</p>
            {module.diagnostic.map((item, index) => (
              <fieldset className="likert-item" key={item.code}>
                <legend><span className="likert-number">{index + 1}</span>{item.statement}</legend>
                <div className="likert-scale" role="radiogroup" aria-label={item.statement}>
                  {LIKERT.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      role="radio"
                      aria-checked={Number(diagnostic[item.code]) === option.value}
                      title={option.label}
                      className={`likert-option ${Number(diagnostic[item.code]) === option.value ? 'is-selected' : ''}`}
                      onClick={() => setDiagnostic({ ...diagnostic, [item.code]: option.value })}
                    >
                      <b>{option.value}</b>
                      <small>{option.label}</small>
                    </button>
                  ))}
                </div>
              </fieldset>
            ))}
            {alert}
            <div className="lesson-actions">
              <button className="btn btn-primary" disabled={busy} onClick={saveDiagnostic}>{busy ? 'Guardando…' : 'Continuar'}</button>
            </div>
          </section>
        )}

        {step === 1 && (
          <section className="lesson-step">
            <span className="eyebrow">MICROLECCIÓN</span>
            <h2>Aprende lo esencial</h2>
            <div className="lesson-callout"><Icon name="shield" size={20}/><p>{module.micro_lesson}</p></div>
            <div className="lesson-actions"><button className="btn btn-primary" onClick={() => setStep(2)}>Continuar</button></div>
          </section>
        )}

        {step === 2 && (
          <section className="lesson-step">
            <span className="eyebrow">PRACTICA</span>
            <h2>Pon a prueba lo aprendido</h2>
            {module.capacity_questions.map((question, qi) => (
              <fieldset className="quiz-item" key={qi}>
                <legend><span className="likert-number">{qi + 1}</span>{question.prompt}</legend>
                <div className="choice-list" role="radiogroup" aria-label={question.prompt}>
                  {question.options.map((option, oi) => (
                    <button
                      key={oi}
                      type="button"
                      role="radio"
                      aria-checked={Number(answers[qi]) === oi}
                      disabled={busy || Boolean(grade)}
                      className={`choice ${Number(answers[qi]) === oi ? 'is-selected' : ''}`}
                      onClick={() => setAnswers({ ...answers, [qi]: oi })}
                    >
                      <span className="choice-dot" aria-hidden="true"/>
                      {option}
                    </button>
                  ))}
                </div>
                {grade && <Feedback result={grade.results[qi]} correctText={question.options[grade.results[qi].correct_index]}/>}
              </fieldset>
            ))}
            {grade && <p className="lesson-score">Respondiste {grade.correct} de {grade.total} correctamente.</p>}
            {grade && grade.percent < grade.pass_percent && <div className="lesson-note"><Icon name="award" size={16}/><span>Para el certificado de {module.topic} necesitas {grade.pass_percent} % en esta práctica. Puedes continuar y repetirla cuando quieras: se guarda tu mejor resultado.</span></div>}
            {newCertificates.length > 0 && <div className="feedback-box is-correct" role="status"><strong>¡Obtuviste el certificado de {newCertificates.join(', ')}!</strong><p>Lo encuentras en «Certificados».</p></div>}
            {alert}
            <div className="lesson-actions">
              {!grade
                ? <button className="btn btn-secondary" disabled={!capacityComplete || busy} onClick={checkCapacity}>{busy ? 'Revisando…' : 'Revisar respuestas'}</button>
                : <>
                  {grade.percent < grade.pass_percent && <button className="btn btn-secondary" onClick={retryPractice}>Repasar y repetir</button>}
                  <button className="btn btn-primary" onClick={() => setStep(3)}>Continuar</button>
                </>}
            </div>
          </section>
        )}

        {(step === 3 || step === 4) && (
          <section className="lesson-step">
            <span className="eyebrow">{step === 3 ? 'OPORTUNIDAD' : 'MOTIVACIÓN'}</span>
            <h2>{step === 3 ? 'Identifica tus barreras' : 'Piensa en las consecuencias'}</h2>
            <p className="lesson-lead">{step === 3 ? module.opportunity_question : module.motivation_question}</p>
            <label className="reflection-field">
              <span className="sr-only">Tu respuesta</span>
              <textarea
                className="reflection"
                rows="5"
                maxLength={1000}
                placeholder="Escribe con tus palabras. Unas líneas bastan."
                value={reflections[step === 3 ? 'oportunidad' : 'motivacion']}
                onChange={(e) => setReflections({ ...reflections, [step === 3 ? 'oportunidad' : 'motivacion']: e.target.value })}
              />
            </label>
            <div className="textarea-meta">{reflections[step === 3 ? 'oportunidad' : 'motivacion'].length}/1000</div>
            {alert}
            <div className="lesson-actions">
              <button
                className="btn btn-primary"
                disabled={busy || !reflectionOk(step === 3 ? 'oportunidad' : 'motivacion')}
                onClick={() => saveReflection(step === 3 ? 'oportunidad' : 'motivacion', step + 1)}
              >
                {busy ? 'Guardando…' : 'Guardar y continuar'}
              </button>
            </div>
          </section>
        )}

        {step === 5 && (
          <section className="lesson-step">
            <span className="eyebrow">ACCIÓN REAL</span>
            <h2>Llévalo a tu trabajo</h2>
            <div className="lesson-callout is-action"><Icon name="check" size={20}/><p>{module.real_action}</p></div>
            <div className="lesson-note"><Icon name="clock" size={16}/><span>Te recordaremos este módulo en {module.reinforcement_days.join(', ')} días.</span></div>
            {alert}
            <div className="lesson-actions">
              <button className="btn btn-primary" disabled={busy} onClick={finishModule}>{busy ? 'Guardando…' : 'Finalizar módulo'}</button>
            </div>
          </section>
        )}

        {step === 6 && (
          <section className="lesson-step lesson-done">
            <span className="security-seal"><Icon name="check" size={30}/></span>
            <h2>Módulo completado</h2>
            <p className="lesson-lead">Tu avance y tus respuestas quedaron guardados.</p>
            {newCertificates.length > 0 && <div className="feedback-box is-correct" role="status"><strong>¡Obtuviste el certificado de {newCertificates.join(', ')}!</strong><p>Puedes descargarlo en «Certificados». Vale 12 meses.</p></div>}
            <div className="lesson-actions"><button className="btn btn-primary" onClick={onBack}>{backLabel}</button></div>
          </section>
        )}
      </article>
    </GenericPage>
  );
}

function WorkerViews({ data, view, setView, onRefresh }) {
  const [selectedModule, setSelectedModule] = useState(null);
  const [selectedChallenge, setSelectedChallenge] = useState(null);

  if (selectedModule) {
    return (
      <ModulePlayer
        moduleId={selectedModule}
        onBack={() => setSelectedModule(null)}
        onChanged={onRefresh}
        backLabel={view === 'certificados' ? 'Volver a mis certificados' : view === 'inicio' ? 'Volver al inicio' : 'Volver a mis módulos'}
      />
    );
  }

  if (selectedChallenge) {
    return (
      <ChallengePlayer
        challenge={selectedChallenge}
        onBack={() => { setSelectedChallenge(null); onRefresh?.(); }}
        onDone={() => { setSelectedChallenge(null); onRefresh?.(); }}
      />
    );
  }

  if (view === 'inicio') {
    return (
      <WorkerHome
        data={data}
        setView={setView}
        onOpen={setSelectedModule}
        onChallenge={setSelectedChallenge}
      />
    );
  }

  if (view === 'modulos') {
    return (
      <GenericPage
        eyebrow="TU RUTA DE APRENDIZAJE"
        title="Mis módulos"
        description="Completa los contenidos asignados y continúa fortaleciendo tus hábitos de seguridad."
      >
        <article className="panel">
          <ModuleList
            modules={data.modules}
            onOpen={setSelectedModule}
          />
        </article>
      </GenericPage>
    );
  }

  if (view === 'retos') {
    const challenges = data.challenges || [];
    return (
      <GenericPage
        eyebrow="PRÁCTICA"
        title="Mis retos"
        description="Escenarios para practicar cómo actuarías en tu trabajo. Puedes repetirlos las veces que quieras: tus resultados solo los ves tú."
      >
        <section className="challenge-list">
          {challenges.length === 0
            ? <article className="panel"><EmptyState title="Sin retos asignados" description="Cuando tu gestor publique un reto para ti, aparecerá aquí."/></article>
            : challenges.map((item) => (
              <article className="panel challenge-row" key={item.id}>
                <div>
                  <span className="eyebrow">{item.topic} · {KIND_LABEL[item.kind] || 'Reto'}</span>
                  <h2>{item.title}</h2>
                  <p className="muted-text">{item.due}</p>
                </div>
                <div className="challenge-row-actions">
                  {item.answered && <span className={`status ${item.is_correct ? 'status-publicado' : 'status-borrador'}`}>{item.is_correct ? 'Último intento sin errores' : 'Puedes mejorar'} · {item.tries} {item.tries === 1 ? 'intento' : 'intentos'}</span>}
                  <button className={`btn ${item.answered ? 'btn-secondary' : 'btn-primary'}`} onClick={() => setSelectedChallenge(item)}>{item.answered ? 'Practicar de nuevo' : 'Practicar'}</button>
                </div>
              </article>
            ))}
        </section>
      </GenericPage>
    );
  }

  if (view === 'progreso') {
    return (
      <GenericPage
        eyebrow="MI AVANCE"
        title="Mi progreso"
        description="Revisa cuánto has avanzado en tu ruta de aprendizaje."
      >
        <article className="panel">
          <h2>Avance general</h2>

          <h3>{data.progress}% completado</h3>

          <ProgressBar value={data.progress} />

          <div className="topic-list">
            {data.weakTopics.map((item) => (
              <div key={item.name}>
                <span className="topic-icon">
                  <Icon name={item.icon} />
                </span>

                <div>
                  <strong>{item.name}</strong>
                  <small>{item.errors} errores recientes</small>
                </div>

                <div className="topic-score">
                  <b>{item.score}%</b>
                  <ProgressBar value={item.score} />
                </div>
              </div>
            ))}
          </div>
        </article>
      </GenericPage>
    );
  }

  if (view === 'certificados') {
    return (
      <CertificatesPage onOpenModule={setSelectedModule} onChanged={onRefresh}/>
    );
  }

  return (
    <WorkerHome
      data={data}
      setView={setView}
      onOpen={setSelectedModule}
      onChallenge={setSelectedChallenge}
    />
  );
}

const MANAGER_VIEWS = ['inicio', 'contenido', 'retos', 'asignaciones', 'estadisticas'];
const dateLabel = (value) => (value ? new Date(value).toLocaleDateString('es-PE', { dateStyle: 'medium' }) : '—');

async function loadManagerPanel(view) {
  const [dashboard, catalog] = await Promise.all([api.manager.dashboard(), api.manager.topics()]);
  const panel = { ...dashboard, topics: catalog.topics };
  if (view === 'asignaciones') {
    const [assignable, assignments] = await Promise.all([api.manager.assignable(), api.manager.assignments()]);
    return { ...panel, assignable, assignments };
  }
  if (view === 'estadisticas') return { ...panel, stats: await api.manager.stats() };
  return panel;
}

function ContentTable({ rows, onEdit, empty = 'Aún no hay contenido con estos filtros.' }) {
  if (!rows.length) return <EmptyState title="Nada por aquí" description={empty}/>;
  return <div className="table-wrap"><table><thead><tr><th>Contenido</th><th>Tema</th><th>Tipo</th><th>Estado</th><th>Público</th><th>Aprobación</th><th>Actualizado</th><th><span className="sr-only">Acción</span></th></tr></thead><tbody>{rows.map((row) => <tr key={`${row.kind}-${row.id}`}><td><strong>{row.title}</strong></td><td>{row.topic}</td><td>{row.type}</td><td><span className={`status status-${row.status.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')}`}>{row.status}</span></td><td>{row.users ?? '—'}</td><td>{row.success == null ? '—' : `${row.success}%`}</td><td>{dateLabel(row.updated)}</td><td>{row.editable ? <button type="button" className="text-button" onClick={() => onEdit?.(row)}>Editar</button> : <span className="muted-text">Base</span>}</td></tr>)}</tbody></table></div>;
}

function TopicErrors({ items }) {
  if (!items.length) return <EmptyState title="Sin datos todavía" description="Aparecerán cuando tus trabajadores respondan retos."/>;
  return <div className="error-bars">{items.map((item) => <div key={item.topic}><div><span>{item.topic}</span><b>{item.errorRate ?? 0}% error</b></div><ProgressBar value={item.errorRate ?? 0} danger/></div>)}</div>;
}

function ManagerHome({ data, onNew, onEdit }) {
  const recent = [...data.content, ...data.challenges].sort((a, b) => (b.updated || '').localeCompare(a.updated || '')).slice(0, 8);
  const worst = data.topicErrors[0];
  return <>
    <section className="page-heading"><div><span className="eyebrow">PANEL DE CONTENIDO</span><h1>Contenido útil, claro y <span>medible.</span></h1><p>Crea experiencias breves, asígnalas a tu equipo y revisa qué está funcionando.</p></div><div className="hero-actions"><button className="btn btn-primary" onClick={() => onNew('module')}>Crear módulo</button><button className="btn btn-secondary" onClick={() => onNew('challenge')}>Crear reto</button></div></section>
    <section className="stats-grid">{data.stats.map((item) => <StatCard key={item.label} item={item}/>)}</section>
    <section className="two-col-grid manager-grid">
      <article className="panel"><div className="panel-head"><div><span className="eyebrow">BIBLIOTECA</span><h2>Contenido reciente</h2></div></div><ContentTable rows={recent} onEdit={onEdit}/></article>
      <article className="panel"><span className="eyebrow">ANÁLISIS</span><h2>Temas con más errores</h2><TopicErrors items={data.topicErrors}/>{worst && <div className="insight-box"><Icon name="shield" size={18}/><p><strong>{worst.topic} necesita refuerzo.</strong> Considera una segunda actividad práctica para las áreas con mayor tasa de error.</p></div>}</article>
    </section>
  </>;
}

function ManagerLibrary({ kind, data, onNew, onEdit }) {
  const [query, setQuery] = useState('');
  const [topic, setTopic] = useState('');
  const [status, setStatus] = useState('');
  const isModule = kind === 'module';
  const term = query.trim().toLowerCase();
  const rows = (isModule ? data.content : data.challenges).filter((row) =>
    (!topic || row.topic === topic) && (!status || row.status === status) && row.title.toLowerCase().includes(term));
  return <GenericPage eyebrow="BIBLIOTECA" title={isModule ? 'Contenido' : 'Retos'} description={isModule ? 'Crea y edita módulos en lenguaje sencillo, organizados por tema.' : 'Escenarios prácticos basados en situaciones reales del trabajo.'}>
    <article className="panel">
      <div className="manager-toolbar">
        <input className="table-search" type="search" aria-label="Buscar por título" placeholder="Buscar por título…" value={query} onChange={(e) => setQuery(e.target.value)}/>
        <select aria-label="Filtrar por tema" value={topic} onChange={(e) => setTopic(e.target.value)}><option value="">Todos los temas</option>{data.topics.map((item) => <option key={item}>{item}</option>)}</select>
        <select aria-label="Filtrar por estado" value={status} onChange={(e) => setStatus(e.target.value)}><option value="">Todos los estados</option><option>Publicado</option><option>Borrador</option><option>Archivado</option></select>
        <button className="btn btn-primary" onClick={() => onNew(kind)}>{isModule ? 'Nuevo módulo' : 'Nuevo reto'}</button>
      </div>
      <ContentTable rows={rows} onEdit={onEdit} empty={isModule ? 'Crea tu primer módulo o ajusta los filtros.' : 'Crea tu primer reto o ajusta los filtros.'}/>
    </article>
  </GenericPage>;
}

function ManagerAssignments({ data, onChanged }) {
  const items = data.assignable || [];
  const [form, setForm] = useState({ item: items[0] ? `${items[0].item_type}:${items[0].item_id}` : '', target: 'company', areaId: '', userId: '', due: '' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const set = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError(''); setNotice('');
    const [itemType, itemId] = form.item.split(':');
    try {
      await api.manager.createAssignment({
        item_type: itemType, item_id: Number(itemId), target: form.target,
        area_id: form.target === 'area' ? Number(form.areaId) : null,
        user_id: form.target === 'user' ? Number(form.userId) : null,
        due_at: form.due ? new Date(form.due).toISOString() : null,
      });
      setNotice('Asignación guardada.');
      set('due', '');
      onChanged();
    } catch (err) { setError(err.message || 'No se pudo guardar la asignación.'); }
    finally { setBusy(false); }
  }

  async function remove(id) {
    setError(''); setNotice('');
    try { await api.manager.deleteAssignment(id); onChanged(); }
    catch (err) { setError(err.message || 'No se pudo quitar la asignación.'); }
  }

  return <GenericPage eyebrow="PLANIFICACIÓN" title="Asignaciones" description="Elige a quién llega cada módulo o reto y cuándo vence. Sin asignación, el contenido es para toda la empresa.">
    {items.length === 0
      ? <article className="panel"><EmptyState title="Nada publicado todavía" description="Publica un módulo o reto para poder asignarlo."/></article>
      : <article className="panel">
        <form className="modal-form assignment-form" onSubmit={submit}>
          <div className="form-grid">
            <label>Contenido<select value={form.item} onChange={(e) => set('item', e.target.value)}>{items.map((i) => <option key={`${i.item_type}:${i.item_id}`} value={`${i.item_type}:${i.item_id}`}>{i.item_type === 'module' ? 'Módulo' : 'Reto'} · {i.title}</option>)}</select></label>
            <label>Para<select value={form.target} onChange={(e) => set('target', e.target.value)}><option value="company">Toda la empresa</option><option value="area">Un área</option><option value="user">Un trabajador</option></select></label>
          </div>
          {form.target === 'area' && <label>Área<select value={form.areaId} onChange={(e) => set('areaId', e.target.value)} required><option value="">Elige un área</option>{data.areas.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}</select></label>}
          {form.target === 'user' && <label>Trabajador<select value={form.userId} onChange={(e) => set('userId', e.target.value)} required><option value="">Elige un trabajador</option>{data.workers.map((w) => <option key={w.id} value={w.id}>{w.name} · {w.area}</option>)}</select></label>}
          <label>Fecha límite (opcional)<input type="datetime-local" value={form.due} onChange={(e) => set('due', e.target.value)}/></label>
          {error && <div className="form-error" role="alert">{error}</div>}
          {notice && <p className="form-note">{notice}</p>}
          <div className="modal-actions"><button type="submit" className="btn btn-primary" disabled={busy}>{busy ? 'Guardando…' : 'Asignar'}</button></div>
        </form>
      </article>}
    <article className="panel">
      <div className="panel-head"><div><span className="eyebrow">ASIGNADOS</span><h2>Asignaciones activas</h2></div></div>
      {(data.assignments || []).length === 0
        ? <EmptyState title="Sin asignaciones" description="Lo que asignes aparecerá aquí con su fecha límite."/>
        : <div className="table-wrap"><table><thead><tr><th>Contenido</th><th>Tipo</th><th>Para</th><th>Fecha límite</th><th><span className="sr-only">Acción</span></th></tr></thead><tbody>{data.assignments.map((a) => <tr key={a.id}><td><strong>{a.title}</strong></td><td>{a.item_type === 'module' ? 'Módulo' : 'Reto'}</td><td>{a.target}</td><td>{a.due}</td><td><button type="button" className="text-button danger-text" onClick={() => remove(a.id)}>Quitar</button></td></tr>)}</tbody></table></div>}
    </article>
  </GenericPage>;
}

function WorkerBreakdown({ kind, workers }) {
  if (!workers.length) return <p className="muted-text">Nadie está en el público de este contenido todavía.</p>;
  return <table className="inner-table"><thead><tr><th>Trabajador</th><th>Área</th><th>Estado</th></tr></thead><tbody>{workers.map((w) => <tr key={w.user_id}><td>{w.name}</td><td>{w.area}</td><td>{kind === 'module' ? (w.completed ? `Terminó el ${dateLabel(w.completed_at)}` : 'Pendiente') : (!w.answered ? 'Sin practicar' : `Practicó · ${w.tries} ${w.tries === 1 ? 'intento' : 'intentos'}`)}</td></tr>)}</tbody></table>;
}

function StatTable({ kind, rows, open, onToggle }) {
  if (!rows.length) return <EmptyState title="Sin contenido propio" description="Crea un módulo o reto para ver aquí su desempeño."/>;
  return <div className="table-wrap"><table><thead><tr><th>Título</th><th>Tema</th><th>Público</th><th>{kind === 'module' ? 'Terminaron' : 'Practicaron'}</th><th>{kind === 'module' ? '% completado' : '% acierto (1.er intento)'}</th><th><span className="sr-only">Detalle</span></th></tr></thead><tbody>{rows.map((row) => {
    const key = `${kind}-${row.id}`;
    const answered = kind === 'module' ? row.completed : row.attempts;
    const share = kind === 'module' ? row.completion_rate : row.success_rate;
    return <Fragment key={key}><tr><td><strong>{row.title}</strong></td><td>{row.topic}</td><td>{row.audience}</td><td>{answered}</td><td>{share == null ? '—' : `${share}%`}</td><td><button type="button" className="text-button" aria-expanded={open === key} onClick={() => onToggle(key)}>{open === key ? 'Ocultar' : 'Ver trabajadores'}</button></td></tr>{open === key && <tr className="stat-detail"><td colSpan={6}><WorkerBreakdown kind={kind} workers={row.workers}/></td></tr>}</Fragment>;
  })}</tbody></table></div>;
}

function ManagerStats({ data }) {
  const [open, setOpen] = useState(null);
  const modules = data.stats?.modules || [];
  const challenges = data.stats?.challenges || [];
  const toggle = (key) => setOpen((current) => (current === key ? null : key));
  const completions = modules.reduce((sum, m) => sum + m.completed, 0);
  const possible = modules.reduce((sum, m) => sum + m.audience, 0);
  const shown = challenges.filter((c) => c.correct != null);
  const attempts = shown.reduce((sum, c) => sum + c.attempts, 0);
  const correct = shown.reduce((sum, c) => sum + c.correct, 0);
  const minGroup = data.stats?.min_group || 3;
  const certificates = data.stats?.certificates || [];
  return <GenericPage eyebrow="ANALÍTICA" title="Estadísticas" description="Desempeño de lo que creaste, por contenido y por trabajador. Sirve para decidir qué reforzar.">
    <section className="two-col-grid manager-grid">
      <article className="panel"><span className="eyebrow">ANÁLISIS</span><h2>Temas con más errores</h2><TopicErrors items={data.stats?.topic_errors || []}/></article>
      <article className="panel"><span className="eyebrow">RESUMEN</span><h2>Tu contenido</h2>
        <p>Módulos creados: <strong>{modules.length}</strong> · Retos creados: <strong>{challenges.length}</strong></p>
        <p>Módulos terminados: <strong>{completions}</strong> de {possible} posibles</p>
        <p>Aciertos en retos (primer intento): <strong>{attempts ? `${Math.round((correct * 100) / attempts)}%` : '—'}</strong>{attempts ? ` (${correct} de ${attempts})` : ''}</p>
        <p className="form-note">Los retos entrenan, no califican: no verás si cada persona acertó. Los porcentajes de aciertos aparecen solo cuando practican {minGroup} o más personas.</p>
      </article>
    </section>
    <article className="panel"><div className="panel-head"><div><span className="eyebrow">CERTIFICADOS</span><h2>Certificados vigentes por tema</h2></div></div>
      {certificates.length === 0
        ? <EmptyState title="Aún no hay certificados" description="Aparecerán cuando alguien complete todos los módulos de un tema con 80 % o más."/>
        : <div className="table-wrap"><table><thead><tr><th>Tema</th><th>Vigentes</th><th>Por vencer</th><th>Vencidos</th><th>Trabajadores</th></tr></thead><tbody>{certificates.map((c) => <tr key={c.topic}><td><strong>{c.topic}</strong></td><td>{c.active + c.expiring}</td><td>{c.expiring}</td><td>{c.expired}</td><td>{c.workers}</td></tr>)}</tbody></table></div>}
    </article>
    <article className="panel"><div className="panel-head"><div><span className="eyebrow">MÓDULOS</span><h2>Terminaciones por contenido</h2></div></div><StatTable kind="module" rows={modules} open={open} onToggle={toggle}/></article>
    <article className="panel"><div className="panel-head"><div><span className="eyebrow">RETOS</span><h2>Práctica por reto</h2></div></div><StatTable kind="challenge" rows={challenges} open={open} onToggle={toggle}/></article>
  </GenericPage>;
}

function ManagerViews({ data, view, onNew, onEdit, onChanged }) {
  if (view === 'inicio') return <ManagerHome data={data} onNew={onNew} onEdit={onEdit}/>;
  if (view === 'contenido') return <ManagerLibrary kind="module" data={data} onNew={onNew} onEdit={onEdit}/>;
  if (view === 'retos') return <ManagerLibrary kind="challenge" data={data} onNew={onNew} onEdit={onEdit}/>;
  if (view === 'asignaciones') return <ManagerAssignments data={data} onChanged={onChanged}/>;
  return <ManagerStats data={data}/>;
}

const ADMIN_ROLES = { Trabajador: 'worker', Gestor: 'manager', 'Gestor de contenido': 'manager', Administrador: 'admin' };
const roleValue = (role) => ADMIN_ROLES[role] || role;
const critical2FA = (users, role) => {
  const members = users.filter((u) => roleValue(u.role) === role && u.status === 'Activo');
  return members.length ? Math.round(members.filter((u) => u.twoFactor).length * 100 / members.length) : null;
};
const auditTime = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('es-PE', { dateStyle: 'medium', timeStyle: 'short' });
};
const AUDIT_LABELS = {
  LOGIN_SUCCESS: 'Inicio de sesión', LOGIN_SUCCESS_MFA: 'Inicio de sesión con 2FA',
  LOGIN_FAILED: 'Inicio de sesión fallido', MFA_FAILED: 'Verificación 2FA fallida',
  USER_CREATED: 'Usuario creado', USER_UPDATED: 'Usuario actualizado',
  USER_DELETED: 'Usuario eliminado', ROLE_CHANGED: 'Rol actualizado', AREA_CREATED: 'Área creada',
};

function UserTable({ rows, search, setSearch, onEdit, onDelete, currentUserId, areaFilter = '' }) {
  const filtered = rows.filter((u) => (!areaFilter || u.area === areaFilter) && `${u.name} ${u.email} ${u.area} ${u.role} ${u.status}`.toLowerCase().includes(search.toLowerCase()));
  return <article className="panel"><div className="panel-head"><div><span className="eyebrow">GESTIÓN DE USUARIOS</span><h2>Usuarios de la organización</h2></div><input className="table-search" type="search" aria-label="Buscar usuario" placeholder="Buscar usuario…" value={search} onChange={(e) => setSearch(e.target.value)}/></div><div className="table-wrap"><table><thead><tr><th>Usuario</th><th>Área</th><th>Rol</th><th>Estado</th><th>2FA</th>{onEdit && <th>Acciones</th>}</tr></thead><tbody>{filtered.map((u) => <tr key={u.id}><td><div className="table-user"><span>{u.name?.[0] || '?'}</span><div><strong>{u.name}</strong><small>{u.email}</small></div></div></td><td>{u.area}</td><td>{u.role}</td><td><span className={`status ${u.status === 'Activo' ? 'status-publicado' : 'status-borrador'}`}>{u.status}</span></td><td>{u.twoFactor ? 'Activo' : '—'}</td>{onEdit && <td><div className="table-actions"><button type="button" className="text-button" onClick={() => onEdit(u)} aria-label={`Editar ${u.name}`}>Editar</button>{Number(u.id) !== Number(currentUserId) && <button type="button" className="text-button danger-text" onClick={() => onDelete(u)} aria-label={`Eliminar ${u.name}`}>Eliminar</button>}</div></td>}</tr>)}</tbody></table></div>{filtered.length === 0 && <p className="table-empty">No hay usuarios que coincidan con la búsqueda.</p>}</article>;
}

function AdminHome({ data, onCreateUser, onExport, search, setSearch, onEditUser, onDeleteUser, currentUserId }) {
  const admin2FA = critical2FA(data.users, 'admin');
  const manager2FA = critical2FA(data.users, 'manager');
  const criticalUsers = data.users.filter((u) => ['admin', 'manager'].includes(roleValue(u.role)) && u.status === 'Activo');
  const criticalRate = criticalUsers.length ? `${Math.round(criticalUsers.filter((u) => u.twoFactor).length * 100 / criticalUsers.length)}%` : '—';
  return <>
    <section className="admin-hero" aria-labelledby="admin-hero-title">
      <ParticleNetwork />
      <div className="admin-hero-copy">
        <span className="eyebrow">CENTRO DE CONTROL · INKASEC</span>
        <h1 id="admin-hero-title">La seguridad de tu equipo, <span>en tus manos.</span></h1>
        <p>Supervisa la formación, organiza accesos y detecta lo que necesita atención.</p>
        <div className="hero-actions"><button className="btn btn-primary" onClick={onCreateUser}>Crear usuario</button><button className="btn btn-secondary" onClick={onExport}>Exportar reporte por área</button></div>
      </div>
      <div className="admin-hero-aside" aria-hidden="true"><span>VISTA GENERAL</span><strong>{data.users.length}</strong><small>personas en tu organización</small></div>
    </section>
    <section className="stats-grid">{data.stats.filter((item) => item.label !== '2FA en roles críticos').map((item) => <StatCard key={item.label} item={item}/>)}<StatCard item={{ label: '2FA en roles críticos', value: criticalRate, helper: 'Administradores y gestores activos', icon: 'lock', tone: 'blue' }}/></section>
    <section className="two-col-grid admin-grid"><UserTable rows={data.users} search={search} setSearch={setSearch} onEdit={onEditUser} onDelete={onDeleteUser} currentUserId={currentUserId}/><article className="panel security-overview"><span className="security-seal"><Icon name="lock" size={23}/></span><span className="eyebrow">SEGURIDAD DE ACCESO</span><h2>Verificación en dos pasos</h2><div className="security-check"><span>Administradores activos</span><b>{admin2FA == null ? 'Sin usuarios' : `${admin2FA}%`}</b></div><ProgressBar value={admin2FA || 0}/><div className="security-check"><span>Gestores activos</span><b>{manager2FA == null ? 'Sin usuarios' : `${manager2FA}%`}</b></div><ProgressBar value={manager2FA || 0}/><div className="security-note"><Icon name="shield" size={17}/><p>Estos porcentajes se calculan con las cuentas visibles. El bloqueo de acceso y los permisos se aplican en la API.</p></div></article></section>
    <section className="two-col-grid lower"><AuditPanel rows={data.audit}/><AreasPanel rows={data.areas}/></section>
  </>;
}

function AuditPanel({ rows, search, onSearch }) {
  return <article className="panel"><div className="panel-head"><div><span className="eyebrow">TRAZABILIDAD</span><h2>{onSearch ? 'Historial de actividades' : 'Últimos eventos'}</h2></div>{onSearch && <input className="table-search" type="search" aria-label="Buscar evento" placeholder="Buscar acción, usuario o IP…" value={search} onChange={(e) => onSearch(e.target.value)}/>}</div><div className="audit-list">{rows.map((item) => <div key={item.id}><span className={`audit-mark is-${item.type}`}><Icon name={item.type === 'danger' ? 'lock' : item.type === 'role' ? 'users' : 'shield'} size={16}/></span><div><strong>{AUDIT_LABELS[item.action] || item.action}</strong><p>{item.actor ? `${item.actor} · IP ${item.ip || 'desconocida'}` : item.detail}</p><small>{auditTime(item.time)}</small></div></div>)}</div>{rows.length === 0 && <p className="table-empty">No se encontraron eventos.</p>}</article>;
}

function AreasPanel({ rows, users = [] }) {
  return <article className="panel"><div className="panel-head"><div><span className="eyebrow">ÁREAS</span><h2>Usuarios por área</h2></div></div><div className="area-list">{rows.map((area) => <div key={area.id || area.name}><div><strong>{area.name}</strong><small>{area.users} usuarios · {area.managers ?? users.filter((u) => u.area === area.name && roleValue(u.role) === 'manager').length} gestores</small><b>{area.users}</b></div></div>)}</div>{rows.length === 0 && <p className="table-empty">Todavía no hay áreas registradas.</p>}</article>;
}

function AdminViews({ data, view, onCreateUser, onCreateArea, onExport, onEditUser, onDeleteUser, currentUserId, notice, auditPage, setAuditPage, auditQuery, setAuditQuery }) {
  const [search, setSearch] = useState('');
  const [selectedArea, setSelectedArea] = useState('');
  const feedback = notice && <div className={`admin-notice ${notice.type === 'error' ? 'is-error' : ''}`} role="status">{notice.message}</div>;
  if (view === 'inicio') return <>{feedback}<AdminHome data={data} onCreateUser={onCreateUser} onExport={onExport} search={search} setSearch={setSearch} onEditUser={onEditUser} onDeleteUser={onDeleteUser} currentUserId={currentUserId}/></>;
  if (view === 'usuarios') return <GenericPage eyebrow="ADMINISTRACIÓN" title="Usuarios" description="Crea cuentas, cambia roles y estados, o elimina usuarios.">{feedback}<div className="page-toolbar"><button className="btn btn-primary" onClick={onCreateUser}>Crear usuario</button></div><UserTable rows={data.users} search={search} setSearch={setSearch} onEdit={onEditUser} onDelete={onDeleteUser} currentUserId={currentUserId}/></GenericPage>;
  if (view === 'areas') return <GenericPage eyebrow="ORGANIZACIÓN" title="Áreas y roles" description="Crea áreas y consulta la distribución de usuarios y roles.">{feedback}<div className="page-toolbar"><button className="btn btn-primary" onClick={onCreateArea}>Crear área</button></div><AreasPanel rows={data.areas} users={data.users}/><div className="page-toolbar admin-area-toolbar"><label>Filtrar área <select value={selectedArea} onChange={(e) => setSelectedArea(e.target.value)}><option value="">Todas las áreas</option>{data.areas.map((area) => <option key={area.id} value={area.name}>{area.name}</option>)}</select></label></div><UserTable rows={data.users} search={search} setSearch={setSearch} areaFilter={selectedArea} onEdit={onEditUser} onDelete={onDeleteUser} currentUserId={currentUserId}/><p className="admin-hint">Los roles se cambian desde «Editar». La API aún no permite cambiar el área de una cuenta existente.</p></GenericPage>;
  if (view === 'auditoria') return <GenericPage eyebrow="TRAZABILIDAD" title="Auditoría" description="Consulta acciones críticas con fecha, actor e IP.">{feedback}<AuditPanel rows={data.audit.items} search={auditQuery} onSearch={(value) => { setAuditQuery(value); setAuditPage(0); }}/><div className="admin-pagination"><span>{data.audit.total === 0 ? 'Sin resultados' : `${data.audit.offset + 1}–${Math.min(data.audit.offset + data.audit.items.length, data.audit.total)} de ${data.audit.total}`}</span><div><button className="btn btn-secondary" disabled={auditPage === 0} onClick={() => setAuditPage(auditPage - 1)}>Anterior</button><button className="btn btn-secondary" disabled={data.audit.offset + data.audit.items.length >= data.audit.total} onClick={() => setAuditPage(auditPage + 1)}>Siguiente</button></div></div></GenericPage>;
  return <GenericPage eyebrow="INDICADORES" title="Reportes" description="Consulta indicadores registrados y exporta un archivo CSV.">{feedback}<section className="stats-grid"><StatCard item={{label:'Usuarios activos',value:data.report.active_users,helper:`De ${data.report.total_users} registrados`,icon:'users',tone:'blue'}}/><StatCard item={{label:'Avance registrado',value:data.report.average_progress == null ? '—' : `${data.report.average_progress}%`,helper:'Promedio de registros existentes',icon:'chart',tone:'green'}}/><StatCard item={{label:'Módulos completados',value:data.report.completed_modules,helper:'Registros con 100% de avance',icon:'book',tone:'blue'}}/><StatCard item={{label:'Áreas',value:data.report.areas.length,helper:'En esta empresa',icon:'layers',tone:'amber'}}/></section><article className="panel report-card"><div><span className="report-icon"><Icon name="report" size={28}/></span><h2>Reporte por área</h2><p>Incluye usuarios, usuarios activos, avance promedio registrado y módulos completados.</p></div><button className="btn btn-primary" onClick={onExport}>Exportar CSV</button></article><article className="panel admin-report-areas"><div className="panel-head"><div><span className="eyebrow">DESGLOSE</span><h2>Indicadores por área</h2></div></div><div className="table-wrap"><table><thead><tr><th>Área</th><th>Usuarios</th><th>Activos</th><th>Avance registrado</th><th>Módulos completados</th></tr></thead><tbody>{data.report.areas.map((area) => <tr key={area.id}><td><strong>{area.name}</strong></td><td>{area.users}</td><td>{area.active_users}</td><td>{area.average_progress == null ? 'Sin registros' : `${area.average_progress}%`}</td><td>{area.completed_modules}</td></tr>)}</tbody></table></div></article><p className="admin-hint">El avance promedio considera únicamente módulos con progreso registrado; no representa el cumplimiento de todas las asignaciones.</p></GenericPage>;
}

function Modal({ title, onClose, children }) {
  useEffect(() => { const onKey = (e) => e.key === 'Escape' && onClose(); window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey); }, [onClose]);
  return <div className="modal-backdrop" role="presentation" onMouseDown={(e) => e.target === e.currentTarget && onClose()}><div className="modal" role="dialog" aria-modal="true" aria-label={title}><div className="modal-head"><div><span className="eyebrow">INKASEC</span><h2>{title}</h2></div><button type="button" className="round-button" onClick={onClose}>×</button></div>{children}</div></div>;
}

const blankQuestion = () => ({ prompt: '', options: ['', ''], correct: 0, feedback: '' });
const DEFAULT_OPPORTUNITY = '¿Qué te dificulta aplicar esto en tu trabajo?';
const DEFAULT_MOTIVATION = '¿Por qué te importa este tema para tu trabajo?';

function ModuleEditor({ initial, topics, onDone, onClose }) {
  const [form, setForm] = useState(() => initial
    ? { ...initial, capacity_questions: initial.capacity_questions.length ? initial.capacity_questions : [blankQuestion()] }
    : { title: '', topic: topics[0] || '', objective: '', micro_lesson: '', capacity_questions: [blankQuestion()], opportunity_question: DEFAULT_OPPORTUNITY, motivation_question: DEFAULT_MOTIVATION, real_action: '', status: 'draft' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const topicOptions = form.topic && !topics.includes(form.topic) ? [form.topic, ...topics] : topics;
  const set = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));
  const setQuestion = (index, patch) => setForm((prev) => ({ ...prev, capacity_questions: prev.capacity_questions.map((q, i) => (i === index ? { ...q, ...patch } : q)) }));
  function removeOption(qIndex, oIndex) {
    setForm((prev) => ({ ...prev, capacity_questions: prev.capacity_questions.map((q, i) => {
      if (i !== qIndex) return q;
      const correct = q.correct === oIndex ? 0 : q.correct > oIndex ? q.correct - 1 : q.correct;
      return { ...q, options: q.options.filter((_, j) => j !== oIndex), correct };
    }) }));
  }

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError('');
    const payload = {
      title: form.title.trim(), topic: form.topic, objective: form.objective.trim(), micro_lesson: form.micro_lesson.trim(),
      capacity_questions: form.capacity_questions.map((q) => ({ prompt: q.prompt.trim(), options: q.options.map((o) => o.trim()), correct: q.correct, feedback: q.feedback.trim() })),
      opportunity_question: form.opportunity_question.trim(), motivation_question: form.motivation_question.trim(),
      real_action: form.real_action.trim(), status: form.status,
    };
    try {
      if (initial) await api.manager.updateModule(initial.id, payload);
      else await api.manager.createModule(payload);
      onDone();
    } catch (err) { setError(err.message || 'No se pudo guardar el módulo.'); }
    finally { setBusy(false); }
  }

  return <form className="modal-form manager-editor" onSubmit={submit}>
    <label>Título<input value={form.title} maxLength={180} required onChange={(e) => set('title', e.target.value)}/></label>
    <div className="form-grid">
      <label>Tema<select value={form.topic} onChange={(e) => set('topic', e.target.value)}>{topicOptions.map((t) => <option key={t}>{t}</option>)}</select></label>
      <label>Estado<select value={form.status} onChange={(e) => set('status', e.target.value)}>{STATUS_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}</select></label>
    </div>
    <label>Conducta que quieres lograr<textarea rows={2} maxLength={400} required value={form.objective} onChange={(e) => set('objective', e.target.value)}/></label>
    <label>Micro-lección en lenguaje sencillo<textarea rows={4} maxLength={1200} required value={form.micro_lesson} onChange={(e) => set('micro_lesson', e.target.value)}/></label>
    <h3 className="editor-heading">Preguntas de capacidad (1 a 5)</h3>
    {form.capacity_questions.map((q, index) => <fieldset className="question-card" key={index}>
      <legend>Pregunta {index + 1}</legend>
      <label>Enunciado<input value={q.prompt} maxLength={300} required onChange={(e) => setQuestion(index, { prompt: e.target.value })}/></label>
      <OptionsEditor name={`correct-${index}`} options={q.options} correct={q.correct}
        onText={(o, value) => setQuestion(index, { options: q.options.map((x, j) => (j === o ? value : x)) })}
        onCorrect={(c) => setQuestion(index, { correct: c })}
        onAdd={() => setQuestion(index, { options: [...q.options, ''] })}
        onRemove={(o) => removeOption(index, o)}/>
      <label>Retroalimentación al responder<input value={q.feedback} maxLength={300} onChange={(e) => setQuestion(index, { feedback: e.target.value })}/></label>
      {form.capacity_questions.length > 1 && <button type="button" className="text-button danger-text" onClick={() => set('capacity_questions', form.capacity_questions.filter((_, i) => i !== index))}>Quitar pregunta</button>}
    </fieldset>)}
    {form.capacity_questions.length < 5 && <button type="button" className="btn btn-secondary" onClick={() => set('capacity_questions', [...form.capacity_questions, blankQuestion()])}>Agregar pregunta</button>}
    <label>Pregunta de oportunidad<input value={form.opportunity_question} maxLength={300} required onChange={(e) => set('opportunity_question', e.target.value)}/></label>
    <label>Pregunta de motivación<input value={form.motivation_question} maxLength={300} required onChange={(e) => set('motivation_question', e.target.value)}/></label>
    <label>Acción real que debe practicar<textarea rows={2} maxLength={500} required value={form.real_action} onChange={(e) => set('real_action', e.target.value)}/></label>
    {error && <div className="form-error" role="alert">{error}</div>}
    <div className="modal-actions"><button type="button" className="btn btn-secondary" onClick={onClose}>Cancelar</button><button type="submit" className="btn btn-primary" disabled={busy}>{busy ? 'Guardando…' : 'Guardar módulo'}</button></div>
  </form>;
}

function ManagerEditorModal({ kind, id, topics, onClose, onSaved }) {
  const [initial, setInitial] = useState(null);
  const [loadError, setLoadError] = useState('');
  useEffect(() => {
    if (!id) return undefined;
    let active = true;
    const request = kind === 'module' ? api.manager.getModule(id) : api.manager.getChallenge(id);
    request.then((item) => { if (active) setInitial(item); }).catch((err) => { if (active) setLoadError(err.message || 'No se pudo abrir el contenido.'); });
    return () => { active = false; };
  }, [kind, id]);
  const title = `${id ? 'Editar' : 'Nuevo'} ${kind === 'module' ? 'módulo' : 'reto'}`;
  const done = () => { onSaved(); onClose(); };
  let body;
  if (loadError) body = <p className="form-error" role="alert">{loadError}</p>;
  else if (id && !initial) body = <p className="muted-text">Cargando…</p>;
  else if (kind === 'module') body = <ModuleEditor initial={initial} topics={topics} onDone={done} onClose={onClose}/>;
  else body = <ChallengeEditor initial={initial} topics={topics} onDone={done} onClose={onClose}/>;
  return <Modal title={title} onClose={onClose}>{body}</Modal>;
}

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error) {
    console.error('Error al mostrar la sección', error);
  }

  render() {
    if (this.state.failed) {
      return <div className="fatal-state inside"><h2>No pudimos mostrar esta sección</h2><p>Recarga la página. Si vuelve a pasar, avisa al administrador.</p><button className="btn btn-secondary" onClick={() => window.location.reload()}>Recargar</button></div>;
    }
    return this.props.children;
  }
}

function AdminCreateUserModal({ onClose, onCreated, areas = [] }) {
  const [form, setForm] = useState({ name: '', email: '', area: areas[0]?.name || '', role: 'worker' }); const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const [created, setCreated] = useState(null);
  async function submit(e) {
    e.preventDefault(); setBusy(true); setError('');
    try {
      const { temporary_password, ...user } = await api.admin.createUser({ ...form, name: form.name.trim(), email: form.email.trim(), area: form.area.trim() });
      await onCreated(user);
      setCreated({ email: user.email, temporary_password });
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  if (created) return <Modal title="Usuario creado" onClose={onClose}><div className="created-user-credentials"><p>Guarda estos datos ahora y entrégalos al usuario por un canal seguro. Se muestran una sola vez.</p><div><strong>Correo</strong><code>{created.email}</code></div><div><strong>Contraseña inicial</strong><code>{created.temporary_password}</code></div><p className="form-note">Gestores y administradores recibirán un código en su correo cada vez que inicien sesión.</p><div className="modal-actions"><button type="button" className="btn btn-primary" onClick={onClose}>Ya guardé los datos</button></div></div></Modal>;
  return <Modal title="Crear usuario" onClose={onClose}><form className="modal-form" onSubmit={submit}><label>Nombre completo<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required maxLength={120}/></label><label>Correo corporativo<input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required/></label><div className="form-grid"><label>Área<select value={form.area} onChange={(e) => setForm({ ...form, area: e.target.value })} required><option value="" disabled>Selecciona un área</option>{areas.map((area) => <option key={area.id || area.name} value={area.name}>{area.name}</option>)}</select></label><label>Rol<select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}><option value="worker">Trabajador</option><option value="manager">Gestor</option><option value="admin">Administrador</option></select></label></div><p className="form-note">Las áreas se crean en «Áreas y roles». Gestores y administradores iniciarán sesión con un código que llega a su correo.</p>{error && <div className="form-error" role="alert">{error}</div>}<div className="modal-actions"><button type="button" className="btn btn-secondary" onClick={onClose}>Cancelar</button><button className="btn btn-primary" disabled={busy || !form.area}>{busy ? 'Creando…' : 'Crear usuario'}</button></div></form></Modal>;
}

function AdminCreateAreaModal({ onClose, onCreated }) {
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    try { await api.admin.createArea({ name: name.trim() }); await onCreated(); onClose(); }
    catch (err) { setError(err.message || 'No se pudo crear el área.'); }
    finally { setBusy(false); }
  }
  return <Modal title="Crear área" onClose={onClose}><form className="modal-form" onSubmit={submit}><label>Nombre del área<input autoFocus value={name} onChange={(event) => setName(event.target.value)} minLength={2} maxLength={100} required placeholder="Por ejemplo: Finanzas"/></label><p className="admin-hint">El área quedará disponible para asignarla al crear usuarios.</p>{error && <div className="form-error" role="alert">{error}</div>}<div className="modal-actions"><button type="button" className="btn btn-secondary" onClick={onClose}>Cancelar</button><button className="btn btn-primary" disabled={busy || name.trim().length < 2}>{busy ? 'Creando…' : 'Crear área'}</button></div></form></Modal>;
}

function AdminEditUserModal({ user, currentUserId, onClose, onSaved }) {
  const [role, setRole] = useState(roleValue(user.role));
  const [active, setActive] = useState(user.status === 'Activo');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const isSelf = Number(user.id) === Number(currentUserId);
  async function submit(e) {
    e.preventDefault(); setBusy(true); setError('');
    try { await api.admin.updateUser(user.id, { role, is_active: active }); await onSaved(); onClose(); }
    catch (err) { setError(err.message || 'No se pudo guardar el usuario.'); }
    finally { setBusy(false); }
  }
  return <Modal title={`Editar acceso de ${user.name}`} onClose={onClose}><form className="modal-form" onSubmit={submit}><p className="admin-hint">Nombre: {user.name}<br/>Correo: {user.email}<br/>Área: {user.area}</p><label>Rol<select value={role} onChange={(e) => setRole(e.target.value)} disabled={isSelf}><option value="worker">Trabajador</option><option value="manager">Gestor</option><option value="admin">Administrador</option></select></label><label className="admin-checkbox"><input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} disabled={isSelf}/>Cuenta activa</label>{isSelf && <p className="admin-hint">No puedes cambiar tu propio rol ni desactivar tu cuenta desde este panel.</p>}<p className="admin-hint">La API todavía no permite modificar nombre, correo o área.</p>{error && <div className="form-error" role="alert">{error}</div>}<div className="modal-actions"><button type="button" className="btn btn-secondary" onClick={onClose}>Cancelar</button><button className="btn btn-primary" disabled={busy || (role === roleValue(user.role) && active === (user.status === 'Activo'))}>{busy ? 'Guardando…' : 'Guardar cambios'}</button></div></form></Modal>;
}

function AdminDeleteUserModal({ user, onClose, onDeleted }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function confirm() {
    setBusy(true); setError('');
    try { await api.admin.deleteUser(user.id); await onDeleted(); onClose(); }
    catch (err) { setError(err.message || 'No se pudo eliminar el usuario.'); }
    finally { setBusy(false); }
  }
  return <Modal title="Eliminar usuario" onClose={onClose}><p>Se eliminará la cuenta de <strong>{user.name}</strong> ({user.email}). Esta acción no se puede deshacer.</p>{error && <div className="form-error" role="alert">{error}</div>}<div className="modal-actions"><button type="button" className="btn btn-secondary" onClick={onClose}>Cancelar</button><button type="button" className="btn btn-danger" disabled={busy} onClick={confirm}>{busy ? 'Eliminando…' : 'Eliminar cuenta'}</button></div></Modal>;
}

function AuthenticatedApp() {
  const { user, loading } = useAuth();
  const [view, setView] = useState(() => adminViewFromPath(window.location.pathname));
  const [data, setData] = useState(null);
  const [dataView, setDataView] = useState(null);
  const [error, setError] = useState('');
  const [modal, setModal] = useState(null);
  const [notice, setNotice] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [auditPage, setAuditPage] = useState(0);
  const [auditQuery, setAuditQuery] = useState('');
  const [managerEditor, setManagerEditor] = useState(null);
  const managerView = MANAGER_VIEWS.includes(view) ? view : 'inicio';
  const activeView = user?.role === 'admin' ? view : user?.role === 'manager' ? managerView : 'inicio';
  const navView = user?.role === 'worker' ? view : activeView;

  useEffect(() => {
    const onPopState = () => { setView(adminViewFromPath(window.location.pathname)); setError(''); setNotice(null); };
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  useEffect(() => {
    if (!user) return;
    if (user.role === 'admin') {
      const initialView = adminViewFromPath(window.location.pathname);
      if (window.location.pathname !== ADMIN_PATHS[initialView]) window.history.replaceState(null, '', ADMIN_PATHS[initialView]);
      setView(initialView);
    } else if (window.location.pathname.startsWith('/admin')) {
      window.history.replaceState(null, '', '/');
      setView('inicio');
    }
    setData(null); setDataView(null); setError(''); setNotice(null);
  }, [user]);

  useEffect(() => {
    if (!user) return;
    let active = true;
    async function load() {
      if (user.role === 'manager') return loadManagerPanel(activeView);
      if (user.role !== 'admin') return api.worker.dashboard();
      if (activeView === 'inicio') return api.admin.dashboard();
      if (activeView === 'usuarios' || activeView === 'areas') {
        const [users, areas] = await Promise.all([api.admin.users(), api.admin.areas()]);
        return { users, areas };
      }
      if (activeView === 'auditoria') return { audit: await api.admin.audit({ limit: 20, offset: auditPage * 20, q: auditQuery }) };
      return { report: await api.admin.reportSummary() };
    }
    load().then((result) => { if (active) { setData(result); setDataView(activeView); setError(''); } }).catch((err) => { if (active) setError(err.message || 'No se pudo cargar el panel.'); });
    return () => { active = false; };
  }, [user, activeView, reloadKey, auditPage, auditQuery]);

  function navigate(nextView) {
    if (user?.role === 'admin') {
      const path = ADMIN_PATHS[nextView] || ADMIN_PATHS.inicio;
      if (window.location.pathname !== path) window.history.pushState(null, '', path);
    }
    setView(nextView);
    setError('');
    setNotice(null);
  }

  if (loading) return <LoadingScreen/>;
  if (!user) return <LoginPage/>;
  if (!['worker', 'manager', 'admin'].includes(user.role)) return <div className="fatal-state"><h1>Acceso no autorizado</h1><p>Tu cuenta no tiene un rol válido asignado.</p></div>;

  async function refreshAdmin(message) {
    setNotice({ type: 'success', message });
    setReloadKey((value) => value + 1);
  }

  async function exportReport() {
    try {
      const blob = await api.admin.exportReport();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `inkasec-reporte-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setNotice({ type: 'success', message: 'Se descargó el reporte por área.' });
    } catch (err) { setNotice({ type: 'error', message: err.message || 'No se pudo exportar el CSV.' }); }
  }

  const content = error ? <div className="fatal-state inside"><h2>No pudimos cargar esta sección</h2><p>{error}</p><button className="btn btn-secondary" onClick={() => { setError(''); setReloadKey((value) => value + 1); }}>Reintentar</button></div> : !data || dataView !== activeView ? <div className="panel admin-loading" role="status">Cargando sección…</div> : user.role === 'admin' ? <AdminViews data={data} view={view} onCreateUser={() => setModal('user')} onCreateArea={() => setModal('area')} onExport={exportReport} onEditUser={(item) => setModal({ type: 'edit', user: item })} onDeleteUser={(item) => setModal({ type: 'delete', user: item })} currentUserId={user.id} notice={notice} auditPage={auditPage} setAuditPage={setAuditPage} auditQuery={auditQuery} setAuditQuery={setAuditQuery}/> : user.role === 'manager' ? <ManagerViews data={data} view={activeView} onNew={(kind) => setManagerEditor({ kind, id: null })} onEdit={(row) => setManagerEditor({ kind: row.kind, id: row.id })} onChanged={() => setReloadKey((value) => value + 1)}/> : <WorkerViews key={view} data={data} view={view} setView={navigate} onRefresh={() => setReloadKey((value) => value + 1)}/>;

  return <InkaSecLayout activeView={navView} onViewChange={navigate} notifications={data?.notifications || []}><div className="inka-page-shell"><ErrorBoundary key={activeView}>{content}</ErrorBoundary></div>{managerEditor && <ManagerEditorModal kind={managerEditor.kind} id={managerEditor.id} topics={data?.topics || []} onClose={() => setManagerEditor(null)} onSaved={() => setReloadKey((value) => value + 1)}/>} {modal === 'user' && <AdminCreateUserModal onClose={() => setModal(null)} areas={data?.areas || []} onCreated={() => refreshAdmin('Usuario creado correctamente.')}/>} {modal === 'area' && <AdminCreateAreaModal onClose={() => setModal(null)} onCreated={() => refreshAdmin('Área creada correctamente.')}/>} {modal?.type === 'edit' && <AdminEditUserModal user={modal.user} currentUserId={user.id} onClose={() => setModal(null)} onSaved={() => refreshAdmin('Acceso actualizado correctamente.')}/>} {modal?.type === 'delete' && <AdminDeleteUserModal user={modal.user} onClose={() => setModal(null)} onDeleted={() => refreshAdmin('Usuario eliminado correctamente.')}/>}</InkaSecLayout>;
}

export default function App() {
  // La verificación de certificados es pública: no pide iniciar sesión.
  const verify = window.location.pathname.match(/^\/verificar\/?([A-Za-z0-9-]*)\/?$/);
  if (verify) return <VerifyCertificatePage code={verify[1]}/>;
  return <AuthProvider><AuthenticatedApp/></AuthProvider>;
}
