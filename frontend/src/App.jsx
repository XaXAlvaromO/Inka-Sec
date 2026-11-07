
import React, { useEffect, useState } from 'react';
import { AuthProvider, useAuth } from './AuthContext';
import InkaSecLayout, { Icon } from './InkaSecLayout';
import { api } from './api';
import { ADMIN_PATHS, adminViewFromPath } from './adminRoutes';
import ParticleNetwork from './ParticleNetwork';
import './inka-sec.css';

function ProgressBar({ value, danger = false }) {
  return <div className={`progress-track ${danger ? 'is-danger' : ''}`} aria-label={`${value}%`}><span style={{ width: `${Math.max(0, Math.min(100, value))}%` }}/></div>;
}

function StatCard({ item }) {
  return <article className="stat-card"><span className={`stat-icon tone-${item.tone || 'violet'}`}><Icon name={item.icon}/></span><div><small>{item.label}</small><strong>{item.value}</strong><p>{item.helper}</p></div></article>;
}

function EmptyState({ title, description }) {
  return <div className="empty-state"><span><Icon name="shield" size={28}/></span><h3>{title}</h3><p>{description}</p></div>;
}

function LoadingScreen() {
  return <div className="inka-loading"><span className="inka-brand-mark"><Icon name="shield" size={22}/></span><div className="loading-bar"><span/></div><p>Preparando tu espacio seguro…</p></div>;
}

function LoginPage() {
  const { login, verify2FA } = useAuth();
  const [step, setStep] = useState('credentials');
  const [form, setForm] = useState({ email: '', password: '', code: '' });
  const [challenge, setChallenge] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submitCredentials(e) {
    e.preventDefault(); setError(''); setBusy(true);
    try {
      const result = await login({ email: form.email.trim(), password: form.password });
      if (result?.requires_2fa) { setChallenge(result.challenge_id); setStep('2fa'); }
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
        <div className="login-message"><span className="eyebrow">CAPACITACIÓN QUE SE CONVIERTE EN HÁBITO</span><h1>Seguridad digital, <em>sin complicaciones.</em></h1><p>Aprende a reconocer riesgos reales, practica con escenarios breves y fortalece la seguridad de tu organización.</p></div>
        <div className="login-trust"><div><Icon name="lock" size={18}/><span><strong>Acceso protegido</strong><small>Sesión corporativa y 2FA para roles críticos</small></span></div><div><Icon name="shield" size={18}/><span><strong>Privacidad por diseño</strong><small>El navegador no almacena tokens de producción</small></span></div></div>
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
              <span className="security-seal"><Icon name="lock" size={25}/></span><span className="eyebrow">VERIFICACIÓN EN DOS PASOS</span><h2>Confirma que eres tú</h2><p className="form-intro">Ingresa el código de 6 dígitos de tu aplicación de autenticación.</p>
              <label>Código de seguridad<input className="otp-input" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.replace(/\D/g, '') })} placeholder="000000" required /></label>
              {error && <div className="form-error" role="alert">{error}</div>}
              <button className="btn btn-primary btn-block btn-lg" disabled={busy || form.code.length !== 6}>{busy ? 'Verificando…' : 'Verificar y entrar'}</button>
              <button className="text-link" type="button" onClick={() => { setStep('credentials'); setError(''); setForm({ ...form, code: '' }); }}>Volver al inicio de sesión</button>
            </form>
          )}
        </div>
      </section>
    </div>
  );
}

