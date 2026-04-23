# Import necessary libraries for logging, system operations, and file handling.
import logging
import sys
import os

# Import core components from the 'agno' library for building the agent.
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.lancedb import LanceDb, SearchType

# Import Gradio for creating the web user interface.
import gradio as gr

# Import libraries for handling PDFs and images.
import fitz  # PyMuPDF, used for PDF processing.
from PIL import Image # Pillow library for image manipulation.
import io # Used to handle in-memory binary streams.
import requests # For making HTTP requests to download files.
import re # Regular expressions for searching text patterns.

# Configure basic logging to output messages to the console.
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
# Get a logger instance for this script.
logger = logging.getLogger(__name__)

# Retrieve the OpenAI API key from environment variables.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
# If the API key is not found, raise an error.
if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY")

# Initialize the Knowledge Base for the agent.
knowledge = Knowledge(
    # Use LanceDB as the vector database to store and search document embeddings.
    vector_db=LanceDb(
        uri="tmp/lancedb", # Directory to store the database.
        table_name="pdf_documents", # Name of the table within the database.
        search_type=SearchType.vector, # Use vector search for finding relevant documents.
        # Use OpenAI's embedding model to convert text into numerical vectors.
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    )
)

# A list of URLs pointing to PDF documents that will be added to the knowledge base.
pdf_urls = [
    "https://media.datacamp.com/cms/working-with-hugging-face.pdf",
    "https://media.datacamp.com/cms/ai-agents-cheat-sheet.pdf",
    "https://media.datacamp.com/cms/introduction-to-sql-with-ai-1.pdf",
    "https://media.datacamp.com/legacy/image/upload/v1719844709/Marketing/Blog/Azure_CLI_Cheat_Sheet.pdf",
    "https://s3.amazonaws.com/assets.datacamp.com/email/other/Power+BI_Cheat+Sheet.pdf",
    "https://media.datacamp.com/cms/python-basics-cheat-sheet-v4.pdf"
]

# Defines a function to download a file from a URL if it doesn't already exist locally.
def download_if_needed(url, filename):
    # Check if the file path does not exist.
    if not os.path.exists(filename):
        logger.info(f"Downloading {url}...")
        # Send an HTTP GET request to the URL.
        response = requests.get(url)
        # Open the local file in write-binary mode.
        with open(filename, "wb") as f:
            # Write the content of the response to the file.
            f.write(response.content)
        logger.info(f"Downloaded {filename} ({len(response.content)} bytes)")

# Create a directory named 'pdf_cache' to store downloaded PDF files.
# 'exist_ok=True' prevents an error if the directory already exists.
os.makedirs("pdf_cache", exist_ok=True)

# Defines a function to add the specified PDFs to the agent's knowledge base.
def add_pdfs_to_knowledge():
    """Add PDFs to knowledge base using the correct method for the installed agno version"""
    # Create an empty list to hold information about the content to be added.
    contents_to_add = []
    
    # Loop through the list of PDF URLs with their index.
    for i, url in enumerate(pdf_urls):
        # Define a local filename for the cached PDF.
        filename = f"pdf_cache/file_{i}.pdf"
        try:
            # Download the PDF if it's not already in the cache.
            download_if_needed(url, filename)
            # Prepare a dictionary with the file path and metadata (source URL).
            contents_to_add.append({
                "path": filename,
                "metadata": {"source": url}
            })
            logger.info(f"Prepared PDF {i+1}: {url}")
        except Exception as e:
            # Log an error if the PDF preparation fails.
            logger.error(f"Failed to prepare PDF {i+1}: {str(e)}")
    
    # Proceed only if there are PDFs to add.
    if contents_to_add:
        try:
            # This block checks for the correct method to add documents based on the 'agno' library version.
            # Check if the 'add_contents' method (for batch processing) exists.
            if hasattr(knowledge, 'add_contents'):
                knowledge.add_contents(contents_to_add)
                logger.info(f"✅ Successfully added {len(contents_to_add)} PDFs using add_contents")
            # Else, check if the 'add_content' method (for single item processing) exists.
            elif hasattr(knowledge, 'add_content'):
                for item in contents_to_add:
                    knowledge.add_content(**item)
                logger.info(f"✅ Successfully added {len(contents_to_add)} PDFs using add_content")
            # As a fallback for older versions, manually read and insert the documents.
            else:
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
            # Log and re-raise any exception that occurs during the addition process.
            logger.error(f"Failed to add PDFs: {str(e)}")
            raise
    else:
        # Warn if no PDFs were prepared.
        logger.warning("No PDFs were prepared to add")

