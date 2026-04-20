import logging
import sys
import os
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.lancedb import LanceDb, SearchType
import gradio as gr
import fitz  # PyMuPDF
from PIL import Image
import io
import requests
import re

# --- Logging ---
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Secrets ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY")

# Create a knowledge base with PDF documents
knowledge = Knowledge(
    vector_db=LanceDb(
        uri="tmp/lancedb",
        table_name="pdf_documents",
        search_type=SearchType.vector,  # Changed to vector to avoid tantivy dependency
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    )
)

# Download and add PDFs to knowledge base
pdf_urls = [
    "https://media.datacamp.com/cms/working-with-hugging-face.pdf",
    "https://media.datacamp.com/cms/ai-agents-cheat-sheet.pdf",
    "https://media.datacamp.com/cms/introduction-to-sql-with-ai-1.pdf",
    "https://media.datacamp.com/legacy/image/upload/v1719844709/Marketing/Blog/Azure_CLI_Cheat_Sheet.pdf"
]

def download_if_needed(url, filename):
    if not os.path.exists(filename):
        logger.info(f"Downloading {url}...")
        response = requests.get(url)
        with open(filename, "wb") as f:
            f.write(response.content)
        logger.info(f"Downloaded {filename} ({len(response.content)} bytes)")

# Create a directory for PDFs if it doesn't exist
os.makedirs("pdf_cache", exist_ok=True)

# Method 1: Try using knowledge.add_content (newer agno versions)
def add_pdfs_to_knowledge():
    """Add PDFs to knowledge base using the correct method for the installed agno version"""
    contents_to_add = []
    
    for i, url in enumerate(pdf_urls):
        filename = f"pdf_cache/file_{i}.pdf"
        try:
            download_if_needed(url, filename)
            contents_to_add.append({
                "path": filename,
                "metadata": {"source": url}
            })
            logger.info(f"Prepared PDF {i+1}: {url}")
        except Exception as e:
            logger.error(f"Failed to prepare PDF {i+1}: {str(e)}")
    
    if contents_to_add:
        try:
            # Try the new method first
            if hasattr(knowledge, 'add_contents'):
                knowledge.add_contents(contents_to_add)
                logger.info(f"✅ Successfully added {len(contents_to_add)} PDFs using add_contents")
            elif hasattr(knowledge, 'add_content'):
                for item in contents_to_add:
                    knowledge.add_content(**item)
                logger.info(f"✅ Successfully added {len(contents_to_add)} PDFs using add_content")
            else:
                # Fallback: Direct vector DB insertion
                from agno.document.reader.pdf_reader import PDFReader
                reader = PDFReader()
                all_docs = []
                for item in contents_to_add:
                    docs = reader.read(item["path"])
                    for doc in docs:
                        doc.metadata = item["metadata"]
                        all_docs.append(doc)
                knowledge.vector_db.insert(documents=all_docs)
                logger.info(f"✅ Successfully added {len(all_docs)} document chunks from {len(contents_to_add)} PDFs")
        except Exception as e:
            logger.error(f"Failed to add PDFs: {str(e)}")
            raise
    else:
        logger.warning("No PDFs were prepared to add")

# Add PDFs to knowledge base
add_pdfs_to_knowledge()

# Define the agent
agent = Agent(
    model=OpenAIChat(id="gpt-4.1-mini", temperature=0.2),
    description="You are Dox a data expert!",
    instructions="""
    You are a data professional's assistant named Dox.

    Your primary goal is to answer questions about data, programming, cloud computing, AI/ML, and technology topics.

    Here are your operating procedures:

    1.  **Information Gathering Strategy**:
        *   **Prioritize Knowledge Base**: First, search your internal knowledge base for the answer.
        *   **Supplement with Web Search**: If the knowledge base information is outdated, insufficient, or the question is better suited for current web information, use the DuckDuckGo tool to perform web searches to fill in gaps or find the most up-to-date data.
        *   For general technology questions not in your knowledge base, use web search to provide accurate answers.
        *   If the question is NOT data-related, you MUST respond with: "Please ask relevant data questions only." and terminate.

    2.  **Response Length Guidelines**:
        *   For basic questions, keep your answer to a maximum of 300 words.
        *   For complex questions, extend your answer to a maximum of 500 words.

    3.  **Citation Rules (CRITICAL)**:
        *   **Knowledge Base Citation**: For any information sourced from your internal knowledge base, you MUST include a citation on a NEW LINE after the answer, starting with "Source: ", followed by the metadata field 'source' to get the hyperlink.
        *   **Web Search Citation**: For any information obtained from the web using the DuckDuckGo tool, you MUST include a citation on a NEW LINE after the answer, starting with "Online Source: ", followed by the full hyperlink.
        *   **Final Rule for Citations**: Always end your answers with the appropriate citations, ensuring they are on separate lines as specified. Do NOT mix or combine citation types on a single line.
        *   ALWAYS cite with links NOT text like "from internal knowledge base"

    4.  **Accuracy and Non-Hallucination**:
        *   Provide factual and relevant answers based ONLY on the information found in your knowledge base or through web searches.
        *   NEVER invent or hallucinate information. If an answer cannot be found, state that directly.

    Make sure to follow these instructions precisely.
    """,
    knowledge=knowledge,
    add_datetime_to_context=True,
    add_location_to_context=True,
    search_knowledge=True,
    tools=[DuckDuckGoTools()],
    markdown=True
)