function WorkerHome({ data, setView, onOpen }) {
  return <>
    <section className="page-hero compact-hero"><div><span className="eyebrow">TU RUTA DE APRENDIZAJE</span><h1>Aprende a protegerte <span>con decisiones simples.</span></h1><p>Continúa donde lo dejaste y practica con situaciones reales de tu trabajo.</p><div className="hero-actions"><button className="btn btn-primary" onClick={() => setView('modulos')}>Continuar aprendiendo <Icon name="chevron" size={17}/></button><button className="btn btn-secondary" onClick={() => setView('progreso')}>Ver mi progreso</button></div></div><article className="progress-summary"><div className="progress-ring" style={{ '--value': `${data.progress * 3.6}deg` }}><span><strong>{data.progress}%</strong><small>completado</small></span></div><div><small>Avance general</small><h3>Tu constancia está dando resultados</h3><p>Completa 2 módulos más para finalizar la ruta básica.</p></div></article></section>
    <section className="stats-grid">{data.stats.map((item) => <StatCard key={item.label} item={item}/>)}</section>
    <section className="two-col-grid"><article className="panel"><div className="panel-head"><div><span className="eyebrow">ASIGNADOS A TI</span><h2>Continúa aprendiendo</h2></div><button className="text-button" onClick={() => setView('modulos')}>Ver todos</button></div><ModuleList modules={data.modules} onOpen={onOpen} /></article><ChallengeCard challenge={data.challenge}/></section>
    <section className="two-col-grid lower"><article className="panel"><div className="panel-head"><div><span className="eyebrow">MEJORA CONTINUA</span><h2>Temas a reforzar</h2></div></div><div className="topic-list">{data.weakTopics.map((item) => <div key={item.name}><span className="topic-icon"><Icon name={item.icon}/></span><div><strong>{item.name}</strong><small>{item.errors} errores recientes</small></div><div className="topic-score"><b>{item.score}%</b><ProgressBar value={item.score}/></div></div>)}</div></article><article className="panel certificate-card"><span className="certificate-mark"><Icon name="award" size={28}/></span><span className="eyebrow">CERTIFICACIÓN</span><h2>Fundamentos de seguridad digital</h2><p>Tu certificado se habilitará al completar la ruta y aprobar los retos requeridos.</p><button className="btn btn-secondary" onClick={() => setView('certificados')}>Ver certificado</button></article></section>
  </>;
}

function ModuleList({ modules, onOpen }) {
  return (
    <div className="module-list">
      {modules.map((module) => (
        <article className="module-row" key={module.id}>
          <span className="module-icon"><Icon name={module.icon}/></span>
          <div className="module-copy">
            <div className="module-topline"><span>{module.topic}</span><small>Vence {module.due}</small></div>
            <h3>{module.title}</h3>
            <div className="module-meta"><span>{module.time}</span><b>{module.progress}%</b></div>
            <ProgressBar value={module.progress}/>
          </div>
          <button className="round-button" aria-label={`Abrir ${module.title}`} onClick={() => onOpen(module.id)}><Icon name="chevron" size={17}/></button>
        </article>
      ))}
    </div>
  );
}

function ChallengeCard({ challenge }) {
  return <article className="panel challenge-card"><div className="challenge-tag"><Icon name="target" size={16}/> Reto de la semana <b>+{challenge.points} pts</b></div><span className="challenge-icon"><Icon name="shield" size={34}/></span><h2>{challenge.title}</h2><p>{challenge.description}</p><div className="challenge-meta"><span>{challenge.time}</span><span>Vence en {challenge.due}</span></div><button className="btn btn-primary btn-block">Resolver reto</button></article>;
}

