# Supertrack AI Platform

A multitenant SaaS platform that syncs enterprise data into Apache Iceberg tables, StarRocks analytical databases, and Neo4j knowledge graphs to power topic-specific AI agents.

## Features

- **AI-Powered Data Management**: Autonomous agents for data syncing and analysis
- **Multi-Database Architecture**: Leverages Iceberg, StarRocks, and Neo4j
- **Interactive Q&A**: Chat with AI agents and pin answers to dashboards
- **API Integration**: Automation workflows through comprehensive API access
- **Enterprise-Grade Security**: Strict tenant isolation and data privacy

## Tech Stack

### Frontend
- Next.js 14 with App Router
- TypeScript
- shadcn/ui + Tailwind CSS
- Chart.js for visualizations

### Backend
- Azure Functions (Python)
- Azure Cosmos DB
- Azure Data Lake Storage Gen2
- StarRocks & Neo4j
- LangChain & LCEL

## Getting Started

### Prerequisites

- Node.js 18.x or later
- Python 3.9 or later
- Azure subscription
- Docker for local development

### Development Setup

1. Clone the repository:
```bash
git clone https://github.com/jounigithub-m/supertrack.git
cd supertrack
```

2. Install frontend dependencies:
```bash
cd frontend
npm install
```

3. Install backend dependencies:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp frontend/.env.example frontend/.env.local
cp backend/.env.example backend/.env
```

5. Start development servers:

Frontend:
```bash
cd frontend
npm run dev
```

Backend:
```bash
cd backend
func start
```

## Project Structure

```
supertrack/
├── frontend/              # Next.js 14 frontend application
├── backend/              # Azure Functions backend
├── infrastructure/       # Infrastructure as code
├── docs/                # Documentation
├── scripts/             # Utility scripts
└── tests/               # End-to-end and integration tests
```

## Documentation

- [Frontend Guidelines](docs/frontend-guidelines.md)
- [Backend Structure](docs/backend-structure.md)
- [API Documentation](docs/api-docs.md)
- [Deployment Guide](docs/deployment-guide.md)

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please open an issue in the GitHub repository or contact the development team.