# 💊 PharmAI: The AI-Powered Pharmacovigilance & Accessibility Platform

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-green.svg)
![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock%20%7C%20Kendra-FF9900.svg)
![Sarvam AI](https://img.shields.io/badge/Indic%20AI-Sarvam-purple.svg)

**PharmAI** is a groundbreaking, full-stack healthcare intelligence platform built for the **AI for Bharat Hackathon**. It tackles India's most pressing healthcare challenges: regulatory compliance of drugs (CDSCO gazettes) and the accessibility of affordable generic medicines (Jan Aushadhi) using cutting-edge Generative AI and Indic Language models.

---

## 🚀 The Vision

In India:
1. **Regulatory Blindspots**: Pharmacies unknowingly stock locally banned fixed-dose combinations (FDCs) because parsing CDSCO gazettes manually is an administrative nightmare.
2. **Cost Barrier**: Millions overpay for branded drugs because they are unaware of equally effective, highly regulated **Jan Aushadhi** generic alternatives.
3. **Language Barrier**: The majority of India's population communicates in vernacular languages, making English-first medical advisory tools useless.

**PharmAI solves this.** 
We parse complex regulatory law into structured JSON in milliseconds, provide AI OCR to digitize prescriptions, map branded drugs to high-quality affordable generics, and deliver the entire experience via Indic Voice capabilities (Speech-to-Text & Text-to-Speech).

---

## ✨ Core Features

* 📚 **Real-Time Regulatory RAG**: Queries against official CDSCO gazette documents to flag banned/restricted drugs instantly with 100% hallucination-free citations.
* 💸 **Jan Aushadhi Substitutions**: Recommends heavily discounted, government-approved generic alternatives to lower out-of-pocket patient expenses.
* 🗣️ **Indic Voice Core**: Integrated with **Sarvam AI** for native Indian language Speech-to-Text (STT), Text-to-Speech (TTS), and real-time translation. 
* 📝 **Prescription OCR & Analysis**: Upload handwritten or printed prescriptions. The platform digitizes the text, analyzes the drugs, checks for cross-interactions, and flags safety warnings.
* ⚡ **Seamless Dual-System Architecture**: 
  * A lightweight, highly responsive **Flask Portal** for the User Interface.
  * A robust, high-performance **FastAPI backend (AWS_RAG_CURD)** interfacing securely with Amazon Bedrock and Kendra.

---

## 🏗️ Project Structure

This repository acts as the master monorepo. It heavily interacts with our backend service.

| Directory / Service | Role | Tech Stack |
|:---|:---|:---|
| [`pharmai_portal`](.) | User Portal & Client-Side Proxy | Flask, HTML5, CSS3, JS, Sarvam APIs |
| [`AWS_RAG_CURD`](../AWS_RAG_CURD) | Knowledge Base RAG Backend | FastAPI, Bedrock, Kendra, Nova Lite |

For an in-depth look at our technical approach, please see our [**TECHNICAL_ARCHITECTURE.md**](./TECHNICAL_ARCHITECTURE.md).

For our business and scalable go-to-market strategy, explore our [**PITCH.md**](./PITCH.md).

For our future vision and planned features, see [**FUTURE_ROADMAP.md**](./FUTURE_ROADMAP.md).

---

## 🛠️ Getting Started

To run the complete PharmAI platform locally, you will need to spin up both the RAG Backend and the Frontend Portal.

### 1. Start the AWS RAG Backend
The backend manages the Knowledge Base and CDSCO logic.
```bash
cd ../AWS_RAG_CURD
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env # Configure your AWS credentials here
uvicorn app.main:app --port 4101 --reload
```

### 2. Start the PharmAI Portal
The portal handles user interactions, OCR, and Indic audio features.
```bash
cd ../pharmai_portal/frontend
python3 -m venv venv_pharmai
source venv_pharmai/bin/activate
pip install -r requirements.txt
cp .env.example .env # Configure your Sarvam AI keys here
python app.py
```

Visit `http://localhost:5000` to interact with the PharmAI Platform!

---

## 💡 Hackathon Evaluation Highlight
* **Novelty**: First platform to merge real-time Gazette indexing with native Hindi/regional language translation for immediate patient and pharmacy impact.
* **Impact**: Potential to save ₹8,800 Cr in reduced healthcare spending through generic substitutions and thousands of lives saved by automating drug ban enforcement.
* **Execution**: Fully functional multi-tier RAG processing, active STT/TTS modules, and zero-hallucination guardrails via Amazon Kendra.

---

*Built with ❤️ for the AI For Bharat Hackathon.*
