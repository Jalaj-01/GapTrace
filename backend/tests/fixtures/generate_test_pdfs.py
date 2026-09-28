"""Utility to programmatically create realistic scientific PDFs for unit & integration testing."""

from pathlib import Path
import fitz  # PyMuPDF

FIXTURES_DIR = Path(__file__).parent


def create_sample_scientific_pdf(output_path: Path) -> Path:
    """Creates a multi-page realistic scientific paper PDF with title, abstract, sections, and references."""
    doc = fitz.open()

    # --- PAGE 1 ---
    page1 = doc.new_page(width=595, height=842)  # A4 size

    # Header / Meta
    page1.insert_text(fitz.Point(50, 40), "Proceedings of the International NLP Conference (Published 2024)", fontsize=8, color=(0.4, 0.4, 0.4))
    page1.insert_text(fitz.Point(400, 40), "DOI: 10.48550/arXiv.1706.03762", fontsize=8, color=(0.4, 0.4, 0.4))

    # Title (Large prominent font)
    title_text = "Attention Is All You Need: Discovering Research Gaps in Neural Sequence Models"
    page1.insert_text(fitz.Point(50, 90), title_text, fontsize=15, color=(0, 0, 0))

    # Authors
    authors_text = "Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit"
    page1.insert_text(fitz.Point(50, 120), authors_text, fontsize=10, color=(0.2, 0.2, 0.2))
    page1.insert_text(fitz.Point(50, 135), "Google Brain & Google Research - contact@google.ai", fontsize=8, color=(0.4, 0.4, 0.4))

    # Abstract
    page1.insert_text(fitz.Point(50, 170), "Abstract", fontsize=11, color=(0, 0, 0))
    abstract_p = (
        "The dominant sequence transduction models are based on complex recurrent or convolutional neural "
        "networks in an encoder-decoder configuration. In this paper, we propose the Transformer, an architecture "
        "eschewing recurrence and relying entirely on an attention mechanism to draw global dependencies between "
        "input and output. The Transformer allows for significantly more parallelization and establishes a new "
        "state of the art in machine translation quality."
    )
    rect_abstract = fitz.Rect(50, 185, 545, 260)
    page1.insert_textbox(rect_abstract, abstract_p, fontsize=9, color=(0.1, 0.1, 0.1))

    # Section 1: Introduction
    page1.insert_text(fitz.Point(50, 280), "1. Introduction", fontsize=12, color=(0, 0, 0))
    intro_p1 = (
        "Recurrent neural networks, long short-term memory, and gated recurrent networks have been firmly established "
        "as state-of-the-art approaches in sequential language modeling and sequence transduction such as neural "
        "machine translation. Recurrent models typically factor computation along the symbol positions of the input "
        "and output sequences. Aligning positions to steps in computation time precludes parallelization within "
        "training examples, which becomes critical at longer sequence lengths."
    )
    rect_intro1 = fitz.Rect(50, 295, 545, 390)
    page1.insert_textbox(rect_intro1, intro_p1, fontsize=9.5, color=(0, 0, 0))

    intro_p2 = (
        "Attention mechanisms have become an integral part of compelling sequence modeling and transduction models "
        "in various tasks, allowing modeling of dependencies without regard to their distance in the input or output "
        "sequences. In this work we propose the Transformer, a model architecture eschewing recurrence."
    )
    rect_intro2 = fitz.Rect(50, 400, 545, 490)
    page1.insert_textbox(rect_intro2, intro_p2, fontsize=9.5, color=(0, 0, 0))

    # Section 2: Methodology
    page1.insert_text(fitz.Point(50, 510), "2. Methodology", fontsize=12, color=(0, 0, 0))
    method_p1 = (
        "The Transformer follows an overall encoder-decoder architecture using stacked self-attention and point-wise, "
        "fully connected layers for both the encoder and decoder. The encoder is composed of a stack of N = 6 "
        "identical layers. Each layer has two sub-layers: a multi-head self-attention mechanism and a position-wise "
        "feed-forward network. We employ residual connections around each of the sub-layers followed by layer normalization."
    )
    rect_method = fitz.Rect(50, 525, 545, 640)
    page1.insert_textbox(rect_method, method_p1, fontsize=9.5, color=(0, 0, 0))

    page1.insert_text(fitz.Point(280, 810), "1", fontsize=9, color=(0.4, 0.4, 0.4))

    # --- PAGE 2 ---
    page2 = doc.new_page(width=595, height=842)

    # Section 3: Limitations
    page2.insert_text(fitz.Point(50, 60), "3. Limitations", fontsize=12, color=(0, 0, 0))
    limitations_p = (
        "While self-attention allows for full sequence parallelization, its computational complexity scales "
        "quadratically O(N^2) with respect to input context length. This limitation presents a major bottleneck "
        "for ultra-long scientific document processing and extensive document-level context modeling. Furthermore, "
        "the lack of inherent inductive bias for temporal sequence ordering requires explicit positional encodings, "
        "which can degrade when evaluating on sequences longer than those encountered during training."
    )
    rect_limits = fitz.Rect(50, 75, 545, 175)
    page2.insert_textbox(rect_limits, limitations_p, fontsize=9.5, color=(0, 0, 0))

    # Section 4: Conclusion
    page2.insert_text(fitz.Point(50, 195), "4. Conclusion", fontsize=12, color=(0, 0, 0))
    conclusion_p = (
        "In this work, we presented the Transformer, the first sequence transduction model based entirely on "
        "attention. We plan to extend the Transformer to problems involving input and output modalities other than text, "
        "such as images and audio, and investigate localized attention mechanisms to address long sequences."
    )
    rect_conclusion = fitz.Rect(50, 210, 545, 300)
    page2.insert_textbox(rect_conclusion, conclusion_p, fontsize=9.5, color=(0, 0, 0))

    # Section 5: References
    page2.insert_text(fitz.Point(50, 320), "References", fontsize=12, color=(0, 0, 0))
    ref_text = (
        "[1] Dzmitry Bahdanau, Kyunghyun Cho, and Yoshua Bengio. Neural machine translation by jointly learning to align and translate. In ICLR, 2015.\n\n"
        "[2] Sepp Hochreiter and Jurgen Schmidhuber. Long short-term memory. Neural Computation, 9(8):1735-1780, 1997.\n\n"
        "[3] Ashish Vaswani, Noam Shazeer, Niki Parmar, and Jakob Uszkoreit. Attention is all you need. In NeurIPS, 2017."
    )
    rect_refs = fitz.Rect(50, 335, 545, 480)
    page2.insert_textbox(rect_refs, ref_text, fontsize=8.5, color=(0.1, 0.1, 0.1))

    page2.insert_text(fitz.Point(280, 810), "2", fontsize=9, color=(0.4, 0.4, 0.4))

    doc.save(output_path)
    doc.close()
    return output_path


