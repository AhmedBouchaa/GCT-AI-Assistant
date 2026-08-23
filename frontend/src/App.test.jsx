import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from './App.jsx';
import { verifyToken } from './api.js';

// verifyToken est mocké ; ask / uploadDocument / setToken / getToken restent réels.
vi.mock('./api.js', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, verifyToken: vi.fn() };
});

const MOCK_ANSWER = {
  question: 'Quel est l\'objet de la décision ?',
  answer: 'La décision porte sur la maintenance des équipements lourds.',
  sources: [
    { file_name: 'GCT_notes_exemples_50-6.pdf', page_number: 1, score: 0.8, chunk_id: 'x' },
    { file_name: 'GCT_notes_exemples_50-2.pdf', page_number: 1, score: 0.7, chunk_id: 'y' },
  ],
};

function mockFetchResolved(body, status = 200) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  });
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn());
  verifyToken.mockResolvedValue({ authenticated: true, role: 'admin' });
  localStorage.clear();
});

/** Rend l'app et attend que le chat soit visible (auth résolue en admin). */
async function renderChat() {
  render(<App />);
  await screen.findByLabelText('Question');
}

describe('GCT AI Assistant frontend', () => {
  it('affiche le titre de l\'application', () => {
    render(<App />);
    expect(screen.getByText('GCT AI Assistant')).toBeInTheDocument();
  });

  it('envoie la question et affiche la réponse + les sources', async () => {
    global.fetch = mockFetchResolved(MOCK_ANSWER);

    await renderChat();
    fireEvent.change(screen.getByLabelText('Question'), { target: { value: MOCK_ANSWER.question } });
    fireEvent.click(screen.getByText('Envoyer'));

    expect(await screen.findByText(MOCK_ANSWER.answer)).toBeInTheDocument();
    expect(screen.getByText('Sources')).toBeInTheDocument();
    expect(screen.getByText('GCT_notes_exemples_50-6.pdf')).toBeInTheDocument();
    // les deux sources affichent leur page
    expect(screen.getAllByText(/page 1/)).toHaveLength(2);

    // le chunk_id interne n'est PAS affiché à l'utilisateur
    expect(screen.queryByText('x')).not.toBeInTheDocument();
    // le score n'est pas non plus exposé
    expect(screen.queryByText(/score/)).not.toBeInTheDocument();

    // le payload envoyé au backend est correct
    const [url, init] = global.fetch.mock.calls[0];
    expect(url).toContain('/api/v1/ask');
    const body = JSON.parse(init.body);
    expect(body.question).toBe(MOCK_ANSWER.question);
    expect(body.top_k).toBe(5);
    expect(body.temperature).toBe(0.2);
    expect(body.max_tokens).toBe(512);
  });

  it('affiche un état de chargement pendant la requête', async () => {
    let resolveFetch;
    global.fetch = vi.fn().mockImplementation(
      () => new Promise((resolve) => { resolveFetch = resolve; })
    );

    await renderChat();
    fireEvent.change(screen.getByLabelText('Question'), { target: { value: 'Question ?' } });
    fireEvent.click(screen.getByText('Envoyer'));

    expect(await screen.findByText(/Génération en cours/)).toBeInTheDocument();

    resolveFetch({
      ok: true,
      status: 200,
      json: () => Promise.resolve(MOCK_ANSWER),
    });

    await waitFor(() => expect(screen.queryByText(/Génération en cours/)).not.toBeInTheDocument());
  });

  it('ne permet pas d\'envoyer une question vide', async () => {
    await renderChat();
    const button = screen.getByText('Envoyer');
    expect(button).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Question'), { target: { value: '   ' } });
    expect(button).toBeDisabled();
  });

  it('affiche un message clair quand Ollama est injoignable (503)', async () => {
    global.fetch = mockFetchResolved({ detail: 'Ollama injoignable' }, 503);

    await renderChat();
    fireEvent.change(screen.getByLabelText('Question'), { target: { value: 'Question ?' } });
    fireEvent.click(screen.getByText('Envoyer'));

    expect(await screen.findByText(/Ollama est injoignable/)).toBeInTheDocument();
  });

  it('affiche un message d\'erreur réseau si le backend est injoignable', async () => {
    global.fetch = vi.fn().mockRejectedValue(new TypeError('fetch failed'));

    await renderChat();
    fireEvent.change(screen.getByLabelText('Question'), { target: { value: 'Question ?' } });
    fireEvent.click(screen.getByText('Envoyer'));

    expect(await screen.findByText(/Impossible de joindre le serveur API/)).toBeInTheDocument();
  });
});

function selectPdf() {
  const input = screen.getByLabelText('Fichier PDF');
  const file = new File([new Uint8Array([0x25, 0x50, 0x44, 0x46])], 'doc.pdf', {
    type: 'application/pdf',
  });
  fireEvent.change(input, { target: { files: [file] } });
}

