/**
 * Client API du frontend GCT AI Assistant.
 *
 * L'URL de base est configurée via la variable d'environnement
 * VITE_API_BASE_URL (défaut : http://127.0.0.1:8000). Voir .env.example.
 */

// URL de base de l'API. Vide (défaut) = chemins relatifs gérés par un proxy
// (Vite en développement, nginx en Docker). Pour un backend direct sans proxy,
// définir VITE_API_BASE_URL (ex: http://127.0.0.1:8000).
const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

const TOKEN_KEY = 'gct_token';
let authToken = null;

/** Enregistre (ou efface) le token d'authentification. */
export function setToken(token) {
  authToken = token || null;
  if (authToken) {
    localStorage.setItem(TOKEN_KEY, authToken);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

/** Retourne le token stocké (mémoire + localStorage). */
export function getToken() {
  if (authToken === null) {
    authToken = localStorage.getItem(TOKEN_KEY) || null;
  }
  return authToken;
}

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Valide le token courant auprès du backend. Retourne {authenticated, role}.
 * Lève une erreur avec `status` (401 si non authentifié).
 */
export async function verifyToken() {
  const response = await fetch(`${API_BASE}/api/v1/auth/verify`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    const error = new Error('Non authentifié');
    error.status = response.status;
    throw error;
  }
  return response.json();
}

/**
 * Envoie une question au backend et retourne {question, answer, sources}.
 * Les erreurs sont levées avec une propriété `status` (code HTTP) si possible.
 */
export async function ask(question, opts = {}) {
  const response = await fetch(`${API_BASE}/api/v1/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({
      question,
      top_k: opts.top_k ?? 5,
      temperature: opts.temperature ?? 0.2,
      max_tokens: opts.max_tokens ?? 512,
    }),
  });

  if (!response.ok) {
    let detail = '';
    try {
      const data = await response.json();
      detail = data && data.detail ? data.detail : '';
    } catch (_) {
      /* réponse non-JSON : on garde le message générique */
    }
    const error = new Error(detail || `Erreur serveur (HTTP ${response.status})`);
    error.status = response.status;
    throw error;
  }

  return response.json();
}

/**
 * Envoie un fichier PDF au backend pour ingestion.
 * Retourne {file_name, status, pages, chunks, message, ocr_pages}.
 */
export async function uploadDocument(file) {
  const form = new FormData();
  form.append('file', file);

  const response = await fetch(`${API_BASE}/api/v1/documents`, {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  });

  if (!response.ok) {
    let detail = '';
    try {
      const data = await response.json();
      detail = data && data.detail ? data.detail : '';
    } catch (_) {
      /* réponse non-JSON : message générique */
    }
    const error = new Error(detail || `Erreur serveur (HTTP ${response.status})`);
    error.status = response.status;
    throw error;
  }

  return response.json();
}

/**
 * Récupère le contenu d'une page d'un document PDF.
 * Retourne {file_name, page_number, total_pages, content}.
 */
export async function getDocumentContent(fileName, pageNumber = null) {
  if (!fileName) {
    throw new Error('Nom de fichier requis');
  }

  const params = new URLSearchParams();
  if (pageNumber !== null && pageNumber !== undefined) {
    params.append('page_number', pageNumber);
  }

  const query = params.toString();
  const encodedName = encodeURIComponent(fileName);
  const url = `${API_BASE}/api/v1/documents/${encodedName}/content${query ? '?' + query : ''}`;

  console.log(`[DEBUG] Fetching: ${url}`);
  console.log(`[DEBUG] File name: "${fileName}"`);
  console.log(`[DEBUG] Page number: ${pageNumber}`);

  const response = await fetch(url, {
    headers: authHeaders(),
  });

  if (!response.ok) {
    let detail = '';
    try {
      const data = await response.json();
      detail = data && data.detail ? data.detail : '';
    } catch (_) {
      /* réponse non-JSON : message générique */
    }
    console.error(`[ERROR] HTTP ${response.status}: ${detail}`);
    const error = new Error(detail || `Erreur serveur (HTTP ${response.status})`);
    error.status = response.status;
    throw error;
  }

  const data = await response.json();
  console.log(`[DEBUG] Document loaded: ${data.file_name}, page ${data.page_number}/${data.total_pages}`);
  return data;
}