def create_short_scientific_pdf(output_path: Path) -> Path:
    """Creates a 1-page concise paper PDF."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    page.insert_text(fitz.Point(50, 50), "Empirical Study of Oversmoothing in Citation Graph Neural Networks", fontsize=14, color=(0, 0, 0))
    page.insert_text(fitz.Point(50, 80), "Elena Rostova, David Miller - Oxford University (2025)", fontsize=10, color=(0.3, 0.3, 0.3))

    page.insert_text(fitz.Point(50, 120), "Abstract", fontsize=11, color=(0, 0, 0))
    page.insert_textbox(fitz.Rect(50, 135, 545, 195), "Graph neural networks on dense citation networks experience exponential feature similarity decay when layer depth increases beyond threshold K=4.", fontsize=9)

    page.insert_text(fitz.Point(50, 220), "1. Introduction", fontsize=12, color=(0, 0, 0))
    page.insert_textbox(fitz.Rect(50, 235, 545, 330), "Analyzing scientific literature using graph representations has revolutionized bibliometrics. However, multi-hop aggregation introduces severe representation collapse.", fontsize=9.5)

    page.insert_text(fitz.Point(50, 355), "2. Limitations", fontsize=12, color=(0, 0, 0))
    page.insert_textbox(fitz.Rect(50, 370, 545, 460), "Our experiments are strictly limited to homogeneous citation graphs and do not generalize to heterogeneous author-institution networks.", fontsize=9.5)

    page.insert_text(fitz.Point(50, 485), "References", fontsize=12, color=(0, 0, 0))
    page.insert_textbox(fitz.Rect(50, 500, 545, 580), "[1] Thomas N. Kipf and Max Welling. Semi-supervised classification with graph convolutional networks. ICLR 2017.", fontsize=8.5)

    doc.save(output_path)
    doc.close()
    return output_path


def create_corrupted_pdf(output_path: Path) -> Path:
    """Creates an invalid/corrupted PDF file."""
    output_path.write_bytes(b"%PDF-1.4\n%Broken binary content\x00\xff\xeeNOT_A_VALID_XREF_TABLE")
    return output_path


def create_text_file(output_path: Path) -> Path:
    """Creates a non-pdf file for format validation testing."""
    output_path.write_text("This is a plain text file, not a PDF.")
    return output_path


def generate_all_fixtures():
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    sample_pdf = FIXTURES_DIR / "sample_paper.pdf"
    short_pdf = FIXTURES_DIR / "sample_paper_short.pdf"
    corrupt_pdf = FIXTURES_DIR / "corrupted_paper.pdf"
    txt_file = FIXTURES_DIR / "invalid_file.txt"

    create_sample_scientific_pdf(sample_pdf)
    create_short_scientific_pdf(short_pdf)
    create_corrupted_pdf(corrupt_pdf)
    create_text_file(txt_file)

    print(f"Generated sample PDF fixtures at: {FIXTURES_DIR}")


if __name__ == "__main__":
    generate_all_fixtures()
