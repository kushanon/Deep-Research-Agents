# 🔬 Deep Research Agent

AI agent system that automates internal document search and deep research for enterprises

## 🎯 Overview
Deep Research Agent is a next-generation MultiAgent system built on **Semantic Kernel**. Through **MagenticOrchestration**, multiple specialized AI agents dynamically collaborate to automatically generate high-quality research reports from enterprise internal documents. From internal document search via Azure AI Search, Semantic Kernel Memory, to comprehensive reliability assessment, it intelligently automates the entire enterprise research process.

### 🌟 Key Features

- **🤖 Magentic Multi-Agent Orchestration**: Latest orchestration technology from Semantic Kernel
- **🔍 Advanced Internal Document Search**: Azure AI Search + Semantic Kernel Memory integration
- **🌐 Web Search Integration**: Enhanced research capabilities with external web search fallback
- **🧠 Contextual Memory Management**: Persistent research context and knowledge integration via Semantic Kernel Memory
- **🛡️ AI Reliability Assessment**: Multi-layered Confidence evaluation and source quality management
- **📝 Structured Report Generation**: Evidence-based reports with citation management
- **🌐 Multilingual Intelligence**: Professional terminology translation system
- **⚡ Dynamic Quality Management**: Real-time quality assessment and self-improvement loops

## 🏗️ Architecture

Deep Research Agent is a next-generation MultiAgent system centered on **Microsoft Semantic Kernel** and **MagenticOrchestration**. It fully automates internal document search, analysis, and report generation specialized for enterprise R&D.

### 🎭 System Overview Diagram

```
                         ┌─────────────────────────────────┐
                         │    MagenticOrchestration        │
                         │  (StandardMagenticManager)      │
                         │     + R&D Logic Engine          │
                         └──────────┬──────────────────────┘
                                    │ Dynamic Coordination
                                    ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │                     Specialized Agent System                    │
   │                    (Semantic Kernel Agents)                     │
   │                                                                 │
   │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐    │
   │  │ LeadResearcher  │ │ Credibility     │ │   Summarizer    │    │
   │  │    Agent        │ │ Critic Agent    │ │     Agent       │    │
   │  │ ┌─────────────┐ │ │ (Source Quality │ │ (Knowledge      │    │
   │  │ │RESEARCHER1  │ │ │  Assessment)    │ │  Synthesis)     │    │
   │  │ │RESEARCHER2  │ │ │                 │ │                 │    │
   │  │ │RESEARCHER3+ │ │ │                 │ │                 │    │
   │  │ └─────────────┘ │ │                 │ │                 │    │
   │  └─────────────────┘ └─────────────────┘ └─────────────────┘    │
   │                                                                 │
   │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐    │
   │  │ ReportWriter    │ │ Reflection      │ │  Translator     │    │
   │  │    Agent        │ │ Critic Agent    │ │    Agent        │    │
   │  │ (Confidence +   │ │ (Quality        │ │ (Professional   │    │
   │  │  Citations)     │ │  Validation)    │ │  Translation)   │    │
   │  └─────────────────┘ └─────────────────┘ └─────────────────┘    │
   │                                                                 │
   │  ┌─────────────────┐                                            │
   │  │  Citation       │                                            │
   │  │    Agent        │                                            │
   │  │ (Reference      │                                            │
   │  │  Management)    │                                            │
   │  └─────────────────┘                                            │
   └─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │                     Plugin & Infrastructure Layer               │
   │                                                                 │
   │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐    │
   │  │  SK Memory      │ │ ModularSearch   │ │   Embedding     │    │
   │  │   Plugin        │ │    Plugin       │ │   Provider      │    │
   │  │ (Research       │ │ (Azure AI       │ │ (Vectorization) │    │
   │  │  Context)       │ │  Search)        │ │                 │    │
   │  └─────────────────┘ └─────────────────┘ └─────────────────┘    │
   └─────────────────────────────────────────────────────────────────┘
```

### 🔬 Internal Document Search System

**ModularSearchPlugin** provides comprehensive search capabilities:

An Azure AI Search integration system dynamically configured based on project settings (`config/project_config.yaml`). It provides unified interface search functionality across multiple indexes defined in configuration files.

The search system flexibly adapts to enterprise-specific document structures and index configurations, achieving high-precision information retrieval through a combination of Vector search, Semantic search, and Full-text search.

#### 🌐 Web Search Integration

**Enhanced Research Capabilities**: The system now includes web search functionality as an additional information source and fallback mechanism:

- **Primary Search**: Internal document search via Azure AI Search
- **Web Search Fallback**: When internal sources are insufficient, the system automatically falls back to web search
- **Configurable Integration**: Web search can be enabled/disabled and configured via `project_config.yaml`
- **Quality Assurance**: Web search results undergo the same reliability assessment as internal documents

<details>
<summary>

### 🎭 Specialized Agent Configuration

</summary>

