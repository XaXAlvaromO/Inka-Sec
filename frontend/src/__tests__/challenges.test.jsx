// Retos: los tres formatos para el trabajador (con reintento) y el editor del gestor.
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../api', async () => (await import('../test/mockApi')).createApiMock());

import { api, ApiError } from '../api';
import { ChallengeEditor, ChallengePlayer } from '../challenges';

const QUICK = { id: 1, kind: 'quick', topic: 'Phishing', title: 'Correo del gerente', description: 'Pide una transferencia urgente.', options: ['La hago', 'Verifico por otro canal'] };
const STEPS = {
  id: 2, kind: 'steps', topic: 'Ingeniería social', title: 'Llamada de soporte', description: 'Suena tu anexo.',
  steps: [{ prompt: '¿Instalas el programa?', options: ['Sí', 'Verifico con soporte'] }, { prompt: 'Insiste.', options: ['Cuelgo y llamo', 'Sigo sus pasos'] }],
};
const SIGNALS = {
  id: 3, kind: 'signals', topic: 'Phishing', title: 'Cuenta suspendida', description: 'Llegó a las 8 a. m.',
  segments: [{ field: 'from', text: 'alertas@micros0ft.com' }, { field: 'subject', text: 'URGENTE' }, { field: 'body', text: 'Llama a la mesa de ayuda.' }, { field: 'link', text: 'http://login.verificar.co' }],
};

function play(challenge) {
  const onBack = vi.fn(); const onDone = vi.fn();
  render(<ChallengePlayer challenge={challenge} onBack={onBack} onDone={onDone}/>);
  return { onBack, onDone };
}

