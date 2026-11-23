// Inicio de sesión (con y sin 2FA), panel del trabajador y navegación entre secciones.
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api', async () => (await import('../test/mockApi')).createApiMock());

import App from '../App';
import { api, ApiError } from '../api';

const WORKER = { id: 1, name: 'María López', role: 'worker', area: 'Finanzas' };
const MANAGER = { id: 2, name: 'Lucía Torres', role: 'manager', area: 'RR. HH.' };

const DASHBOARD = {
  stats: [{ label: 'Módulos completados', value: '0 / 1', helper: 'Ruta COM-B', icon: 'book', tone: 'blue' }],
  progress: 0,
  modules: [{ id: 7, title: 'Phishing y enlaces sospechosos', topic: 'Phishing', progress: 0, time: '10 min', icon: 'book', due: 'Sin fecha límite' }],
  challenges: [],
  challenge: null,
  weakTopics: [],
  certificates: { active: 0, topics: 1, expiring: [], expired: [], next: { topic: 'Phishing', remaining: 1 } },
  notifications: [],
};

const MODULE = {
  topic: 'Phishing', title: 'Phishing y enlaces sospechosos', behavior_objective: 'Verificar antes de hacer clic.',
  diagnostic: [{ code: 'C1', dimension: 'capacidad', statement: 'Reconozco un enlace raro.' }],
  micro_lesson: 'Revisa el remitente.', capacity_questions: [{ prompt: '¿Qué haces?', options: ['Clic', 'Reviso'] }],
  opportunity_question: '¿Qué te dificulta?', motivation_question: '¿Por qué importa?', real_action: 'Reporta un correo.',
  reinforcement_days: [7, 30, 90], saved_reflections: {},
};

async function loginAs(user, extra = {}) {
  api.auth.me.mockRejectedValueOnce(new ApiError('Sin sesión', 401));
  api.auth.login.mockResolvedValueOnce(extra.requires2fa ? { requires_2fa: true, challenge_id: 'abc', email_hint: 'g***@inkasec.pe' } : { user });
  render(<App/>);
  await userEvent.type(await screen.findByLabelText('Correo corporativo'), 'persona@inkasec.pe');
  await userEvent.type(screen.getByLabelText('Contraseña'), 'Clave-Segura-2026');
  await userEvent.click(screen.getByRole('button', { name: /Continuar/ }));
}

beforeEach(() => {
  api.worker.dashboard.mockResolvedValue(DASHBOARD);
  api.worker.certificates.mockResolvedValue({
    pass_percent: 80, validity_days: 365, warning_days: 30, history: [], new: [],
    topics: [{ topic: 'Phishing', passed: 0, total: 1, certificate: null,
      modules: [{ id: 7, title: 'Phishing y enlaces sospechosos', completed: false, passed: false, needs_review: false }] }],
  });
  api.worker.module.mockResolvedValue(MODULE);
});