#### 1. **LeadResearcherAgent** 🎯 *Lead Researcher*
   - **Role**: Manager and coordinator of multiple internal sub-ResearchAgents
   - **Architecture**: Contains and orchestrates 3+ sub-ResearchAgents (RESEARCHER1, RESEARCHER2, RESEARCHER3...)
   - **Special Capability**: Parallel orchestration and concurrent execution of multiple research queries
   - **Implementation**: Internal agent management via `ConcurrentOrchestration` and `ParallelResearchPlugin`
   - **Functions**: 
     - Distributes research queries across sub-ResearchAgents
     - Aggregates and synthesizes results from multiple agents
     - Quality management and result integration
     - Dynamic agent scaling based on workload
   - **Memory**: Context continuation through Semantic Kernel Memory integration shared across all sub-agents

#### 2. **CredibilityCriticAgent** 🔍 *Reliability Assessment Specialist*
   - **Role**: Scientific evaluation of internal source reliability and coverage
   - **Evaluation Criteria**: Source quality, information consistency, evidence strength
   - **Functions**: Supplementation through additional searches, reliability score calculation
   - **Output**: Structured reliability reports + improvement recommendations

#### 3. **SummarizerAgent** 📋 *Knowledge Integration Specialist*
   - **Role**: Structured summarization of large volumes of internal documents
   - **Specialization**: Classification by enterprise themes, prioritization
   - **Technology**: Hierarchical summarization, keyword extraction, relevance analysis
   - **Output**: Structured summaries + key point extraction

#### 4. **ReportWriterAgent** ✍️ *Report Generation Specialist*
   - **Role**: Final report creation and Confidence score assignment
   - **Technology**: Structured document generation, citation management, evidence demonstration
   - **Evaluation**: Multi-axis Confidence evaluation (source quality, consistency, comprehensiveness)
   - **Output**: Decision support reports + reliability indicators

#### 5. **ReflectionCriticAgent** 🎯 *Quality Assurance Specialist*
   - **Role**: Validation of report quality and Confidence evaluation validity
   - **Technology**: Meta-cognitive evaluation, logical consistency checks, improvement recommendations
   - **Standards**: Compliance with enterprise R&D quality standards
   - **Output**: Quality evaluation reports + improvement guidance

#### 6. **TranslatorAgent** 🌐 *Multilingual Specialist*
   - **Role**: High-precision translation with specialized terminology support
   - **Specialization**: Technical document format preservation, specialized terminology dictionary
   - **Functions**: Bidirectional Japanese-English translation, context-aware translation
   - **Quality**: Translation quality evaluation, terminology standardization

#### 7. **CitationAgent** 📚 *Citation Management Specialist*
   - **Role**: Internal document citation and reference management
   - **Technology**: Automated citation generation, source traceability
   - **Verification**: Citation accuracy, source existence confirmation
   - **Output**: Structured citation lists + metadata

</details>

## 🚀 Setup

### Prerequisites

Before installing the Deep Research Agent, ensure you have the following:

- **Python 3.12+** (Recommended: 3.12.10 or later)
- **Azure OpenAI** account with access to:
  - GPT-4.1, GPT-4.1-mini, o3 or equivalent models
  - Text embedding models (text-embedding-3-small, text-embedding-3-large, etc.)
- **Azure AI Search** service with:
  - Semantic search configuration enabled
  - Vector search capabilities
  - Existing search indexes with your enterprise documents
- **Web Search API** (optional, for web search functionality):
  - Tavily API key
  - Currently, this repo only supports Tavily, please implement search providers if you want to use other search engines

### 📦 Installation

Follow these step-by-step instructions to set up the Deep Research Agent:

#### Step 1: Clone the Repository
```powershell
git clone <repository-url>
cd <directory-name>
```

#### Step 2: Create Python Virtual Environment (if needed)
```powershell
# Create virtual environment
python -m venv deepresearchagent

# Activate virtual environment
.\deepresearchagent\Scripts\Activate.ps1

# Verify activation (should show the virtual environment path)
where python
```

#### Step 3: Install Python Dependencies
```powershell
pip install -r requirements.txt
```

#### Step 4: Create Configuration Files from Templates

**4.1 Create Environment Variables File**
```powershell
# Copy template and create your .env file
Copy-Item .env.example .env
```
Please update based on your settings

**4.2 Create Project Configuration File**
```powershell
# Copy template and create your project configuration
Copy-Item config\project_config_templates.yaml config\project_config.yaml

```
Please update project configuration with your specific settings

**Required configurations in `config/project_config.yaml`:**
- Company information (system.company)
- **Azure AI Search index configurations (data_sources.document_types)**
- Web search settings (data_sources.web_search)
- Agent behavior parameters (agents)

#### Step 5: Launch the script
```powershell
# Start the research agent
python main.py --query "Could you summarize the latest update on Azure OpenAI in 2025?"
```

### 🛠️ Configuration Details

#### Template File Structure

The system uses template files that you need to copy and customize:

```
Deep-Research-Agent/

├── config/
│   ├── project_config_templates.yaml # Template for project configuration
│   └── project_config.yaml           # Your customized configuration (create this)
├── .env.example                      # Template for environment variables
└── .env                              # Your environment variables (create this)
```