logger.info("Agent initialized successfully")

# -----------------------------
# Your agent function
# -----------------------------
def ask_agent(question):
    logger.info(f"Question asked: {question[:100]}...")
    response = agent.run(question, use_knowledge=True)
    full_content = response.get_content_as_string()

    # Extract PDF URL from response
    match = re.search(r'https?://[^\s]+\.pdf', full_content, re.IGNORECASE)
    link = match.group(0) if match else None
    
    if link:
        logger.info(f"PDF link found: {link}")
    else:
        logger.info("No PDF link found in response")

    return full_content, link

# -----------------------------
# Download PDF
# -----------------------------
def download_pdf_from_url(url):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.content

# -----------------------------
# Display PDF
# -----------------------------
def display_pdf(pdf_url):
    if not pdf_url:
        return gr.update(visible=False)
    
    try:
        logger.info(f"Displaying PDF from: {pdf_url}")
        pdf_bytes = download_pdf_from_url(pdf_url)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[0]
        
        zoom = 1.5
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        doc.close()
        
        logger.info("PDF displayed successfully")
        return gr.update(value=img, visible=True)
    except Exception as e:
        logger.error(f"Error displaying PDF: {str(e)}")
        return gr.update(value=None, visible=False)

# -----------------------------
# UI Wrapper for Blocks
# -----------------------------
def ask_agent_ui(question):
    response_text, link = ask_agent(question)
    
    return (
        response_text,
        link,
        gr.update(visible=link is not None),  # button visibility
        gr.update(value=None, visible=False)  # RESET PDF preview
    )

# -----------------------------
# Combined Gradio UI with Blocks and Interface
# -----------------------------
with gr.Blocks(title="# 🌊 Dox the Data Professional's Advisor 🤖", theme=gr.themes.Ocean()) as demo:
    gr.Markdown("# 🌊 Dox the Data Professional's Advisor 🤖")
    gr.Markdown("🧠 Dox has 4 DataCamp cheat sheets in its database that you could ask about (1️⃣ Hugging Face | 2️⃣ AI Agents | 3️⃣ SQL with AI | 4️⃣ Azure CLI):")
    
    # Create two columns for better layout
    with gr.Row():
        with gr.Column(scale=2):
            question = gr.Textbox(
                label="Ask Dox a question:",
                lines=2,
                placeholder="Type your question here..."
            )
            
            # Add examples
            gr.Examples(
                examples=[
                    "How do you log into Azure using device code authentication?",
                    "What are the three main components of an AI agent?",
                    "What are the \"core four\" Hugging Face libraries?",
                    "What SQL clause is used to filter data after grouping?"
                ],
                inputs=question,
                label="Example Questions"
            )
            
            ask_btn = gr.Button("Submit", variant="primary")
            
            answer = gr.Markdown(
                label="Answer: ",
                render=True,
                container=True,
                elem_id="answer_markdown"
            )
            
        with gr.Column(scale=2):
            link_state = gr.State()
            show_btn = gr.Button("Show PDF", visible=False, variant="secondary")
            output_image = gr.Image(label="PDF Preview (Page 1)", visible=False)
    
    # Ask agent functionality
    ask_btn.click(
        ask_agent_ui,
        inputs=question,
        outputs=[answer, link_state, show_btn, output_image]
    )
    
    # Show PDF functionality
    show_btn.click(
        display_pdf,
        inputs=link_state,
        outputs=output_image
    ).then(
        lambda: gr.update(visible=True),
        None,
        output_image
    )

if __name__ == "__main__":
    demo.launch()
