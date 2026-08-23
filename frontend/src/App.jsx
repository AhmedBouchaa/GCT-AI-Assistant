import { useEffect, useRef, useState } from 'react';
import { ask, getToken, setToken, uploadDocument, verifyToken } from './api';
import SourceViewer from './components/SourceViewer';
import './styles.css';

const ARABIC_RE = /[؀-ۿ]/;

function isArabic(text) {
  return ARABIC_RE.test(text);
}

const EXAMPLE_PROMPTS = [
  {
    title: 'تعيين لجنة صيانة',
    body: 'من هو رئيس اللجنة الفنية لصيانة المعدات الثقيلة بوحدات الإنتاج بقابس؟',
  },
  {
    title: 'Procédure GCT',
    body: 'Quelle est la procédure de maintenance des équipements lourds à Gabès selon les notes GCT ?',
  },
  {
    title: 'Document N° 002/2026',
    body: 'Résume la note N° 002/2026 concernant la commission technique des équipements lourds.',
  },
];

function formatError(err) {
  if (err instanceof TypeError) return 'Impossible de joindre le serveur API. Vérifiez que le backend est lancé, puis réessayez.';
  switch (err.status) {
    case 401: return 'Authentification requise. Vérifiez votre jeton d’accès.';
    case 400: return 'Requête invalide. Vérifiez votre question.';
    case 503: return 'Le serveur Ollama est injoignable. Vérifiez qu’Ollama est lancé, puis réessayez.';
    case 502: return 'Erreur de génération du modèle. Veuillez réessayer.';
    case 500: return 'Erreur interne du serveur. Veuillez réessayer.';
    default: return err.message || 'Erreur inconnue.';
  }
}

function formatUploadError(err) {
  if (err instanceof TypeError) return 'Impossible de joindre le serveur API. Vérifiez que le backend est lancé.';
  return err.message || 'Erreur inconnue.';
}

function LogoMark({ small }) {
  return (
    <div className={`logo-mark ${small ? 'logo-mark--small' : ''}`} aria-hidden>
      GCT
    </div>
  );
}