describe('reto rápido', () => {
  it('muestra la explicación y permite intentarlo de nuevo', async () => {
    api.worker.answerChallenge.mockResolvedValueOnce({ is_correct: false, correct_index: 1, feedback: 'Verifica siempre.', tries: 1 });
    const { onDone } = play(QUICK);
    const send = screen.getByRole('button', { name: 'Enviar respuesta' });
    expect(send).toBeDisabled();
    await userEvent.click(screen.getByRole('radio', { name: /La hago/ }));
    await userEvent.click(send);
    expect(await screen.findByText('Respuesta correcta: Verifico por otro canal')).toBeInTheDocument();
    expect(screen.getByText('Verifica siempre.')).toBeInTheDocument();
    expect(api.worker.answerChallenge).toHaveBeenCalledWith(1, { choice: 0 });

    await userEvent.click(screen.getByRole('button', { name: 'Intentar de nuevo' }));
    expect(screen.getByRole('button', { name: 'Enviar respuesta' })).toBeDisabled();   // empieza de cero
    await userEvent.click(screen.getByRole('button', { name: '← Volver a mis retos' }));
    expect(onDone).not.toHaveBeenCalled();
  });

  it('muestra el error si la API falla', async () => {
    api.worker.answerChallenge.mockRejectedValueOnce(new ApiError('Reto no encontrado', 404));
    play(QUICK);
    await userEvent.click(screen.getByRole('radio', { name: /Verifico/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Enviar respuesta' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Reto no encontrado');
  });
});

describe('escenario por pasos', () => {
  it('muestra la consecuencia de cada decisión y un resumen final', async () => {
    api.worker.checkStep
      .mockResolvedValueOnce({ safe: false, safe_index: 1, feedback: 'Controlan tu equipo.', safe_feedback: 'Canal oficial.' })
      .mockResolvedValueOnce({ safe: true, safe_index: 0, feedback: 'Rompes el engaño.', safe_feedback: 'Rompes el engaño.' });
    api.worker.answerChallenge.mockResolvedValueOnce({
      is_correct: false, safe_steps: 1, total_steps: 2, feedback: 'Verifica y reporta.', tries: 1,
      steps: [{ choice: 0, safe: false, safe_index: 1, safe_feedback: 'Canal oficial.' }, { choice: 0, safe: true, safe_index: 0, safe_feedback: '' }],
    });
    const { onDone } = play(STEPS);
    expect(screen.getByText('Paso 1 de 2')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('radio', { name: /Sí/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar decisión' }));
    expect(await screen.findByText('Esta decisión es riesgosa')).toBeInTheDocument();
    expect(screen.getByText(/Lo seguro: Verifico con soporte/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente paso' }));

    expect(screen.getByText('Paso 2 de 2')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('radio', { name: /Cuelgo/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar decisión' }));
    expect(await screen.findByText('Decisión segura')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Ver resultado' }));

    expect(await screen.findByText('Tomaste 1 de 2 decisiones seguras')).toBeInTheDocument();
    expect(api.worker.answerChallenge).toHaveBeenCalledWith(2, { choices: [0, 0] });
    expect(api.worker.checkStep).toHaveBeenNthCalledWith(1, 2, { step: 0, choice: 0 });
    await userEvent.click(screen.getByRole('button', { name: 'Volver a mis retos' }));
    expect(onDone).toHaveBeenCalled();
  });

  it('permite volver a un paso anterior y recupera la decisión que había elegido', async () => {
    api.worker.checkStep.mockResolvedValueOnce({ safe: false, safe_index: 1, feedback: 'Controlan tu equipo.', safe_feedback: 'Canal oficial.' });
    play(STEPS);
    expect(screen.queryByRole('button', { name: '← Paso anterior' })).not.toBeInTheDocument();   // no hay a dónde volver
    await userEvent.click(screen.getByRole('radio', { name: /Sí/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar decisión' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Siguiente paso' }));

    expect(screen.getByText('Paso 2 de 2')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: '← Paso anterior' }));

    expect(screen.getByText('Paso 1 de 2')).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /Sí/ })).toBeChecked();   // su decisión no se perdió
    expect(screen.queryByText('Esta decisión es riesgosa')).not.toBeInTheDocument();   // puede cambiar de opinión
  });

  it('felicita cuando todas las decisiones son seguras', async () => {
    api.worker.checkStep.mockResolvedValue({ safe: true, safe_index: 0, feedback: 'Bien.', safe_feedback: 'Bien.' });
    api.worker.answerChallenge.mockResolvedValueOnce({ is_correct: true, safe_steps: 2, total_steps: 2, feedback: 'Excelente.', tries: 1,
      steps: [{ choice: 1, safe: true, safe_index: 1 }, { choice: 0, safe: true, safe_index: 0 }] });
    play(STEPS);
    for (const name of [/Verifico/, /Cuelgo/]) {
      await userEvent.click(screen.getByRole('radio', { name }));
      await userEvent.click(screen.getByRole('button', { name: 'Confirmar decisión' }));
      await userEvent.click(await screen.findByRole('button', { name: /Siguiente paso|Ver resultado/ }));
    }
    expect(await screen.findByText('Tomaste todas las decisiones seguras')).toBeInTheDocument();
  });
});

describe('encuentra las señales', () => {
  it('marca, desmarca y explica cada parte al revisar', async () => {
    api.worker.answerChallenge.mockResolvedValueOnce({
      is_correct: false, found: 1, total_signals: 3, false_marks: 1, feedback: 'No hagas clic.', tries: 1,
      segments: [
        { index: 0, suspicious: true, marked: true, explanation: 'Dominio falso.' },
        { index: 1, suspicious: true, marked: false, explanation: 'Urgencia.' },
        { index: 2, suspicious: false, marked: true, explanation: 'Frase normal.' },
        { index: 3, suspicious: true, marked: false, explanation: 'Enlace no oficial.' },
      ],
    });
    play(SIGNALS);
    const mail = screen.getByLabelText('Mensaje para revisar');
    await userEvent.click(within(mail).getByRole('button', { name: /micros0ft/ }));
    await userEvent.click(within(mail).getByRole('button', { name: /URGENTE/ }));
    await userEvent.click(within(mail).getByRole('button', { name: /URGENTE/ }));   // desmarcar
    await userEvent.click(within(mail).getByRole('button', { name: /mesa de ayuda/ }));
    expect(screen.getByText('Marcaste 2 partes. Toca de nuevo para desmarcar.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Revisar mensaje' }));

    expect(api.worker.answerChallenge).toHaveBeenCalledWith(3, { marked: [0, 2] });
    expect(await screen.findByText('Encontraste 1 de 3 señales')).toBeInTheDocument();
    expect(screen.getByText('Señal encontrada.')).toBeInTheDocument();
    expect(screen.getAllByText('Se te pasó esta señal.')).toHaveLength(2);
    expect(screen.getByText('No era una señal.')).toBeInTheDocument();
    expect(screen.getByText(/Marcaste 1 parte normal como sospechosa/)).toBeInTheDocument();
  });
});

describe('editor de retos del gestor', () => {
  const topics = ['Phishing', 'Contraseñas'];

  async function fillCommon() {
    await userEvent.type(screen.getByLabelText('Título'), 'Mi reto');
    await userEvent.type(screen.getByRole('textbox', { name: /Escenario|Contexto/ }), 'Un caso que pasa todos los días en la oficina.');
  }

  it('crea un reto rápido con sus opciones', async () => {
    api.manager.createChallenge.mockResolvedValueOnce({ id: 9 });
    const onDone = vi.fn();
    render(<ChallengeEditor topics={topics} onDone={onDone} onClose={vi.fn()}/>);
    await fillCommon();
    await userEvent.type(screen.getByLabelText('Opción 1'), 'Abrir');
    await userEvent.type(screen.getByLabelText('Opción 2'), 'Reportar');
    await userEvent.click(screen.getAllByRole('radio', { name: 'Correcta' })[1]);
    await userEvent.click(screen.getByRole('button', { name: 'Guardar reto' }));
    expect(api.manager.createChallenge).toHaveBeenCalledWith(expect.objectContaining({
      kind: 'quick', title: 'Mi reto', topic: 'Phishing', options: ['Abrir', 'Reportar'], correct_index: 1, status: 'draft' }));
    expect(onDone).toHaveBeenCalled();
  });

  it('arma los pasos del escenario y cambia la opción segura', async () => {
    api.manager.createChallenge.mockResolvedValueOnce({ id: 10 });
    render(<ChallengeEditor topics={topics} onDone={vi.fn()} onClose={vi.fn()}/>);
    await userEvent.click(screen.getByRole('radio', { name: /Escenario por pasos/ }));
    await fillCommon();
    const steps = screen.getAllByRole('group', { name: /Paso \d/ });
    for (const [i, step] of steps.entries()) {
      await userEvent.type(within(step).getByRole('textbox', { name: /Qué pasa/ }), `Momento ${i + 1}`);
      await userEvent.type(within(step).getByLabelText(`Paso ${i + 1}, opción 1`), 'Bien');
      await userEvent.type(within(step).getByLabelText(`Paso ${i + 1}, opción 2`), 'Mal');
      await userEvent.type(within(step).getByLabelText('Consecuencia de la opción 1'), 'Es lo seguro.');
      await userEvent.type(within(step).getByLabelText('Consecuencia de la opción 2'), 'Es riesgoso.');
    }
    await userEvent.click(within(steps[1]).getAllByRole('radio', { name: 'Segura' })[1]);
    await userEvent.click(within(steps[1]).getByRole('button', { name: '+ Agregar opción' }));
    expect(within(steps[1]).getAllByRole('radio', { name: 'Segura' })).toHaveLength(3);
    await userEvent.click(within(steps[1]).getAllByRole('button', { name: 'Quitar' })[2]);
    await userEvent.click(screen.getByRole('button', { name: 'Guardar reto' }));
    const payload = api.manager.createChallenge.mock.calls[0][0];
    expect(payload.kind).toBe('steps');
    expect(payload.options).toBeUndefined();
    expect(payload.steps).toHaveLength(2);
    expect(payload.steps[1].options.map((o) => o.safe)).toEqual([false, true]);
    expect(payload.steps[0].options[0]).toEqual({ text: 'Bien', feedback: 'Es lo seguro.', safe: true });
  });

  it('arma las partes del mensaje y muestra el error de la API', async () => {
    api.manager.createChallenge.mockRejectedValueOnce(new ApiError('Marca al menos un fragmento como sospechoso', 422));
    render(<ChallengeEditor topics={topics} onDone={vi.fn()} onClose={vi.fn()}/>);
    await userEvent.click(screen.getByRole('radio', { name: /Encuentra las señales/ }));
    await fillCommon();
    await userEvent.click(screen.getByRole('button', { name: 'Agregar parte' }));
    const parts = screen.getAllByRole('group', { name: /Parte \d/ });
    expect(parts).toHaveLength(4);
    for (const part of parts) {
      await userEvent.type(within(part).getByLabelText('Texto'), 'Texto');
      await userEvent.type(within(part).getByLabelText('Explicación que verá al revisar'), 'Porque sí.');
    }
    await userEvent.selectOptions(within(parts[3]).getByLabelText('Tipo'), 'link');
    await userEvent.click(within(parts[3]).getByRole('checkbox', { name: 'Es una señal sospechosa' }));
    await userEvent.click(screen.getByRole('button', { name: 'Guardar reto' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Marca al menos un fragmento como sospechoso');
    const payload = api.manager.createChallenge.mock.calls[0][0];
    expect(payload.segments.map((s) => s.field)).toEqual(['from', 'subject', 'body', 'link']);
    expect(payload.segments[3].suspicious).toBe(true);
  });

  it('carga un reto existente y lo actualiza', async () => {
    api.manager.updateChallenge.mockResolvedValueOnce({ id: 3 });
    const initial = { id: 3, title: 'Viejo', topic: 'Tema heredado', kind: 'quick', scenario: 'Un caso que ya existía en la empresa.',
      options: ['A', 'B', 'C'], correct_index: 2, feedback: '', status: 'published', steps: [], segments: [] };
    render(<ChallengeEditor initial={initial} topics={topics} onDone={vi.fn()} onClose={vi.fn()}/>);
    expect(screen.getByRole('option', { name: 'Tema heredado' })).toBeInTheDocument();   // conserva el tema antiguo
    await userEvent.click(screen.getAllByRole('button', { name: 'Quitar' })[0]);
    await userEvent.click(screen.getByRole('button', { name: 'Guardar reto' }));
    expect(api.manager.updateChallenge).toHaveBeenCalledWith(3, expect.objectContaining({ options: ['B', 'C'], correct_index: 1 }));
  });
});