describe('Ajout de document', () => {
  it('ouvre le panneau Documents', async () => {
    await renderChat();
    fireEvent.click(screen.getByText('Documents'));
    expect(screen.getByText('Ajouter un document')).toBeInTheDocument();
  });

  it('upload réussi : affiche pages/chunks et envoie un FormData', async () => {
    global.fetch = mockFetchResolved({
      file_name: 'doc.pdf',
      status: 'indexed',
      pages: 2,
      chunks: 3,
      message: 'ok',
      ocr_pages: 0,
    });

    await renderChat();
    fireEvent.click(screen.getByText('Documents'));
    selectPdf();
    fireEvent.click(screen.getByText('Importer'));

    expect(await screen.findByText('Document ajouté — 2 pages / 3 chunks')).toBeInTheDocument();

    const [, init] = global.fetch.mock.calls[0];
    expect(init.body).toBeInstanceOf(FormData);
  });

  it('upload en cours : état de chargement', async () => {
    let resolveFetch;
    global.fetch = vi.fn().mockImplementation(
      () => new Promise((resolve) => { resolveFetch = resolve; })
    );

    await renderChat();
    fireEvent.click(screen.getByText('Documents'));
    selectPdf();
    fireEvent.click(screen.getByText('Importer'));

    expect(await screen.findByText(/Ingestion en cours/)).toBeInTheDocument();

    resolveFetch({
      ok: true,
      status: 200,
      json: () => Promise.resolve({
        file_name: 'doc.pdf', status: 'indexed', pages: 1, chunks: 1, message: 'ok', ocr_pages: 0,
      }),
    });

    await waitFor(() => expect(screen.queryByText(/Ingestion en cours/)).not.toBeInTheDocument());
  });

  it('upload OCR requis affiche le message dédié', async () => {
    global.fetch = mockFetchResolved({
      file_name: 'scan.pdf',
      status: 'ocr_required',
      pages: 1,
      chunks: 0,
      message: 'OCR requis mais non supporté : document sans texte.',
      ocr_pages: 1,
    });

    await renderChat();
    fireEvent.click(screen.getByText('Documents'));
    selectPdf();
    fireEvent.click(screen.getByText('Importer'));

    expect(await screen.findByText(/OCR requis mais non supporté/)).toBeInTheDocument();
  });

  it('upload partiel (OCR) affiche un avertissement pages', async () => {
    global.fetch = mockFetchResolved({
      file_name: 'mixte.pdf',
      status: 'indexed',
      pages: 3,
      chunks: 2,
      message: 'Document indexé avec succès.',
      ocr_pages: 1,
    });

    await renderChat();
    fireEvent.click(screen.getByText('Documents'));
    selectPdf();
    fireEvent.click(screen.getByText('Importer'));

    expect(
      await screen.findByText(/Document ajouté — 3 pages \/ 2 chunks \(1 page\(s\) en échec OCR\)/)
    ).toBeInTheDocument();
  });

  it('upload rejeté par le serveur affiche le détail', async () => {
    global.fetch = mockFetchResolved({ detail: 'Seuls les fichiers PDF sont acceptés.' }, 400);

    await renderChat();
    fireEvent.click(screen.getByText('Documents'));
    selectPdf();
    fireEvent.click(screen.getByText('Importer'));

    expect(await screen.findByText(/Seuls les fichiers PDF sont acceptés/)).toBeInTheDocument();
  });

  it('upload dupliqué affiche le message dédié', async () => {
    global.fetch = mockFetchResolved({
      file_name: 'doc.pdf',
      status: 'skipped',
      pages: 0,
      chunks: 3,
      message: 'Document déjà indexé (inchangé).',
      ocr_pages: 0,
    });

    await renderChat();
    fireEvent.click(screen.getByText('Documents'));
    selectPdf();
    fireEvent.click(screen.getByText('Importer'));

    expect(await screen.findByText(/Document déjà indexé/)).toBeInTheDocument();
  });
});

describe('Authentification', () => {
  it('affiche l\'écran de connexion quand non authentifié', async () => {
    verifyToken.mockRejectedValue({ status: 401 });

    render(<App />);

    expect(await screen.findByLabelText("Jeton d'accès")).toBeInTheDocument();
    expect(screen.queryByLabelText('Question')).not.toBeInTheDocument();
  });

  it('connexion réussie affiche le chat', async () => {
    verifyToken.mockRejectedValue({ status: 401 });
    render(<App />);
    await screen.findByLabelText("Jeton d'accès");

    verifyToken.mockResolvedValue({ authenticated: true, role: 'admin' });
    fireEvent.change(screen.getByLabelText("Jeton d'accès"), { target: { value: 'tok' } });
    fireEvent.click(screen.getByRole('button', { name: 'Connexion' }));

    expect(await screen.findByLabelText('Question')).toBeInTheDocument();
  });

  it('token invalide affiche une erreur', async () => {
    verifyToken.mockRejectedValue({ status: 401 });
    render(<App />);
    await screen.findByLabelText("Jeton d'accès");

    fireEvent.change(screen.getByLabelText("Jeton d'accès"), { target: { value: 'mauvais' } });
    verifyToken.mockRejectedValue({ status: 401 });
    fireEvent.click(screen.getByRole('button', { name: 'Connexion' }));

    expect(await screen.findByText(/Jeton invalide/)).toBeInTheDocument();
  });

  it('l\'admin voit le bouton Documents', async () => {
    await renderChat();
    expect(screen.getByText('Documents')).toBeInTheDocument();
  });

  it('l\'utilisateur (non admin) ne voit pas le bouton Documents', async () => {
    verifyToken.mockResolvedValue({ authenticated: true, role: 'user' });
    await renderChat();
    expect(screen.queryByText('Documents')).not.toBeInTheDocument();
  });

  it('déconnexion revient à l\'écran de connexion', async () => {
    await renderChat();
    fireEvent.click(screen.getByText('Déconnexion'));
    expect(await screen.findByLabelText("Jeton d'accès")).toBeInTheDocument();
  });
});
