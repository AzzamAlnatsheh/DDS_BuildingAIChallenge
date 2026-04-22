# 🤖 Dox - The Data Professional's AI Advisor

[![Hugging Face Spaces](https://img.shields.io/badge/🤗-Live%20Demo-blue)](https://huggingface.co/spaces/Crackershoot/BuildingAIChallenge)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
<!-- 
Dox is an AI-powered assistant designed to answer data-related questions. It uses a knowledge base of DataCamp cheat sheets (Hugging Face, AI Agents, Azure CLI, SQL with AI) and can supplement answers with a web search.

## ✨ Features

-   🤖 Answers questions using a vector knowledge base
-   🌐 Can perform web searches for up-to-date information
-   📄 Extracts PDF links from responses and displays the first page as a preview
-   🎨 Clean, Ocean-themed Gradio interface
-   🔗 Automatic citation linking to sources

## 🚀 Live Demo

The easiest way to try Dox is on Hugging Face Spaces:  
**[Click here for the live demo](https://huggingface.co/spaces/Crackershoot/BuildingAIChallenge)**

## 💻 Run Locally

To run Dox on your own computer:

1.  **Clone the repository**
    ```bash
    git clone https://github.com/AzzamAlnatsheh/DDS_BuildingAIChallenge.git
    cd DDS_BuildingAIChallenge

# 🤖 Dox – Data Professional's AI Advisor
-->
Dox is an AI-powered assistant designed for data professionals.
It combines a **vector-based knowledge base**, **live web search**, and an intuitive **Gradio UI** to deliver accurate, context-aware answers on data, AI, cloud, and programming topics.

---

## 🚀 Features

* 🧠 **Knowledge Base Search (RAG)**

  * Uses DataCamp cheat sheets (PDFs)
  * Embedded with OpenAI embeddings
  * Stored in LanceDB for fast vector retrieval

* 🌐 **Live Web Search**

  * Uses DuckDuckGo for up-to-date answers
  * Automatically triggered when needed

* 📄 **PDF Source Detection & Preview**

  * Extracts PDF links from responses
  * Displays first-page preview directly in UI
  * Option to open full document

* 💬 **Interactive Chat Interface**

  * Built with Gradio Blocks
  * Streaming-style response flow (“Thinking...” UX)
  * Example prompts for quick start

* 👍 **User Feedback System**

  * Thumbs up / down interaction
  * Optional feedback submission
  * Designed for future improvement loop

* 🧹 **Session Controls**

  * Clear chat functionality
  * Dynamic UI updates

---

## 🏗️ Architecture

```
User asks a question
   ↓
Gradio UI (Chat Interface)
   ↓
Agent (agno)
   ├── 🔍 Knowledge Base (LanceDB + PDFs)
   └── 🌐 DuckDuckGo Web Search
   ↓
Response + Source Link
   ↓
PDF Preview Renderer (PyMuPDF)
```
---

## 🚀 Live Demo

The easiest way to try Dox is on Hugging Face Spaces:  
**[Click here for the live demo](https://huggingface.co/spaces/Crackershoot/BuildingAIChallenge)**

---

## 🧰 Tech Stack

| Component       | Technology                      |
| --------------- | ------------------------------- |
| LLM             | OpenAI (gpt-4.1-mini)           |
| Agent Framework | agno                            |
| Embeddings      | OpenAI `text-embedding-3-small` |
| Vector DB       | LanceDB                         |
| UI              | Gradio                          |
| PDF Handling    | PyMuPDF + Pillow                |
| Web Search      | DuckDuckGo                      |

---

## 📚 Knowledge Sources

Dox is powered by curated cheat sheets:

* Hugging Face
* AI Agents
* SQL with AI
* Azure CLI

---

## ⚙️ Installation

```bash
git clone https://github.com/your-username/dox-ai-advisor.git
cd dox-ai-advisor
pip install -r requirements.txt
```

---

## 🔑 Environment Variables

Create a `.env` file or set:

```bash
OPENAI_API_KEY=your_openai_api_key
```

---

## ▶️ Run the App

```bash
python app.py
```

Then open the Gradio link in your browser.

---

## 💡 Example Questions

* How do you log into Azure using device code authentication?
* What are the three main components of an AI agent?
* What SQL clause is used after GROUP BY?
* What is the latest GPT model?

---

## 🧠 How It Works

1. User submits a question
2. Agent searches:

   * First → Knowledge Base (PDFs)
   * Then → Web (if needed)
3. Response is generated with citations
4. PDF links are extracted and previewed

---

## 📸 UI Highlights

* Chat-based interaction
* Real-time thinking indicator
* PDF preview panel
* Feedback buttons

---

## 🔮 Future Improvements

* 🔄 Streaming token-by-token responses
* 📊 Feedback analytics dashboard
* 🧑‍💻 User authentication & session history
* 🗂️ Multi-document upload support
* 🌙 Dark mode toggle

---

## 📄 License

MIT License

---

## 👤 Author

**Azzam Alnatsheh**
Power BI Developer | Data Analyst | AI Enthusiast

---

## ⭐ Support

If you find this project useful, consider giving it a star ⭐ on GitHub!