describe('inicio de sesión', () => {
  it('la verificación pública no pide iniciar sesión', async () => {
    window.history.replaceState(null, '', '/verificar/INKA-7KQ2-M9XP-4HTR');
    api.certificates.verify.mockResolvedValueOnce({ valid: true, status: 'active', status_label: 'Vigente', holder: 'María López',
      company: 'InkaSec Demo', topic: 'Phishing', issued_at: '2026-11-22T10:00:00Z', expires_at: '2027-11-22T10:00:00Z' });
    render(<App/>);
    expect(await screen.findByText('Certificado válido')).toBeInTheDocument();
    expect(api.auth.me).not.toHaveBeenCalled();
  });

  it('muestra el formulario cuando no hay sesión', async () => {
    api.auth.me.mockRejectedValueOnce(new ApiError('Sin sesión', 401));
    render(<App/>);
    expect(await screen.findByRole('heading', { name: 'Inicia sesión' })).toBeInTheDocument();
  });

  it('el trabajador entra directo a su panel', async () => {
    await loginAs(WORKER);
    expect(await screen.findByText('Continúa aprendiendo')).toBeInTheDocument();
    expect(api.auth.login).toHaveBeenCalledWith({ email: 'persona@inkasec.pe', password: 'Clave-Segura-2026' });
    expect(screen.getByText(/te falta 1 módulo para el certificado de Phishing/i)).toBeInTheDocument();
  });

  it('muestra el error cuando las credenciales no son válidas', async () => {
    api.auth.me.mockRejectedValueOnce(new ApiError('Sin sesión', 401));
    api.auth.login.mockRejectedValueOnce(new ApiError('Credenciales inválidas', 401));
    render(<App/>);
    await userEvent.type(await screen.findByLabelText('Correo corporativo'), 'x@inkasec.pe');
    await userEvent.type(screen.getByLabelText('Contraseña'), 'Clave-Mala-123');
    await userEvent.click(screen.getByRole('button', { name: /Continuar/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Credenciales inválidas');
  });

  it('el gestor pasa por el código de 6 dígitos', async () => {
    await loginAs(MANAGER, { requires2fa: true });
    expect(await screen.findByText('g***@inkasec.pe')).toBeInTheDocument();
    const submit = screen.getByRole('button', { name: 'Verificar y entrar' });
    const code = screen.getByLabelText('Código de seguridad');
    await userEvent.type(code, '12ab34');
    expect(code).toHaveValue('1234');                 // solo acepta números
    expect(submit).toBeDisabled();                     // hasta tener 6 dígitos
    api.auth.verify2FA.mockRejectedValueOnce(new ApiError('Código 2FA inválido', 401));
    await userEvent.type(code, '56');
    await userEvent.click(submit);
    expect(await screen.findByRole('alert')).toHaveTextContent('Código 2FA inválido');
    expect(api.auth.verify2FA).toHaveBeenCalledWith({ challenge_id: 'abc', code: '123456' });

    await userEvent.click(screen.getByRole('button', { name: 'Volver al inicio de sesión' }));
    expect(screen.getByRole('heading', { name: 'Inicia sesión' })).toBeInTheDocument();
  });
});

describe('navegación del trabajador', () => {
  it('un módulo abierto desde Certificados marca "Mis módulos" y vuelve a Certificados', async () => {
    await loginAs(WORKER);
    await screen.findByText('Continúa aprendiendo');
    await userEvent.click(screen.getByRole('button', { name: /Certificados/ }));
    const topic = await screen.findByRole('heading', { name: 'Phishing' });
    await userEvent.click(within(topic.closest('article')).getByRole('button', { name: 'Abrir' }));

    expect(await screen.findByRole('button', { name: '← Volver a mis certificados' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Mis módulos/ })).toHaveClass('is-active');

    await userEvent.click(screen.getByRole('button', { name: '← Volver a mis certificados' }));
    expect(await screen.findByRole('heading', { name: 'Mis certificados' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Certificados/ })).toHaveClass('is-active');
  });

  it('un clic en la barra cierra el módulo abierto', async () => {
    await loginAs(WORKER);
    await screen.findByText('Continúa aprendiendo');
    await userEvent.click(screen.getAllByRole('button', { name: 'Abrir Phishing y enlaces sospechosos' })[0]);
    expect(await screen.findByRole('button', { name: '← Volver al inicio' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Retos/ }));
    expect(await screen.findByRole('heading', { name: 'Mis retos' })).toBeInTheDocument();
    expect(screen.queryByText('DIAGNÓSTICO INICIAL')).not.toBeInTheDocument();
  });

  it('el paso de acción muestra los recordatorios y el módulo termina', async () => {
    api.worker.gradeCapacity.mockResolvedValue({ results: [{ index: 0, is_correct: true, correct_index: 1, feedback: 'Bien.' }], correct: 1, total: 1, percent: 100, pass_percent: 80, new_certificates: [] });
    api.worker.completeModule.mockResolvedValue({ new_certificates: ['Phishing'] });
    await loginAs(WORKER);
    await screen.findByText('Continúa aprendiendo');
    await userEvent.click(screen.getAllByRole('button', { name: 'Abrir Phishing y enlaces sospechosos' })[0]);

    await userEvent.click(await screen.findByRole('radio', { name: /De acuerdo/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Continuar' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Continuar' }));
    await userEvent.click(screen.getByRole('radio', { name: 'Reviso' }));
    await userEvent.click(screen.getByRole('button', { name: 'Revisar respuestas' }));
    expect(await screen.findByText('Respondiste 1 de 1 correctamente.')).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'Reviso' })).toBeDisabled();   // la práctica no se cambia después de revisar
    await userEvent.click(screen.getByRole('button', { name: 'Continuar' }));
    for (let i = 0; i < 2; i += 1) {
      await userEvent.type(await screen.findByPlaceholderText(/Escribe con tus palabras/), 'Me cuesta recordar.');
      await userEvent.click(screen.getByRole('button', { name: 'Guardar y continuar' }));
    }
    expect(await screen.findByText('Te recordaremos este módulo en 7, 30, 90 días.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Finalizar módulo' }));
    expect(await screen.findByText('¡Obtuviste el certificado de Phishing!')).toBeInTheDocument();
  });
});

