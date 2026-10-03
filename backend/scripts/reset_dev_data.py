import sqlite3
import os

DB_PATH = os.path.join("data", "metadata", "gap_finder_dev.db")
FAISS_PATH = os.path.join("data", "embeddings", "faiss_index.bin")
VECTOR_META_PATH = os.path.join("data", "embeddings", "vector_metadata.json")
RAW_PDF_DIR = os.path.join("data", "raw")

def reset_all_data():
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        tables = [
            "paper_topic_assignments",
            "discovered_topics",
            "evidence_embeddings",
            "scientific_extractions",
            "scientific_sentences",
            "research_gaps",
            "paper_references",
            "paper_sections",
            "papers",
        ]
        for tbl in tables:
            try:
                c.execute(f"DELETE FROM {tbl};")
            except Exception as e:
                print(f"Skipping {tbl}: {e}")
        conn.commit()
        conn.close()
        print("Cleared all SQLite database tables.")

    # Reset vector index
    if os.path.exists(FAISS_PATH):
        try:
            os.remove(FAISS_PATH)
            print("Removed FAISS index.")
        except Exception as e:
            print(f"Error removing FAISS index: {e}")

    if os.path.exists(VECTOR_META_PATH):
        try:
            os.remove(VECTOR_META_PATH)
            print("Removed vector metadata.")
        except Exception as e:
            print(f"Error removing vector metadata: {e}")

    # Remove temporary raw PDFs
    if os.path.exists(RAW_PDF_DIR):
        for f in os.listdir(RAW_PDF_DIR):
            if f.endswith(".pdf"):
                try:
                    os.remove(os.path.join(RAW_PDF_DIR, f))
                    print(f"Removed raw PDF: {f}")
                except Exception as e:
                    print(f"Error removing {f}: {e}")

    print("All dev/test mock and residual data successfully cleared.")

if __name__ == "__main__":
    reset_all_data()