export default function App() {
  const [auth, setAuth] = useState({ status: 'checking', role: null });
  const [loginToken, setLoginToken] = useState('');
  const [loginError, setLoginError] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [selectedSource, setSelectedSource] = useState(null);
  const endRef = useRef(null);

  useEffect(() => {
    const stored = getToken();
    if (stored) setToken(stored);
    verifyToken().then((info) => setAuth({ status: 'in', role: info.role })).catch(() => setAuth({ status: 'out', role: null }));
  }, []);

  useEffect(() => {
    const el = endRef.current;
    if (el && typeof el.scrollIntoView === 'function') {
      try { el.scrollIntoView({ behavior: 'smooth' }); } catch (_) {}
    }
  }, [messages, loading]);

  async function handleLogin() {
    setLoginError(null);
    setToken(loginToken.trim());
    try {
      const info = await verifyToken();
      setAuth({ status: 'in', role: info.role });
    } catch (err) {
      setToken(null);
      setLoginError("Jeton invalide. Vérifiez votre jeton d'accès.");
    }
  }

  function handleLogout() {
    setToken(null);
    setAuth({ status: 'out', role: null });
    setMessages([]);
    setUploadResult(null);
    setShowUpload(false);
  }

  function handleNewConversation() {
    setMessages([]);
    setInput('');
    setUploadResult(null);
  }

  async function handleUpload() {
    if (!file || uploading) return;
    setUploading(true);
    setUploadResult(null);
    try {
      const data = await uploadDocument(file);
      if (data.status === 'ocr_required') setUploadResult({ type: 'ocr', text: data.message || 'OCR non disponible.' });
      else if (data.status === 'skipped') setUploadResult({ type: 'success', text: data.message || 'Document déjà indexé.' });
      else if (data.status === 'failed') setUploadResult({ type: 'error', text: data.message || 'Ingestion impossible.' });
      else {
        const base = `Document ajouté — ${data.pages} pages / ${data.chunks} chunks`;
        const type = data.ocr_pages > 0 ? 'ocr' : 'success';
        const text = data.ocr_pages > 0 ? `${base} (${data.ocr_pages} page(s) en échec OCR)` : base;
        setUploadResult({ type, text });
      }
    } catch (err) {
      setUploadResult({ type: 'error', text: formatUploadError(err) });
    } finally {
      setUploading(false);
    }
  }

  async function handleSend() {
    const question = input.trim();
    if (!question || loading) return;
    setMessages((prev) => [...prev, { role: 'user', text: question }]);
    setInput('');
    setLoading(true);
    try {
      const data = await ask(question);
      setMessages((prev) => [...prev, { role: 'assistant', text: data.answer, sources: data.sources || [] }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', error: true, text: formatError(err) }]);
    } finally {
      setLoading(false);
    }
  }

  function handleExampleClick(prompt) {
    setInput(prompt);
  }

  const loggedIn = auth.status === 'in';
  const canSend = input.trim().length > 0 && !loading;

  // ---- Login ----
  if (!loggedIn) {
    return (
      <div className="login-shell">
        <header className="topbar topbar--guest">
          <div className="topbar-inner">
            <LogoMark />
            <div className="topbar-brand"><span className="brand-name">GCT AI Assistant</span><span className="brand-sub">Groupe Chimique Tunisien</span></div>
          </div>
        </header>
        <main className="login">
          <div className="login-card">
            {auth.status === 'checking' ? (
              <p className="login-muted">Vérification de l’accès…</p>
            ) : (
              <>
                <h2 className="login-title">Connexion</h2>
                <p className="login-muted">Une authentification est requise pour accéder à l’assistant.</p>
                <input type="password" className="login-input" value={loginToken} onChange={(e) => setLoginToken(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') handleLogin(); }} placeholder="Jeton d’accès" aria-label="Jeton d'accès" />
                <button type="button" className="login-button" onClick={handleLogin} disabled={!loginToken.trim()}>Connexion</button>
                {loginError && <div className="login-error">{loginError}</div>}
              </>
            )}
          </div>
        </main>
      </div>
    );
  }

  // ---- Authenticated ----
  return (
    <div className="shell">
      {sidebarOpen && <button type="button" className="sidebar-overlay" onClick={() => setSidebarOpen(false)} aria-label="Fermer la barre latérale" />}
      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'sidebar--open' : 'sidebar--closed'}`}>
        <div className="sidebar-top">
          <div className="sidebar-brand">
            <LogoMark small />
            <div className="sidebar-brand-text">
              <span className="sidebar-title">GCT AI Assistant</span>
              <span className="sidebar-sub">Assistant documentaire</span>
            </div>
          </div>
          <button type="button" className="sidebar-new" onClick={handleNewConversation} title="Nouvelle conversation">＋ Nouvelle conversation</button>
          <div className="sidebar-section">
            <div className="sidebar-label">Conversation</div>
            <div className="sidebar-hint">{messages.length === 0 ? 'Aucun message — démarrez par une question.' : `${messages.length} message(s) dans cette conversation.`}</div>
          </div>
        </div>

        <div className="sidebar-bottom">
          {auth.role === 'admin' && (
            <div className="sidebar-section sidebar-section--docs">
              <button type="button" className="sidebar-docs-toggle" onClick={() => setShowUpload((v) => !v)} aria-expanded={showUpload} aria-label="Documents">
                Documents
              </button>
              {showUpload && (
                <div className="sidebar-upload">
                  <div className="sidebar-upload-title">Ajouter un document</div>
                  <input type="file" accept=".pdf,application/pdf" onChange={(e) => setFile(e.target.files[0] || null)} aria-label="Fichier PDF" />
                  <button type="button" className="sidebar-upload-btn" onClick={handleUpload} disabled={!file || uploading}>{uploading ? '…' : 'Importer'}</button>
                  {uploading && <div className="sidebar-upload-status loading">Ingestion en cours…</div>}
                  {uploadResult && <div className={`sidebar-upload-status ${uploadResult.type}`}>{uploadResult.text}</div>}
                </div>
              )}
            </div>
          )}

          {/* Desktop+: Documents are in the sidebar. Mobile also exposes a quick toggle above the chat. */}
          <div className="sidebar-account">
            <span className="sidebar-role">{auth.role === 'admin' ? 'Admin' : 'Utilisateur'}</span>
            <button type="button" className="sidebar-logout" onClick={handleLogout}>Déconnexion</button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="main">
        <header className="topbar">
          <div className="topbar-inner">
            <button type="button" className="topbar-menu" onClick={() => setSidebarOpen((v) => !v)} aria-label="Basculer la barre latérale">{sidebarOpen ? '☰' : '☰'}</button>
            <div className="topbar-title">GCT AI Assistant</div>
            <div className="topbar-spacer" />
            <span className="topbar-role">{auth.role === 'admin' ? 'Admin' : 'Utilisateur'}</span>
            {auth.role === 'admin' && !sidebarOpen && (
              <button type="button" className="topbar-docs" onClick={() => setShowUpload((v) => !v)} aria-expanded={showUpload}>Documents</button>
            )}
          </div>
        </header>

        {/* Upload is in the sidebar; no duplicate panel in the main area. */}
        {showUpload && !sidebarOpen && (
          <div className="upload-panel upload-panel--fallback">
            <div className="upload-title">Ajouter un document</div>
            <div className="upload-row">
              <input type="file" accept=".pdf,application/pdf" onChange={(e) => setFile(e.target.files[0] || null)} aria-label="Fichier PDF" />
              <button type="button" onClick={handleUpload} disabled={!file || uploading}>{uploading ? '…' : 'Importer'}</button>
            </div>
            {uploading && <div className="upload-status loading">Ingestion en cours…</div>}
            {uploadResult && <div className={`upload-status ${uploadResult.type}`}>{uploadResult.text}</div>}
          </div>
        )}

        <main className="chat">
          {messages.length === 0 ? (
            <div className="welcome">
              <div className="welcome-mark" aria-hidden>GCT</div>
              <h1 className="welcome-title">GCT AI Assistant</h1>
              <p className="welcome-sub">Posez une question sur les procédures, notes et documents du GCT.</p>
              <div className="welcome-actions">
                <button type="button" className="welcome-clear" onClick={handleNewConversation}>Nouvelle conversation</button>
              </div>
              <div className="welcome-prompts">
                {EXAMPLE_PROMPTS.map((p) => (
                  <button key={p.title} type="button" className="prompt-card" onClick={() => handleExampleClick(p.body)} title={p.body}>
                    <span className="prompt-card-title">{p.title}</span>
                    <span className="prompt-card-body" dir={isArabic(p.body) ? 'rtl' : 'ltr'}>{p.body}</span>
                  </button>
                ))}
              </div>
              <p className="welcome-langs">Français · العربية · English</p>
            </div>
          ) : (
            <>
              <div className="conversation-toolbar">
                <button type="button" className="toolbar-clear" onClick={handleNewConversation} disabled={loading}>Nouvelle conversation</button>
              </div>
              <div className="messages">
                {messages.map((message, i) => (
                  <div key={i} className={`message ${message.role}${message.error ? ' error' : ''}`} dir={isArabic(message.text) ? 'rtl' : 'ltr'}>
                    <div className="message-avatar" aria-hidden>{message.role === 'user' ? 'Vous' : 'GCT'}</div>
                    <div className="message-body">
                      <div className="bubble">{message.text}</div>
                      {message.sources && message.sources.length > 0 && (
                        <div className="sources" aria-label="Sources">
                          <div className="sources-title">Sources</div>
                          <div className="sources-grid">
                            {message.sources.map((source, j) => (
                              <button
                                key={j}
                                className="source-card"
                                onClick={() => setSelectedSource(source)}
                                type="button"
                                title={`Cliquez pour voir ${source.file_name} page ${source.page_number || 1}`}
                              >
                                <span className="source-card-icon" aria-hidden>📄</span>
                                <div className="source-card-meta">
                                  <span className="source-file">{source.file_name}</span>
                                  {source.page_number != null && <span className="source-page"> · page {source.page_number}</span>}
                                </div>
                                <span className="source-card-label">Source</span>
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {loading && (
                  <div className="message assistant" dir="ltr">
                    <div className="message-avatar" aria-hidden>GCT</div>
                    <div className="message-body">
                      <div className="bubble bubble-loading" aria-live="polite">
                        <span className="typing-dots" aria-hidden><span /><span /><span /></span>
                        <span>Génération en cours…</span>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={endRef} />
              </div>
            </>
          )}
        </main>

        <footer className="composer">
          <div className="composer-inner">
            <div className="composer-field">
              <textarea
                value={input}
                dir={isArabic(input) ? 'rtl' : 'ltr'}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }}}
                placeholder="Écrivez votre question…  (Entrée = envoyer, Maj+Entrée = nouvelle ligne)"
                rows={1}
                aria-label="Question"
              />
              <button type="button" className="composer-send" onClick={handleSend} disabled={!canSend} aria-label="Envoyer">Envoyer</button>
            </div>
            <div className="composer-hint" dir={isArabic(input) ? 'rtl' : 'ltr'}>Entrée pour envoyer · Maj + Entrée pour une nouvelle ligne</div>
          </div>
        </footer>
      </div>

      {selectedSource && <SourceViewer source={selectedSource} onClose={() => setSelectedSource(null)} />}
    </div>
  );
}