describe('retos y progreso del trabajador', () => {
  const QUICK = { id: 1, kind: 'quick', kind_label: 'Reto rápido', topic: 'Phishing', title: 'Correo del gerente', description: 'Pide una transferencia.',
    options: ['La hago', 'Verifico'], steps: [], segments: [], due: 'Sin fecha límite' };

  beforeEach(() => {
    api.worker.dashboard.mockResolvedValue({
      ...DASHBOARD,
      challenge: { ...QUICK, time: '1-3 min' },
      challenges: [{ ...QUICK, answered: false, is_correct: null, tries: 0 },
        { ...QUICK, id: 2, title: 'Practicado', answered: true, is_correct: false, tries: 2 }],
      weakTopics: [{ name: 'Phishing', icon: 'shield', errors: 1, score: 50 }],
    });
  });

  it('practica el reto de la semana desde el inicio y vuelve a la lista de retos', async () => {
    api.worker.answerChallenge.mockResolvedValueOnce({ is_correct: true, correct_index: 1, feedback: 'Bien.', tries: 1 });
    await loginAs(WORKER);
    await userEvent.click(await screen.findByRole('button', { name: 'Practicar reto' }));
    await userEvent.click(screen.getByRole('radio', { name: /Verifico/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Enviar respuesta' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Volver a mis retos' }));
    expect(api.worker.dashboard).toHaveBeenCalledTimes(2);   // se recarga para mostrar el intento
  });

  it('la lista de retos muestra el estado de práctica y permite repetir', async () => {
    await loginAs(WORKER);
    await screen.findByText('Continúa aprendiendo');
    await userEvent.click(screen.getByRole('button', { name: /^Retos/ }));
    expect(await screen.findByText('Puedes mejorar · 2 intentos')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Practicar de nuevo' }));
    expect(await screen.findByRole('button', { name: '← Volver a mis retos' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: '← Volver a mis retos' }));
    expect(await screen.findByRole('heading', { name: 'Mis retos' })).toBeInTheDocument();
  });

  it('muestra los temas a reforzar en Mi progreso y la lista de módulos', async () => {
    await loginAs(WORKER);
    await screen.findByText('Continúa aprendiendo');
    await userEvent.click(screen.getByRole('button', { name: /Mi progreso/ }));
    expect(await screen.findByText('0% completado')).toBeInTheDocument();
    expect(screen.getByText('1 errores recientes')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Mis módulos/ }));
    expect(await screen.findByRole('heading', { name: 'Mis módulos' })).toBeInTheDocument();
  });

  it('muestra el error si el panel no carga y permite reintentar', async () => {
    api.worker.dashboard.mockRejectedValueOnce(new ApiError('Sin conexión con la API', 0));
    await loginAs(WORKER);
    expect(await screen.findByText('Sin conexión con la API')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByText('Continúa aprendiendo')).toBeInTheDocument();
  });
});
