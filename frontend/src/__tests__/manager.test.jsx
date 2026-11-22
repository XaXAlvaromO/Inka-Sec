// Panel del gestor de contenido: resumen, biblioteca, editor de módulos, asignaciones y estadísticas.
// Los datos de ejemplo son respuestas reales de la API con el seed de demostración.
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api', async () => (await import('../test/mockApi')).createApiMock());

import App from '../App';
import { api, ApiError } from '../api';
import fixtures from '../test/fixtures/manager.json';

const MANAGER = { id: 2, name: 'Lucía Torres', email: 'gestor@inkasec.pe', role: 'manager', area: 'RR. HH.' };
const ASSIGNMENT = { id: 31, item_type: 'module', title: 'Bloquea tu computadora siempre', target: 'Área Finanzas', due: 'Vence el 30/11/2026' };

beforeEach(() => {
  api.auth.me.mockResolvedValue({ user: MANAGER });
  api.manager.dashboard.mockResolvedValue(fixtures.dashboard);
  api.manager.topics.mockResolvedValue(fixtures.topics);
  api.manager.stats.mockResolvedValue(fixtures.stats);
  api.manager.assignable.mockResolvedValue(fixtures.assignable);
  api.manager.assignments.mockResolvedValue([ASSIGNMENT]);
  api.manager.getModule.mockResolvedValue(fixtures.module);
});

async function openManager() {
  render(<App/>);
  expect(await screen.findByText(/Contenido útil, claro y/)).toBeInTheDocument();
}

const go = (name) => userEvent.click(screen.getByRole('button', { name: new RegExp(`^${name}`) }));