function ModulePlayer({ moduleId, onBack, onCompleted }) {
  const [module, setModule] = useState(null);
  const [step, setStep] = useState(0);
  const [diagnostic, setDiagnostic] = useState({});
  const [answers, setAnswers] = useState({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;

    api.worker.module(moduleId)
      .then((data) => { if (active) setModule(data); })
      .catch((err) => { if (active) setError(err.message); });

    return () => { active = false; };
  }, [moduleId]);

  if (error) {
    return <div className="fatal-state inside"><h2>No se pudo cargar el módulo</h2><p>{error}</p><button className="btn btn-secondary" onClick={onBack}>Volver</button></div>;
  }

  if (!module) return <LoadingScreen/>;

  async function saveDiagnostic() {
    const responses = module.diagnostic.map((item) => ({
      dimension: item.dimension,
      code: item.code,
      value: Number(diagnostic[item.code]),
    }));

    if (responses.some((item) => !item.value)) {
      setError('Responde todas las preguntas antes de continuar.');
      return;
    }

    setBusy(true);
    setError('');

    try {
      await api.worker.saveComb(moduleId, { phase: 'pre', responses });
      setStep(1);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function finishModule() {
    let correct = 0;

    module.capacity_questions.forEach((question, index) => {
      if (Number(answers[index]) === question.correct) correct += 1;
    });

    const score = Math.round((correct / module.capacity_questions.length) * 100);

    setBusy(true);

    try {
      await api.worker.completeModule(moduleId, score);
      setStep(6);
      if (onCompleted) onCompleted();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <GenericPage eyebrow={module.topic} title={module.title} description={module.behavior_objective}>
      <article className="panel spaced-panel">
        <button className="text-button" onClick={onBack}>← Volver a mis módulos</button>
        <p>Paso {Math.min(step + 1, 6)} de 6</p>
        <ProgressBar value={step >= 6 ? 100 : ((step + 1) / 6) * 100}/>

        {step === 0 && (
          <section>
            <h2>Diagnóstico inicial</h2>
            <p>Indica cuánto estás de acuerdo con cada afirmación.</p>
            {module.diagnostic.map((item) => (
              <div key={item.code} className="module-question">
                <p>{item.statement}</p>
                <select value={diagnostic[item.code] || ''} onChange={(e) => setDiagnostic({ ...diagnostic, [item.code]: e.target.value })}>
                  <option value="">Selecciona</option>
                  <option value="1">1 - Totalmente en desacuerdo</option>
                  <option value="2">2 - En desacuerdo</option>
                  <option value="3">3 - Neutral</option>
                  <option value="4">4 - De acuerdo</option>
                  <option value="5">5 - Totalmente de acuerdo</option>
                </select>
              </div>
            ))}
            <button className="btn btn-primary" disabled={busy} onClick={saveDiagnostic}>Continuar</button>
          </section>
        )}

        {step === 1 && (
          <section>
            <span className="eyebrow">MICROLECCIÓN</span>
            <h2>Aprende lo esencial</h2>
            <p>{module.micro_lesson}</p>
            <button className="btn btn-primary" onClick={() => setStep(2)}>Continuar</button>
          </section>
        )}

        {step === 2 && (
          <section>
            <span className="eyebrow">CAPACIDAD</span>
            <h2>Pon a prueba lo aprendido</h2>
            {module.capacity_questions.map((question, index) => (
              <div className="module-question" key={index}>
                <p><strong>{question.prompt}</strong></p>
                {question.options.map((option, optionIndex) => (
                  <label key={optionIndex}>
                    <input type="radio" name={`question-${index}`} value={optionIndex} checked={Number(answers[index]) === optionIndex} onChange={(e) => setAnswers({ ...answers, [index]: e.target.value })}/>
                    {' '}{option}
                  </label>
                ))}
              </div>
            ))}
            <button className="btn btn-primary" disabled={Object.keys(answers).length !== module.capacity_questions.length} onClick={() => setStep(3)}>Continuar</button>
          </section>
        )}

        {step === 3 && (
          <section>
            <span className="eyebrow">OPORTUNIDAD</span>
            <h2>Identifica tus barreras</h2>
            <p>{module.opportunity_question}</p>
            <textarea rows="5" placeholder="Escribe brevemente tu respuesta..."/>
            <button className="btn btn-primary" onClick={() => setStep(4)}>Continuar</button>
          </section>
        )}

        {step === 4 && (
          <section>
            <span className="eyebrow">MOTIVACIÓN</span>
            <h2>Piensa en las consecuencias</h2>
            <p>{module.motivation_question}</p>
            <textarea rows="5" placeholder="Escribe brevemente tu respuesta..."/>
            <button className="btn btn-primary" onClick={() => setStep(5)}>Continuar</button>
          </section>
        )}

        {step === 5 && (
          <section>
            <span className="eyebrow">ACCIÓN REAL</span>
            <h2>Llévalo a tu trabajo</h2>
            <p>{module.real_action}</p>
            <div className="insight-box"><p>El siguiente refuerzo estará programado para los días {module.reinforcement_days.join(', ')}.</p></div>
            {error && <div className="form-error">{error}</div>}
            <button className="btn btn-primary" disabled={busy} onClick={finishModule}>{busy ? 'Guardando…' : 'Finalizar módulo'}</button>
          </section>
        )}

        {step === 6 && (
          <section>
            <span className="security-seal"><Icon name="check" size={30}/></span>
            <h2>Módulo completado</h2>
            <p>Tu progreso y resultado fueron guardados correctamente.</p>
            <button className="btn btn-primary" onClick={onBack}>Volver a mis módulos</button>
          </section>
        )}
      </article>
    </GenericPage>
  );
}

function WorkerViews({ data, view, setView }) {
  const [selectedModule, setSelectedModule] = useState(null);

  if (selectedModule) {
    return <ModulePlayer moduleId={selectedModule} onBack={() => setSelectedModule(null)} onCompleted={() => {}}/>;
  }

  if (view === 'inicio') return <WorkerHome data={data} setView={setView} onOpen={setSelectedModule}/>;

  if (view === 'modulos') {
    return <GenericPage eyebrow="TU RUTA DE APRENDIZAJE" title="Mis módulos" description="Completa los contenidos asignados y continúa fortaleciendo tus hábitos de seguridad."><article className="panel"><ModuleList modules={data.modules} onOpen={setSelectedModule}/></article></GenericPage>;
  }

  if (view === 'progreso') {
    return <GenericPage eyebrow="MI AVANCE" title="Mi progreso" description="Revisa cuánto has avanzado en tu ruta de aprendizaje."><article className="panel"><h2>Avance general</h2><h3>{data.progress}% completado</h3><ProgressBar value={data.progress}/><div className="topic-list">{data.weakTopics.map((item) => <div key={item.name}><span className="topic-icon"><Icon name={item.icon}/></span><div><strong>{item.name}</strong><small>{item.errors} errores recientes</small></div><div className="topic-score"><b>{item.score}%</b><ProgressBar value={item.score}/></div></div>)}</div></article></GenericPage>;
  }

  if (view === 'certificados') {
    return <GenericPage eyebrow="CERTIFICACIÓN" title="Mis certificados" description="Aquí podrás consultar los certificados obtenidos."><article className="panel"><EmptyState title="Certificado pendiente" description="El certificado estará disponible cuando completes la ruta y cumplas los requisitos."/></article></GenericPage>;
  }

  return <WorkerHome data={data} setView={setView} onOpen={setSelectedModule}/>;
}

function ManagerHome({ data, onCreate }) {
  return <><section className="page-heading"><div><span className="eyebrow">PANEL DE CONTENIDO</span><h1>Contenido útil, claro y <span>medible.</span></h1><p>Crea experiencias breves, asígnalas a la organización y revisa qué está funcionando.</p></div><button className="btn btn-primary" onClick={onCreate}>Crear contenido</button></section><section className="stats-grid">{data.stats.map((item) => <StatCard key={item.label} item={item}/>)}</section><section className="two-col-grid manager-grid"><ContentTable rows={data.content}/><article className="panel"><span className="eyebrow">ANÁLISIS</span><h2>Temas con más errores</h2><div className="error-bars">{data.topicErrors.map((item) => <div key={item.topic}><div><span>{item.topic}</span><b>{item.errorRate}% error</b></div><ProgressBar value={item.errorRate} danger/></div>)}</div><div className="insight-box"><Icon name="shield" size={18}/><p><strong>Phishing necesita refuerzo.</strong> Considera una segunda actividad práctica para las áreas con mayor tasa de error.</p></div></article></section></>;
}

function ContentTable({ rows }) {
  return <article className="panel"><div className="panel-head"><div><span className="eyebrow">BIBLIOTECA</span><h2>Contenido reciente</h2></div></div><div className="table-wrap"><table><thead><tr><th>Contenido</th><th>Tipo</th><th>Estado</th><th>Asignados</th><th>Aprobación</th><th>Actualizado</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td><strong>{row.title}</strong></td><td>{row.type}</td><td><span className={`status status-${row.status.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')}`}>{row.status}</span></td><td>{row.users}</td><td>{row.success == null ? '—' : `${row.success}%`}</td><td>{row.updated}</td></tr>)}</tbody></table></div></article>;
}

function ManagerViews({ data, view, onCreate }) {
  if (view === 'inicio') return <ManagerHome data={data} onCreate={onCreate}/>;
  if (view === 'contenido') return <GenericPage eyebrow="BIBLIOTECA" title="Contenido" description="Crea, edita, publica y organiza módulos en lenguaje sencillo."><div className="page-toolbar"><button className="btn btn-primary" onClick={onCreate}>Crear contenido</button></div><ContentTable rows={data.content}/></GenericPage>;
  if (view === 'retos') return <GenericPage eyebrow="PRÁCTICA" title="Retos" description="Gestiona escenarios prácticos basados en situaciones reales del entorno laboral."><article className="panel"><EmptyState title="Panel de retos preparado" description="Conecta GET /manager/challenges para mostrar y administrar los retos desde FastAPI."/></article></GenericPage>;
  if (view === 'asignaciones') return <GenericPage eyebrow="PLANIFICACIÓN" title="Asignaciones" description="Define audiencia, área y fecha límite para cada módulo o reto."><article className="panel"><EmptyState title="Asignaciones centralizadas" description="Conecta POST /manager/assignments para programar contenido por usuario o área."/></article></GenericPage>;
  return <GenericPage eyebrow="ANALÍTICA" title="Estadísticas" description="Mide aprobación, errores frecuentes y efectividad del contenido."><article className="panel"><div className="error-bars">{data.topicErrors.map((item) => <div key={item.topic}><div><span>{item.topic}</span><b>{item.errorRate}% error</b></div><ProgressBar value={item.errorRate} danger/></div>)}</div></article></GenericPage>;
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

export function AdminHome({ data, onCreateUser, onExport, search, setSearch, onEditUser, onDeleteUser, currentUserId }) {
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

function GenericPage({ eyebrow, title, description, children }) {
  return <><section className="simple-heading"><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></section>{children}</>;
}

function Modal({ title, onClose, children }) {
  useEffect(() => { const onKey = (e) => e.key === 'Escape' && onClose(); window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey); }, [onClose]);
  return <div className="modal-backdrop" role="presentation" onMouseDown={(e) => e.target === e.currentTarget && onClose()}><div className="modal" role="dialog" aria-modal="true" aria-label={title}><div className="modal-head"><div><span className="eyebrow">INKASEC</span><h2>{title}</h2></div><button type="button" className="round-button" onClick={onClose}>×</button></div>{children}</div></div>;
}

function ManagerCreateModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ title: '', type: 'Módulo', topic: 'Phishing', description: '' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(e) {
    e.preventDefault(); setBusy(true); setError('');
    try { const item = await api.manager.createContent(form); onCreated(item); onClose(); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  return <Modal title="Crear contenido" onClose={onClose}><form className="modal-form" onSubmit={submit}><label>Título<input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required maxLength={120}/></label><div className="form-grid"><label>Tipo<select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}><option>Módulo</option><option>Reto</option></select></label><label>Tema<select value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })}><option>Phishing</option><option>Contraseñas</option><option>Wi-Fi público</option><option>2FA</option></select></label></div><label>Descripción<textarea rows="4" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} required maxLength={500}/></label>{error && <div className="form-error">{error}</div>}<div className="modal-actions"><button type="button" className="btn btn-secondary" onClick={onClose}>Cancelar</button><button className="btn btn-primary" disabled={busy}>{busy ? 'Guardando…' : 'Guardar borrador'}</button></div></form></Modal>;
}

