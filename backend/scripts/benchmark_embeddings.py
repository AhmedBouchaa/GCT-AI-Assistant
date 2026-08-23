"""Benchmark de modèles d'embeddings multilingues pour RAG."""
import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import time
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.pdf_extractor import PDFExtractor


class EmbeddingBenchmark:
    """Classe pour benchmarking de modèles d'embeddings."""
    
    def __init__(self, documents_dir: str, test_questions_file: str):
        """
        Initialise le benchmark.
        
        Args:
            documents_dir: Répertoire contenant les PDF
            test_questions_file: Fichier JSON avec les questions de test
        """
        self.documents_dir = Path(documents_dir)
        self.test_questions_file = Path(test_questions_file)
        self.models_to_test = [
            {
                "name": "paraphrase-multilingual-MiniLM-L12-v2",
                "size_mb": 420,
                "dimension": 384,
                "use_prefixes": False
            },
            {
                "name": "intfloat/multilingual-e5-large",
                "size_mb": 1340,
                "dimension": 1024,
                "use_prefixes": True
            }
        ]
        self.results = []
    
    def load_documents(self) -> Dict[str, str]:
        """
        Charge tous les documents PDF et extrait leur texte.
        
        Returns:
            Dictionnaire {nom_fichier: texte_extrait}
        """
        extractor = PDFExtractor(str(self.documents_dir))
        extracted = extractor.extract_all_pdfs()
        
        # Combiner toutes les pages d'un même PDF
        documents = {}
        for page in extracted:
            filename = page["filename"]
            if filename not in documents:
                documents[filename] = ""
            documents[filename] += f"\n{page['text']}"
        
        return documents
    
    def load_test_questions(self) -> List[Dict]:
        """
        Charge les questions de test depuis le fichier JSON.
        
        Returns:
            Liste des questions avec leurs PDFs attendus
        """
        with open(self.test_questions_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data["questions"]
    
    def validate_expected_pdfs(self, questions: List[Dict], available_pdfs: List[str]) -> None:
        """
        Valide que chaque expected_pdf correspond à un fichier réel.
        
        Args:
            questions: Liste des questions de test
            available_pdfs: Liste des PDF disponibles dans le répertoire
            
        Raises:
            ValueError: Si un expected_pdf ne correspond à aucun fichier réel
        """
        available_set = set(available_pdfs)
        missing_pdfs = set()
        
        for question in questions:
            expected_pdf = question["expected_pdf"]
            if expected_pdf not in available_set:
                missing_pdfs.add(expected_pdf)
        
        if missing_pdfs:
            raise ValueError(
                f"Les PDF suivants dans expected_pdf n'existent pas dans data/documents/: {missing_pdfs}\n"
                f"PDFs disponibles: {available_pdfs}"
            )
        
        print(f"Validation réussie: tous les expected_pdf correspondent à des fichiers réels.")
    
    def compute_embeddings(self, model_name: str, texts: List[str], use_prefixes: bool = False, prefix: str = "", model=None) -> np.ndarray:
        """
        Calcule les embeddings pour une liste de textes.
        
        Args:
            model_name: Nom du modèle HuggingFace
            texts: Liste de textes à encoder
            use_prefixes: Si True, ajoute le préfixe à chaque texte
            prefix: Préfixe à ajouter ("query: " ou "pass: ")
            model: Instance de modèle déjà chargée (optionnel)
            
        Returns:
            Matrice d'embeddings (n_texts, dimension)
        """
        if model is None:
            print(f"Chargement du modèle {model_name}...")
            model = SentenceTransformer(model_name)
        
        # Ajouter les préfixes si nécessaire (pour les modèles E5)
        if use_prefixes and prefix:
            texts = [f"{prefix}{text}" for text in texts]
            print(f"Préfixe '{prefix}' ajouté à {len(texts)} textes")
        
        print(f"Calcul des embeddings pour {len(texts)} textes...")
        start_time = time.time()
        embeddings = model.encode(texts, show_progress_bar=True)
        elapsed = time.time() - start_time
        
        print(f"Embeddings calculés en {elapsed:.2f}s")
        return embeddings
    
    def compute_recall_at_k(self, 
                          retrieved_docs: List[str], 
                          expected_doc: str, 
                          k: int) -> int:
        """
        Calcule si le document attendu est dans les k premiers résultats.
        
        Args:
            retrieved_docs: Liste des documents récupérés (ordonnés par pertinence)
            expected_doc: Nom du document attendu
            k: Nombre de documents à considérer
            
        Returns:
            1 si trouvé, 0 sinon
        """
        top_k = retrieved_docs[:k]
        return 1 if expected_doc in top_k else 0
    
    def search_similar_documents(self, 
                                query_embedding: np.ndarray,
                                doc_embeddings: np.ndarray,
                                doc_names: List[str],
                                top_k: int = 5) -> Tuple[List[str], List[float]]:
        """
        Recherche les documents les plus similaires à la requête.
        
        Args:
            query_embedding: Embedding de la requête
            doc_embeddings: Embeddings des documents
            doc_names: Noms des documents
            top_k: Nombre de résultats à retourner
            
        Returns:
            Tuple (liste des noms de documents ordonnés par pertinence, liste des scores)
        """
        similarities = cosine_similarity(
            query_embedding.reshape(1, -1), 
            doc_embeddings
        )[0]
        
        # Trier par similarité décroissante
        sorted_indices = np.argsort(similarities)[::-1]
        
        top_indices = sorted_indices[:top_k]
        top_docs = [doc_names[i] for i in top_indices]
        top_scores = [similarities[i] for i in top_indices]
        
        return top_docs, top_scores
    
    def benchmark_model(self, model_info: Dict, 
                       documents: Dict[str, str],
                       questions: List[Dict]) -> Dict:
        """
        Effectue le benchmark pour un modèle donné.
        
        Args:
            model_info: Informations sur le modèle
            documents: Dictionnaire {nom_fichier: texte}
            questions: Liste des questions de test
            
        Returns:
            Résultats du benchmark
        """
        print(f"\n{'='*60}")
        print(f"BENCHMARK: {model_info['name']}")
        print(f"{'='*60}")
        
        # Préparer les textes
        doc_names = list(documents.keys())
        doc_texts = list(documents.values())
        question_texts = [q["question"] for q in questions]
        
        # Calculer les embeddings avec préfixes si nécessaire (E5)
        use_prefixes = model_info["use_prefixes"]
        
        # Charger le modèle une seule fois
        print(f"Chargement du modèle {model_info['name']}...")
        model = SentenceTransformer(model_info["name"])
        
        doc_embeddings = self.compute_embeddings(
            model_info["name"], 
            doc_texts,
            use_prefixes=use_prefixes,
            prefix="pass: " if use_prefixes else "",
            model=model
        )
        query_embeddings = self.compute_embeddings(
            model_info["name"], 
            question_texts,
            use_prefixes=use_prefixes,
            prefix="query: " if use_prefixes else "",
            model=model
        )
        
        # Évaluer chaque question
        recall_at_1_scores = []
        recall_at_3_scores = []
        recall_at_5_scores = []
        reciprocal_ranks = []
        
        # Pour E5-large, afficher les détails détaillés
        show_details = model_info["name"] == "intfloat/multilingual-e5-large"
        
        # Statistiques de position pour E5-large
        position_stats = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, "not_found": 0}
        
        # Stocker les détails pour l'analyse de difficulté
        question_details = []
        
        for i, question in enumerate(questions):
            query_emb = query_embeddings[i]
            expected_pdf = question["expected_pdf"]
            
            # Recherche de documents similaires avec scores
            retrieved, scores = self.search_similar_documents(
                query_emb, 
                doc_embeddings, 
                doc_names, 
                top_k=5
            )
            
            # Calcul des scores
            recall_1 = self.compute_recall_at_k(retrieved, expected_pdf, k=1)
            recall_3 = self.compute_recall_at_k(retrieved, expected_pdf, k=3)
            recall_5 = self.compute_recall_at_k(retrieved, expected_pdf, k=5)
            
            recall_at_1_scores.append(recall_1)
            recall_at_3_scores.append(recall_3)
            recall_at_5_scores.append(recall_5)
            
            if show_details:
                print(f"\nQ{i+1}")
                print(f"Question: {question['question']}")
                print(f"Expected: {expected_pdf}")
                print(f"\nTop 5:")
                
                # Trouver la position du document attendu
                expected_position = None
                expected_score = None
                for j, (doc, score) in enumerate(zip(retrieved, scores)):
                    if doc == expected_pdf:
                        expected_position = j + 1
                        expected_score = score
                        break
                
                best_score = scores[0] if scores else 0.0
                score_gap = best_score - expected_score if expected_score is not None else None
                
                # Calculer le reciprocal rank
                if expected_position:
                    rr = 1.0 / expected_position
                    reciprocal_ranks.append(rr)
                    position_stats[expected_position] += 1
                else:
                    rr = 0.0
                    reciprocal_ranks.append(rr)
                    position_stats["not_found"] += 1
                
                # Stocker les détails
                question_details.append({
                    "id": i + 1,
                    "question": question['question'],
                    "expected_pdf": expected_pdf,
                    "rank": expected_position,
                    "expected_score": expected_score,
                    "best_score": best_score,
                    "score_gap": score_gap,
                    "top_5": list(zip(retrieved, scores))
                })
                
                for j, (doc, score) in enumerate(zip(retrieved, scores)):
                    marker = " ✓" if doc == expected_pdf else ""
                    print(f"{j+1}. {doc} — score: {score:.4f}{marker}")
                
                if expected_position:
                    print(f"\nPosition du document attendu: {expected_position}")
                else:
                    print(f"\nPosition du document attendu: Non trouvé dans le Top 5")
                
                # Analyse de difficulté
                print(f"\nAnalyse de difficulté:")
                print(f"  Rang: {expected_position if expected_position else 'N/A'}")
                expected_score_str = f"{expected_score:.4f}" if expected_score is not None else 'N/A'
                score_gap_str = f"{score_gap:.4f}" if score_gap is not None else 'N/A'
                print(f"  Score attendu: {expected_score_str}")
                print(f"  Meilleur score: {best_score:.4f}")
                print(f"  Écart: {score_gap_str}")
            else:
                print(f"Q{i+1}: {question['question'][:30]}... | "
                      f"Attendu: {expected_pdf} | "
                      f"R@1: {recall_1} | R@3: {recall_3}")
        
        if show_details:
            print(f"\n{'='*60}")
            print("STATISTIQUES DE POSITION")
            print(f"{'='*60}")
            print(f"Position 1: {position_stats[1]} questions")
            print(f"Position 2: {position_stats[2]} questions")
            print(f"Position 3: {position_stats[3]} questions")
            print(f"Position 4: {position_stats[4]} questions")
            print(f"Position 5: {position_stats[5]} questions")
            print(f"Non trouvé dans Top 5: {position_stats['not_found']} questions")
            
            # Recalcul des métriques à partir des positions réelles
            print(f"\n{'='*60}")
            print("MÉTRIQUES RECALCULÉES")
            print(f"{'='*60}")
            
            # Recall@1: nombre de questions en position 1 / total
            recalculated_r1 = position_stats[1] / len(questions)
            print(f"Recall@1 = {position_stats[1]}/{len(questions)} = {recalculated_r1:.4f}")
            
            # Recall@3: nombre de questions en position 1-3 / total
            recalculated_r3 = (position_stats[1] + position_stats[2] + position_stats[3]) / len(questions)
            print(f"Recall@3 = ({position_stats[1]}+{position_stats[2]}+{position_stats[3]})/{len(questions)} = {recalculated_r3:.4f}")
            
            # Recall@5: nombre de questions en position 1-5 / total
            recalculated_r5 = (position_stats[1] + position_stats[2] + position_stats[3] + position_stats[4] + position_stats[5]) / len(questions)
            print(f"Recall@5 = ({position_stats[1]}+{position_stats[2]}+{position_stats[3]}+{position_stats[4]}+{position_stats[5]})/{len(questions)} = {recalculated_r5:.4f}")
            
            # MRR: moyenne des reciprocal ranks
            mrr = np.mean(reciprocal_ranks)
            print(f"MRR = moyenne(1/rank) = {mrr:.4f}")
            print(f"\nFormule MRR: (1/{' + 1/'.join([str(r) for r in reciprocal_ranks if r > 0])})/{len(reciprocal_ranks)}")
        
        # Calculer les moyennes (avec gestion des tableaux vides)
        avg_recall_1 = np.mean(recall_at_1_scores) if recall_at_1_scores else 0.0
        avg_recall_3 = np.mean(recall_at_3_scores) if recall_at_3_scores else 0.0
        avg_recall_5 = np.mean(recall_at_5_scores) if recall_at_5_scores else 0.0
        avg_mrr = np.mean(reciprocal_ranks) if reciprocal_ranks else 0.0
        
        result = {
            "model_name": model_info["name"],
            "model_size_mb": model_info["size_mb"],
            "dimension": model_info["dimension"],
            "recall_at_1": avg_recall_1,
            "recall_at_3": avg_recall_3,
            "recall_at_5": avg_recall_5,
            "mrr": avg_mrr,
            "total_questions": len(questions),
            "question_details": question_details if show_details else None
        }
        
        self.results.append(result)
        return result
    
    def run_full_benchmark(self) -> None:
        """Exécute le benchmark complet sur tous les modèles."""
        print("Chargement des documents...")
        documents = self.load_documents()
        print(f"{len(documents)} documents chargés")
        
        print("Chargement des questions de test...")
        questions = self.load_test_questions()
        print(f"{len(questions)} questions chargées")
        
        if not questions:
            print("ATTENTION: Aucune question de test définie.")
            print("Veuillez remplir data/test_questions.json avec des questions basées sur le contenu réel des PDF.")
            print("Utilisez data/test_questions_template.json comme modèle.")
            return
        
        # Valider les expected_pdf
        available_pdfs = list(documents.keys())
        self.validate_expected_pdfs(questions, available_pdfs)
        
        for model_info in self.models_to_test:
            try:
                self.benchmark_model(model_info, documents, questions)
            except Exception as e:
                print(f"Erreur avec {model_info['name']}: {e}")
        
        self.print_summary()
    
    def print_summary(self) -> None:
        """Affiche le tableau comparatif final."""
        print(f"\n{'='*80}")
        print("TABLEAU COMPARATIF FINAL")
        print(f"{'='*80}")
        print(f"{'Modèle':<45} {'Taille':<10} {'Dim':<6} {'R@1':<8} {'R@3':<8} {'R@5':<8} {'MRR':<8}")
        print("-" * 80)
        
        for result in self.results:
            print(f"{result['model_name']:<45} "
                  f"{result['model_size_mb']:<10} "
                  f"{result['dimension']:<6} "
                  f"{result['recall_at_1']:.3f}   "
                  f"{result['recall_at_3']:.3f}   "
                  f"{result['recall_at_5']:.3f}   "
                  f"{result['mrr']:.3f}")
        
        print("-" * 80)
        
        # Recommandation prudente
        print(f"\nCONCLUSION PRUDENTE:")
        print(f"Les résultats sont basés sur le jeu de questions actuel.")
        print(f"Pour une conclusion définitive, il est recommandé d'utiliser un jeu de questions plus discriminant.")
        
        if self.results:
            best_model = max(self.results, key=lambda x: x["recall_at_3"])
            print(f"\nSur la base du benchmark actuel: {best_model['model_name']}")
            print(f"Meilleur Recall@3: {best_model['recall_at_3']:.3f}")


def main():
    """Point d'entrée principal."""
    documents_dir = Path(__file__).parent.parent / "data" / "documents"
    test_questions_file = Path(__file__).parent.parent / "data" / "test_questions_v2.json"
    
    benchmark = EmbeddingBenchmark(str(documents_dir), str(test_questions_file))
    benchmark.run_full_benchmark()


if __name__ == "__main__":
    main()