describe('gestor de contenido', () => {
  it('muestra el resumen con sus indicadores', async () => {
    await openManager();
    expect(screen.getByText('Contenidos publicados')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Contenido reciente' })).toBeInTheDocument();
  });

  it('filtra la biblioteca por título, tema y estado', async () => {
    await openManager();
    await go('Contenido');
    await screen.findByRole('table');
    const rows = () => within(screen.getByRole('table')).getAllByRole('row').length - 1;   // la tabla se vuelve a crear al filtrar
    const all = rows();
    await userEvent.type(screen.getByLabelText('Buscar por título'), 'bloquea');
    expect(rows()).toBe(1);
    await userEvent.clear(screen.getByLabelText('Buscar por título'));
    await userEvent.selectOptions(screen.getByLabelText('Filtrar por tema'), 'Phishing');
    await userEvent.selectOptions(screen.getByLabelText('Filtrar por estado'), 'Borrador');
    expect(screen.getByText('Crea tu primer módulo o ajusta los filtros.')).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText('Filtrar por estado'), '');
    await userEvent.selectOptions(screen.getByLabelText('Filtrar por tema'), '');
    expect(rows()).toBe(all);
  });

  it('crea un módulo con varias preguntas', async () => {
    api.manager.createModule.mockResolvedValueOnce({ id: 50 });
    await openManager();
    await userEvent.click(screen.getByRole('button', { name: 'Crear módulo' }));
    const dialog = screen.getByRole('dialog', { name: 'Nuevo módulo' });
    const q = (label) => within(dialog).getByLabelText(label);
    await userEvent.type(q('Título'), 'Bloquea tu pantalla');
    await userEvent.selectOptions(q('Tema'), 'Dispositivos y USB');
    await userEvent.selectOptions(q('Estado'), 'published');
    await userEvent.type(q('Conducta que quieres lograr'), 'Bloquear la computadora al levantarse.');
    await userEvent.type(q('Micro-lección en lenguaje sencillo'), 'Presiona Windows + L antes de levantarte del sitio.');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Agregar pregunta' }));
    const questions = within(dialog).getAllByRole('group', { name: /Pregunta \d/ });
    for (const [i, question] of questions.entries()) {
      await userEvent.type(within(question).getByLabelText('Enunciado'), `¿Pregunta ${i + 1}?`);
      await userEvent.type(within(question).getByLabelText('Opción 1'), 'No');
      await userEvent.type(within(question).getByLabelText('Opción 2'), 'Sí');
    }
    await userEvent.click(within(questions[0]).getAllByRole('radio', { name: 'Correcta' })[1]);
    await userEvent.click(within(questions[1]).getByRole('button', { name: '+ Agregar opción' }));
    await userEvent.click(within(questions[1]).getAllByRole('button', { name: 'Quitar' })[2]);
    await userEvent.type(q('Acción real que debe practicar'), 'Hoy bloquea al levantarte.');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar módulo' }));

    const payload = api.manager.createModule.mock.calls[0][0];
    expect(payload).toMatchObject({ title: 'Bloquea tu pantalla', topic: 'Dispositivos y USB', status: 'published' });
    expect(payload.capacity_questions).toEqual([
      { prompt: '¿Pregunta 1?', options: ['No', 'Sí'], correct: 1, feedback: '' },
      { prompt: '¿Pregunta 2?', options: ['No', 'Sí'], correct: 0, feedback: '' },
    ]);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('edita un módulo existente y muestra el error de la API', async () => {
    api.manager.updateModule.mockRejectedValueOnce(new ApiError('Solo puedes editar el módulo que creaste', 403));
    await openManager();
    await go('Contenido');
    const row = (await screen.findByText(fixtures.module.title)).closest('tr');
    await userEvent.click(within(row).getByRole('button', { name: 'Editar' }));
    const dialog = await screen.findByRole('dialog', { name: 'Editar módulo' });
    expect(await within(dialog).findByDisplayValue(fixtures.module.title)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar módulo' }));
    expect(api.manager.updateModule).toHaveBeenCalledWith(fixtures.module.id, expect.objectContaining({ title: fixtures.module.title }));
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Solo puedes editar el módulo que creaste');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Cancelar' }));
  });

  it('avisa si no se puede abrir un contenido para editar', async () => {
    api.manager.getModule.mockRejectedValueOnce(new ApiError('Módulo no encontrado', 404));
    await openManager();
    await go('Contenido');
    const row = (await screen.findByText(fixtures.module.title)).closest('tr');
    await userEvent.click(within(row).getByRole('button', { name: 'Editar' }));
    expect(await screen.findByText('Módulo no encontrado')).toBeInTheDocument();
  });

  it('abre el editor de retos desde la biblioteca de retos', async () => {
    await openManager();
    await go('Retos');
    await userEvent.click(await screen.findByRole('button', { name: 'Nuevo reto' }));
    expect(screen.getByRole('dialog', { name: 'Nuevo reto' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /Encuentra las señales/ })).toBeInTheDocument();
  });

  it('asigna a un área con fecha límite y quita una asignación', async () => {
    api.manager.createAssignment.mockResolvedValueOnce({ id: 32 });
    api.manager.deleteAssignment.mockResolvedValueOnce({ ok: true });
    await openManager();
    await go('Asignaciones');
    await screen.findByRole('heading', { name: 'Asignaciones activas' });
    await userEvent.selectOptions(screen.getByLabelText('Para'), 'area');
    await userEvent.selectOptions(screen.getByLabelText('Área'), String(fixtures.dashboard.areas[0].id));
    await userEvent.type(screen.getByLabelText('Fecha límite (opcional)'), '2026-12-15T18:00');
    await userEvent.click(screen.getByRole('button', { name: 'Asignar' }));
    expect(api.manager.createAssignment).toHaveBeenCalledWith(expect.objectContaining({
      item_type: fixtures.assignable[0].item_type, item_id: fixtures.assignable[0].item_id, target: 'area',
      area_id: fixtures.dashboard.areas[0].id, user_id: null, due_at: expect.stringMatching(/^2026-12-15T/) }));
    expect(await screen.findByText('Asignación guardada.')).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText('Para'), 'user');
    expect(screen.getByLabelText('Trabajador')).toBeInTheDocument();

    const row = screen.getByText(ASSIGNMENT.title, { selector: 'strong' }).closest('tr');
    await userEvent.click(within(row).getByRole('button', { name: 'Quitar' }));
    expect(api.manager.deleteAssignment).toHaveBeenCalledWith(31);
  });

  it('muestra el error al asignar', async () => {
    api.manager.createAssignment.mockRejectedValueOnce(new ApiError('La fecha límite ya pasó', 422));
    api.manager.deleteAssignment.mockRejectedValueOnce(new ApiError('Solo quien la creó puede quitarla', 404));
    await openManager();
    await go('Asignaciones');
    await userEvent.click(await screen.findByRole('button', { name: 'Asignar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('La fecha límite ya pasó');
    await userEvent.click(within(screen.getByText(ASSIGNMENT.title, { selector: 'strong' }).closest('tr')).getByRole('button', { name: 'Quitar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Solo quien la creó puede quitarla');
  });

  it('las estadísticas muestran participación y certificados, no aciertos por persona', async () => {
    await openManager();
    await go('Estadísticas');
    expect(await screen.findByRole('heading', { name: 'Certificados vigentes por tema' })).toBeInTheDocument();
    expect(screen.getByText(/no verás si cada persona acertó/)).toBeInTheDocument();
    const practice = screen.getByRole('heading', { name: 'Práctica por reto' }).closest('article');
    await userEvent.click(within(practice).getAllByRole('button', { name: 'Ver trabajadores' })[0]);
    expect(within(practice).getAllByText(/Practicó · 1 intento|Sin practicar/).length).toBeGreaterThan(0);
    expect(within(practice).queryByText('Correcto')).not.toBeInTheDocument();
    await userEvent.click(within(practice).getByRole('button', { name: 'Ocultar' }));
    const modules = screen.getByRole('heading', { name: 'Terminaciones por contenido' }).closest('article');
    await userEvent.click(within(modules).getAllByRole('button', { name: 'Ver trabajadores' })[0]);
    expect(within(modules).getAllByText(/Terminó el|Pendiente/).length).toBeGreaterThan(0);
  });

  it('muestra estados vacíos cuando aún no hay datos', async () => {
    api.manager.stats.mockResolvedValueOnce({ modules: [], challenges: [], certificates: [], workers: [], topic_errors: [], min_group: 3 });
    api.manager.assignable.mockResolvedValueOnce([]);
    api.manager.assignments.mockResolvedValueOnce([]);
    await openManager();
    await go('Estadísticas');
    expect(await screen.findByText('Aún no hay certificados')).toBeInTheDocument();
    expect(screen.getAllByText('Sin contenido propio')).toHaveLength(2);
    await go('Asignaciones');
    expect(await screen.findByText('Nada publicado todavía')).toBeInTheDocument();
    expect(screen.getByText('Sin asignaciones')).toBeInTheDocument();
  });
});