function AdminCreateUserModal({ onClose, onCreated, areas = [] }) {
  const [form, setForm] = useState({ name: '', email: '', area: areas[0]?.name || '', role: 'worker' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [created, setCreated] = useState(null);

  async function submit(e) {
    e.preventDefault(); setBusy(true); setError('');
    try {
      const { temporary_password, totp_setup_secret, ...user } = await api.admin.createUser({ ...form, name: form.name.trim(), email: form.email.trim(), area: form.area.trim() });
      await onCreated(user);
      setCreated({ email: user.email, temporary_password, totp_setup_secret });
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  if (created) return <Modal title="Usuario creado" onClose={onClose}><div className="created-user-credentials"><p>Guarda estos datos ahora y entrégalos al usuario por un canal seguro. Se muestran una sola vez.</p><div><strong>Correo</strong><code>{created.email}</code></div><div><strong>Contraseña inicial</strong><code>{created.temporary_password}</code></div>{created.totp_setup_secret && <div><strong>Secreto para configurar 2FA</strong><code>{created.totp_setup_secret}</code><small>El usuario debe agregar este secreto a su aplicación de autenticación antes de iniciar sesión.</small></div>}<div className="modal-actions"><button type="button" className="btn btn-primary" onClick={onClose}>Ya guardé los datos</button></div></div></Modal>;

  return <Modal title="Crear usuario" onClose={onClose}><form className="modal-form" onSubmit={submit}><label>Nombre completo<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required maxLength={120}/></label><label>Correo corporativo<input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required/></label><div className="form-grid"><label>Área<select value={form.area} onChange={(e) => setForm({ ...form, area: e.target.value })} required><option value="" disabled>Selecciona un área</option>{areas.map((area) => <option key={area.id || area.name} value={area.name}>{area.name}</option>)}</select></label><label>Rol<select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}><option value="worker">Trabajador</option><option value="manager">Gestor</option><option value="admin">Administrador</option></select></label></div><p className="form-note">Las áreas se crean en «Áreas y roles». Los roles Gestor y Administrador requieren configurar 2FA.</p>{error && <div className="form-error" role="alert">{error}</div>}<div className="modal-actions"><button type="button" className="btn btn-secondary" onClick={onClose}>Cancelar</button><button className="btn btn-primary" disabled={busy || !form.area}>{busy ? 'Creando…' : 'Crear usuario'}</button></div></form></Modal>;
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
  const canPromote = user.twoFactor || roleValue(user.role) !== 'worker';

  async function submit(e) {
    e.preventDefault(); setBusy(true); setError('');
    try { await api.admin.updateUser(user.id, { role, is_active: active }); await onSaved(); onClose(); }
    catch (err) { setError(err.message || 'No se pudo guardar el usuario.'); }
    finally { setBusy(false); }
  }

  return <Modal title={`Editar acceso de ${user.name}`} onClose={onClose}><form className="modal-form" onSubmit={submit}><p className="admin-hint">Nombre: {user.name}<br/>Correo: {user.email}<br/>Área: {user.area}</p><label>Rol<select value={role} onChange={(e) => setRole(e.target.value)} disabled={isSelf}><option value="worker">Trabajador</option><option value="manager" disabled={!canPromote}>Gestor</option><option value="admin" disabled={!canPromote}>Administrador</option></select></label>{!canPromote && <p className="admin-hint">Para asignar un rol con 2FA a esta cuenta, la API necesita ofrecer un proceso de configuración del autenticador. Por ahora, crea una cuenta nueva con ese rol.</p>}<label className="admin-checkbox"><input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} disabled={isSelf}/>Cuenta activa</label>{isSelf && <p className="admin-hint">No puedes cambiar tu propio rol ni desactivar tu cuenta desde este panel.</p>}<p className="admin-hint">La API todavía no permite modificar nombre, correo o área.</p>{error && <div className="form-error" role="alert">{error}</div>}<div className="modal-actions"><button type="button" className="btn btn-secondary" onClick={onClose}>Cancelar</button><button className="btn btn-primary" disabled={busy || (role === roleValue(user.role) && active === (user.status === 'Activo'))}>{busy ? 'Guardando…' : 'Guardar cambios'}</button></div></form></Modal>;
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
  const activeView = user?.role === 'admin' ? view : 'inicio';

  useEffect(() => {
    const onPopState = () => {
      setView(adminViewFromPath(window.location.pathname));
      setError('');
      setNotice(null);
    };

    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  useEffect(() => {
    if (!user) return;

    if (user.role === 'admin') {
      const initialView = adminViewFromPath(window.location.pathname);
      if (window.location.pathname !== ADMIN_PATHS[initialView]) {
        window.history.replaceState(null, '', ADMIN_PATHS[initialView]);
      }
      setView(initialView);
    } else if (window.location.pathname.startsWith('/admin')) {
      window.history.replaceState(null, '', '/');
      setView('inicio');
    }

    setData(null);
    setDataView(null);
    setError('');
    setNotice(null);
  }, [user]);

  // CAMBIO 1: este efecto carga los datos de la sección activa.
  // También permite actualizar automáticamente la auditoría.
  useEffect(() => {
    if (!user) return;

    let active = true;

    // CAMBIO 2: evita que se ejecuten varias peticiones al mismo tiempo.
    let isLoading = false;

    async function load() {
      if (!active || isLoading) return;

      isLoading = true;

      try {
        let result;

        if (user.role !== 'admin') {
          result = user.role === 'manager'
            ? await api.manager.dashboard()
            : await api.worker.dashboard();

        } else if (activeView === 'inicio') {
          result = await api.admin.dashboard();

        } else if (activeView === 'usuarios' || activeView === 'areas') {
          const [users, areas] = await Promise.all([
            api.admin.users(),
            api.admin.areas()
          ]);

          result = { users, areas };

        } else if (activeView === 'auditoria') {

          // CAMBIO 3: consulta el historial de auditoría.
          // Respeta la página actual y el texto de búsqueda.
          const audit = await api.admin.audit({
            limit: 20,
            offset: auditPage * 20,
            q: auditQuery
          });

          result = { audit };

        } else {
          result = {
            report: await api.admin.reportSummary()
          };
        }

        if (active) {
          setData(result);
          setDataView(activeView);
          setError('');
        }

      } catch (err) {
        if (active) {
          setError(err.message || 'No se pudo cargar el panel.');
        }

      } finally {
        isLoading = false;
      }
    }

    // CAMBIO 4: carga inicial al entrar o cambiar de sección.
    load();

    // CAMBIO 5: actualiza Auditoría automáticamente cada 5 segundos.
    // No activa este intervalo en Inicio, Usuarios, Áreas ni Reportes.
    let intervalId = null;

    if (user.role === 'admin' && activeView === 'auditoria') {
      intervalId = window.setInterval(() => {
        load();
      }, 5000);
    }

    // CAMBIO 6: limpia el intervalo al salir de Auditoría
    // y evita que una petición anterior actualice el estado.
    return () => {
      active = false;

      if (intervalId !== null) {
        window.clearInterval(intervalId);
      }
    };

  }, [user, activeView, reloadKey, auditPage, auditQuery]);

  function navigate(nextView) {
    if (user?.role === 'admin') {
      const path = ADMIN_PATHS[nextView] || ADMIN_PATHS.inicio;
      if (window.location.pathname !== path) {
        window.history.pushState(null, '', path);
      }
    }

    setView(nextView);
    setError('');
    setNotice(null);
  }

  if (loading) return <LoadingScreen/>;
  if (!user) return <LoginPage/>;

  if (!['worker', 'manager', 'admin'].includes(user.role)) {
    return <div className="fatal-state"><h1>Acceso no autorizado</h1><p>Tu cuenta no tiene un rol válido asignado.</p></div>;
  }

  async function refreshAdmin(message) {
    setNotice({ type: 'success', message });
    setReloadKey((value) => value + 1);
  }

  async function exportReport() {
    try {
      const blob = await api.admin.exportReport();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `inkasec-reporte-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setNotice({ type: 'success', message: 'Se descargó el reporte por área.' });
    } catch (err) {
      setNotice({ type: 'error', message: err.message || 'No se pudo exportar el CSV.' });
    }
  }

  const content = error
    ? <div className="fatal-state inside"><h2>No pudimos cargar esta sección</h2><p>{error}</p><button className="btn btn-secondary" onClick={() => { setError(''); setReloadKey((value) => value + 1); }}>Reintentar</button></div>
    : !data || dataView !== activeView
      ? <div className="panel admin-loading" role="status">Cargando sección…</div>
      : user.role === 'admin'
        ? <AdminViews
            data={data}
            view={view}
            onCreateUser={() => setModal('user')}
            onCreateArea={() => setModal('area')}
            onExport={exportReport}
            onEditUser={(item) => setModal({ type: 'edit', user: item })}
            onDeleteUser={(item) => setModal({ type: 'delete', user: item })}
            currentUserId={user.id}
            notice={notice}
            auditPage={auditPage}
            setAuditPage={setAuditPage}
            auditQuery={auditQuery}
            setAuditQuery={setAuditQuery}
          />
        : user.role === 'manager'
          ? <ManagerViews data={data} view={view} onCreate={() => setModal('content')}/>
          : <WorkerViews data={data} view={view} setView={navigate}/>;

  return (
    <InkaSecLayout activeView={view} onViewChange={navigate} notifications={data?.notifications || []}>
      <div className="inka-page-shell">{content}</div>

      {modal === 'content' && (
        <ManagerCreateModal
          onClose={() => setModal(null)}
          onCreated={(item) => setData((prev) => ({ ...prev, content: [item, ...prev.content] }))}
        />
      )}

      {modal === 'user' && (
        <AdminCreateUserModal
          onClose={() => setModal(null)}
          areas={data?.areas || []}
          onCreated={() => refreshAdmin('Usuario creado correctamente.')}
        />
      )}

      {modal === 'area' && (
        <AdminCreateAreaModal
          onClose={() => setModal(null)}
          onCreated={() => refreshAdmin('Área creada correctamente.')}
        />
      )}

      {modal?.type === 'edit' && (
        <AdminEditUserModal
          user={modal.user}
          currentUserId={user.id}
          onClose={() => setModal(null)}
          onSaved={() => refreshAdmin('Acceso actualizado correctamente.')}
        />
      )}

      {modal?.type === 'delete' && (
        <AdminDeleteUserModal
          user={modal.user}
          onClose={() => setModal(null)}
          onDeleted={() => refreshAdmin('Usuario eliminado correctamente.')}
        />
      )}
    </InkaSecLayout>
  );
}

export default function App() {
  return <AuthProvider><AuthenticatedApp/></AuthProvider>;
}
