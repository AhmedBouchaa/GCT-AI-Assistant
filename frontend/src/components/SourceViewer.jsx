import { useState, useEffect } from 'react';
import { getDocumentContent } from '../api';
import './SourceViewer.css';

export default function SourceViewer({ source, onClose }) {
  const [content, setContent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(source?.page_number || 1);
  const [totalPages, setTotalPages] = useState(null);

  // Validate source object
  if (!source || !source.file_name) {
    return (
      <div className="source-viewer-overlay" onClick={onClose}>
        <div className="source-viewer-modal" onClick={(e) => e.stopPropagation()}>
          <div className="source-viewer-error">
            <p>⚠️ Erreur: informations de document invalides</p>
          </div>
          <button className="source-viewer-close" onClick={onClose} aria-label="Fermer">
            ✕
          </button>
        </div>
      </div>
    );
  }

  useEffect(() => {
    loadPageContent(currentPage);
  }, [currentPage, source.file_name]);

  async function loadPageContent(pageNum) {
    setLoading(true);
    setError(null);
    try {
      console.log(`Fetching document: ${source.file_name}, page: ${pageNum}`);
      const data = await getDocumentContent(source.file_name, pageNum);
      console.log('Document content received:', data);
      setContent(data.content);
      setCurrentPage(data.page_number);
      setTotalPages(data.total_pages);
    } catch (err) {
      console.error('Error loading document:', err);
      setError(err.message || 'Impossible de charger le contenu du document');
    } finally {
      setLoading(false);
    }
  }

  function handlePreviousPage() {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  }

  function handleNextPage() {
    if (totalPages && currentPage < totalPages) {
      setCurrentPage(currentPage + 1);
    }
  }

  return (
    <div className="source-viewer-overlay" onClick={onClose}>
      <div className="source-viewer-modal" onClick={(e) => e.stopPropagation()}>
        <div className="source-viewer-header">
          <div className="source-viewer-title">
            <span className="source-viewer-icon">📄</span>
            <div className="source-viewer-meta">
              <h2>{source.file_name}</h2>
              {totalPages && (
                <p className="source-viewer-page-info">
                  Page {currentPage} sur {totalPages}
                </p>
              )}
            </div>
          </div>
          <button className="source-viewer-close" onClick={onClose} aria-label="Fermer">
            ✕
          </button>
        </div>

        <div className="source-viewer-body">
          {loading && (
            <div className="source-viewer-loading">
              <div className="spinner" />
              <p>Chargement du document…</p>
            </div>
          )}

          {error && (
            <div className="source-viewer-error">
              <p>⚠️ {error}</p>
            </div>
          )}

          {content && !loading && (
            <div className="source-viewer-content">
              <pre>{content}</pre>
            </div>
          )}
        </div>

        {totalPages && totalPages > 1 && (
          <div className="source-viewer-footer">
            <button
              className="source-viewer-nav-btn"
              onClick={handlePreviousPage}
              disabled={currentPage <= 1}
              aria-label="Page précédente"
            >
              ← Précédent
            </button>

            <div className="source-viewer-page-selector">
              <input
                type="number"
                min="1"
                max={totalPages}
                value={currentPage}
                onChange={(e) => {
                  const page = Math.max(1, Math.min(totalPages, parseInt(e.target.value) || 1));
                  setCurrentPage(page);
                }}
                aria-label="Numéro de page"
              />
              <span> / {totalPages}</span>
            </div>

            <button
              className="source-viewer-nav-btn"
              onClick={handleNextPage}
              disabled={currentPage >= totalPages}
              aria-label="Page suivante"
            >
              Suivant →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