# Call the function to load the PDFs into the knowledge base.
add_pdfs_to_knowledge()

# Initialize the AI agent with its configuration.
agent = Agent(
    # Set the underlying language model to OpenAI's GPT-4.1-mini with low temperature for more predictable responses.
    model=OpenAIChat(id="gpt-4.1-mini", temperature=0.2),
    # Give the agent a name/description.
    description="You are Dox a data expert!",
    # Provide detailed instructions (the "system prompt") that govern the agent's behavior.
    instructions="""
    You are a data professional's assistant named Dox.
    Your primary goal is to answer questions about data, programming, cloud computing, AI/ML, and technology topics.
    Here are your operating procedures:
    1.  **Information Gathering Strategy**:
        *   **Prioritize Knowledge Base**: First, search your internal knowledge base for the answer.
        *   **Supplement with Web Search**: If the knowledge base information is outdated, insufficient, or the question is better suited for current web information, use the DuckDuckGo tool to perform web searches to fill in gaps or find the most up-to-date data.
        *   For general technology questions not in your knowledge base, use web search to provide accurate answers.
        *   If the question is asking for the "latest" or "most recent" of a data-related topic, always use web search and datetime to context.
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
    # Link the agent to the knowledge base created earlier.
    knowledge=knowledge,
    # Automatically add the current date and time to the agent's context.
    add_datetime_to_context=True,
    # Automatically add the user's location to the context (if available).
    add_location_to_context=True,
    # Enable the agent to search its knowledge base by default.
    search_knowledge=True,
    # Equip the agent with tools, in this case, the ability to search the web using DuckDuckGo.
    tools=[DuckDuckGoTools()],
    # Enable markdown formatting in the agent's output.
    markdown=True
)

# Log a success message indicating the agent is ready.
logger.info("🟢 Agent initialized successfully!")

# Defines a function to process a user's question.
def ask_agent(question):
    logger.info(f"Question asked: {question[:100]}...")
    try:
        # Run the agent with the user's question, ensuring it uses its knowledge base.
        response = agent.run(question, use_knowledge=True)
        # Get the agent's response as a single string.
        full_content = response.get_content_as_string()
    except Exception as e:
        logger.error(str(e))
        return "❌ Something went wrong. Please try again.", None
    # Use a regular expression to find the first URL ending in '.pdf' in the response.
    match = re.search(r'https?://[^\s]+\.pdf', full_content, re.IGNORECASE)
    # Extract the link if a match is found, otherwise set it to None.
    link = match.group(0) if match else None
    
    if link:
        logger.info(f"PDF link found: {link}")
    else:
        logger.info("🔴 No PDF link found in response")
    # Return the full text response and the extracted PDF link.
    # full_content += "\n\n---\n**🔍 Try asking:**\n- Give me a real example...\n- Explain step by step...\n- Compare with alternatives..."
    full_content += "\n\n---\n**📋 Dox would appreciate your feedback! ⬇️**"
    return full_content, link

# Defines a function to download the raw content of a PDF from a URL.
def download_pdf_from_url(url):
    # Make an HTTP GET request with a timeout.
    response = requests.get(url, timeout=30)
    # Raise an exception if the request was not successful (e.g., 404 error).
    response.raise_for_status()
    # Return the binary content of the PDF.
    return response.content

# A Gradio helper function to update the UI while a PDF is being prepared for display.
def prepare_pdf_loading(link):
    # If a link exists, show a "Loading..." message.
    if link:
        return gr.update(value="📄 Loading PDF preview...", visible=True)
    # Otherwise, hide the message.
    return gr.update(value="❌ No PDF for preview", visible=True)

# Defines a function to display the first page of a PDF as an image.
def display_pdf(pdf_url):
    # If no URL is provided, hide the image and status components in the UI.
    if not pdf_url:
        return (
            gr.update(value=None, visible=False),
            gr.update(value="", visible=False)
        )
    try:
        # Download the PDF content from the URL.
        pdf_bytes = download_pdf_from_url(pdf_url)
        # Open the PDF from the in-memory bytes.
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        # Get the first page of the document.
        page = doc[0]
        # Create a transformation matrix to render the page at a higher resolution.
        zoom = 1.5
        mat = fitz.Matrix(zoom, zoom)
        # Get a pixmap (a raster image) of the page.
        pix = page.get_pixmap(matrix=mat)
        # Convert the pixmap to a PNG image using PIL.
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        # Close the PDF document to free up resources.
        doc.close()
        # Return the image to be displayed in the UI and hide any status messages.
        return (
            gr.update(value=img, visible=True),
            gr.update(value="", visible=False)
        )
    except Exception as e:
        # If an error occurs, log it and display a failure message in the UI.
        logger.error(f"PDF error: {e}")
        return (
            gr.update(value=None, visible=False),
            gr.update(value="❌ Failed to load PDF", visible=True)
        )

theme = gr.themes.Ocean(
    font=[gr.themes.GoogleFont("Inter"), "Segoe UI", "sans-serif"],
    font_mono=[gr.themes.GoogleFont("Fira Code"), "monospace"]
)

demo_css = """
.chatbot {
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
    font-size: 12px !important;
}

.chatbot .message code,
.chatbot .message pre {
    font-size: 12px !important;
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
}

.component {
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
    font-size: 12px !important;
}

.gradio-container .examples {
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
    font-size: 12px !important;
}
"""

# Create the Gradio interface using `gr.Blocks` for a custom layout.
with gr.Blocks(
    title="# 🤖 Dox the Data Professional's Advisor 🤖",
    theme=theme,
    css=demo_css,
    fill_width=True
) as demo:
    # Add titles and descriptions using Markdown.
    gr.Markdown("# 🤖 Dox the Data Professional's Advisor 🤖")
    gr.Markdown("### 🧠 Dox is an expert in the following topics: \n1️⃣ Hugging Face | 2️⃣ AI Agents | 3️⃣ SQL with AI | 4️⃣ Azure CLI | 5️⃣ Power BI | 6️⃣ Python")
    def run_example(question_text, chat_history):
        return chat_ui(question_text, chat_history)
    # Create a main row for the layout.
    with gr.Row():
        # LEFT-SIDE COLUMN: for the chat interface.
        with gr.Column(scale=3):
            # The chatbot display window.
            chatbot = gr.Chatbot(label="💬 Conversation", elem_classes="chatbot", height=450)
            # A text area for status messages (used for PDF loading status).
            status_text = gr.Markdown("")
            # The textbox where the user types their question.
            question = gr.Textbox(
                label="🙋 Ask Dox a question:",
                placeholder="🤔 Type your question here...",
                lines=1, 
                elem_classes="component"
            )
            # The submit button.
            #ask_btn = gr.Button("Submit 📤", variant="primary")
            with gr.Row():
                ask_btn = gr.Button("Submit 📤", variant="primary", elem_classes="component")
                clear_btn = gr.Button("🧹 Clear Chat", elem_classes="component")
            # A section for example questions.
            gr.Markdown("### 💡 Example Questions", elem_classes="component")
            examples = gr.Examples(
                examples=[
                    "How do you log into Azure using device code authentication?",
                    "What are the three main components of an AI agent?",
                    "What are the \"core four\" Hugging Face libraries?",
                    "What SQL clause is used to filter data after grouping?",
                    "What is the latest GPT model?"
                ],
                inputs=question,
                outputs=[chatbot, question],
                fn=run_example,
                cache_examples=False
            )
            # 👍👎 Feedback buttons
            with gr.Row():
                thumbs_up = gr.Button("👍 Helpful", elem_classes="component")
                thumbs_down = gr.Button("👎 Not Helpful", elem_classes="component")
             
            # Hidden feedback box (only appears on 👎)
            feedback_box = gr.Textbox(
                placeholder="💬 Optional: tell us what went wrong...",
                visible=False
            )
             
            submit_feedback_btn = gr.Button("📝 Submit Feedback", visible=False, elem_classes="component")
            feedback_status = gr.Markdown("", elem_classes="component")
        # RIGHT-SIDE COLUMN: for the PDF preview.
        with gr.Column(scale=3):
            gr.Markdown("### 📄 Referenced PDF Document (🌐 Empty for Web Results)", elem_classes="component")
            #gr.Markdown(" 🌐 Empty by default", elem_classes="component")
            # A hidden state to store the PDF link found in the agent's response.
            link_state = gr.State()
            # A markdown component to show PDF loading status.
            pdf_status = gr.Markdown(visible=False, elem_classes="component")
            # An image component to display the PDF preview.
            output_image = gr.Image(
                label="⬇️ Cheat Sheet Preview",
                visible=False
            )
            pdf_link_btn = gr.Markdown("")

    # Defines the main chat logic as a generator function for streaming output.
    def chat_ui(user_message, chat_history):
        # Initialize chat history if it's the first turn.
        if chat_history is None:
            chat_history = []
    
        # Append the user's message to the chat history.
        chat_history.append({
            "role": "user",
            "content": user_message
        })
    
        # Append a temporary "Thinking..." message from the assistant.
        chat_history.append({
            "role": "assistant",
            "content": "🤔 Dox is thinking..."
        })
    
        # `yield` immediately updates the UI with the user's message and "Thinking...".
        # It also clears the user's input textbox.
        yield (
            chat_history,
            None, # No link yet.
            gr.update(value=None, visible=False), # Hide image preview.
            ""  # Clear textbox.
        )
    
        # Call the agent to get the actual response and PDF link.
        response_text, link = ask_agent(user_message)
    
        # Replace the "Thinking..." message with the final response from the agent.
        chat_history[-1] = {
            "role": "assistant",
            "content": response_text
        }
    
        # `yield` again to update the UI with the final response.
        yield (
            chat_history,
            link, # Pass the extracted link to the link_state.
            gr.update(value=None, visible=False), # Keep image preview hidden for now.
            "" # Keep textbox clear.
        )
        
    # This is a helper function to avoid repeating the event handler chain.
    def submit_chain():
        # It specifies that `chat_ui` is the function to run.
        # It maps the `question` textbox and `chatbot` history as inputs.
        # It maps the outputs to `chatbot` history, `link_state`, `output_image`, and clears the `question` textbox.
        return (
            chat_ui,
            [question, chatbot],
            [chatbot, link_state, output_image, question]
        )

    def show_pdf_link(link):
        if link:
            return f"[📥 Open Full PDF]({link})"
        return ""

    def clear_chat():
        return [], None, gr.update(value=None, visible=False), gr.update(value=None, visible=False), gr.update(value=None, visible=False)

    clear_btn.click(
        clear_chat,
        outputs=[chatbot, link_state, output_image, feedback_box, submit_feedback_btn]
    )

    def show_feedback_box():
        return gr.update(visible=True), gr.update(visible=True)

    def show_appreciation():
        logger.info("It was helpful!")
        return "✅ Feedback submitted. Thank you!"
     
    thumbs_down.click(
        show_feedback_box,
        outputs=[feedback_box, submit_feedback_btn]
    )

    thumbs_up.click(
        show_appreciation,
        outputs=feedback_status
    )

    def handle_feedback(text):
        logger.info(f"User feedback: {text}")
        return "✅ Feedback submitted. Thank you!"
     
    submit_feedback_btn.click(
        handle_feedback,
        inputs=feedback_box,
        outputs=feedback_status
    )

    examples.dataset.click(
        *submit_chain()
    ).then(
        prepare_pdf_loading,
        inputs=link_state,
        outputs=pdf_status
    ).then(
        display_pdf,
        inputs=link_state,
        outputs=[output_image, pdf_status]
    ).then(
        show_pdf_link,
        inputs=link_state,
        outputs=pdf_link_btn
    )

    # Set up the event handler for the "Submit" button click.
    ask_btn.click(
        *submit_chain()
    # `.then()` chains subsequent actions after the first one completes.
    ).then(
        # After chat_ui, call `prepare_pdf_loading` to show the "loading" message.
        prepare_pdf_loading,
        inputs=link_state,  # Use the link from chat_ui's output.
        outputs=pdf_status # Update the pdf_status text.
    ).then(
        # Finally, call `display_pdf` to render the PDF page.
        display_pdf,
        inputs=link_state, # Use the same link.
        outputs=[output_image, pdf_status] # Update the image and hide the status text.
    ).then(
        show_pdf_link,
        inputs=link_state,
        outputs=pdf_link_btn
    )
    
    # Set up the same event handler for when the user presses Enter in the textbox.
    question.submit(
        *submit_chain()
    ).then(
        prepare_pdf_loading,
        inputs=link_state,
        outputs=pdf_status
    ).then(
        display_pdf,
        inputs=link_state,
        outputs=[output_image, pdf_status]
    ).then(
        show_pdf_link,
        inputs=link_state,
        outputs=pdf_link_btn
    )

# This block ensures the code inside only runs when the script is executed directly.
if __name__ == "__main__":
    # Launch the Gradio web server.
    demo.launch()
