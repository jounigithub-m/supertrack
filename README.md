# Supertrack AI Platform

Supertrack is a comprehensive AI platform designed for managing data sources, creating AI models, and running analytics in a user-friendly environment.

## Project Structure

The project is split into two main directories:

- `frontend/`: Next.js 14 application with TypeScript
- `backend/`: Python-based Azure Functions for API endpoints

## Technology Stack

### Frontend
- Next.js 14 with App Router
- TypeScript
- Tailwind CSS for styling
- shadcn/ui component library
- NextAuth.js for authentication
- Axios for API requests
- Chart.js for data visualization

### Backend
- Python 3.10+
- Azure Functions
- Azure Cosmos DB for data storage
- Azure Data Lake Storage Gen2 for file storage
- StarRocks DB and Neo4j for specialized data processing
- PyPDF2, pandas, and various AI/ML libraries

## Features

- User authentication and role-based access control
- Data source management
- AI model creation and training
- Dashboard for analytics and monitoring
- Project management
- Team collaboration tools

## Installation

### Prerequisites
- Node.js 18+ and npm
- Python 3.10+
- Azure Functions Core Tools
- Azure CLI (for deployment)

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create a `.env.local` file based on `.env.example` with your configuration.

4. Start the development server:
   ```bash
   npm run dev
   ```

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```

3. Activate the virtual environment:
   ```bash
   # On Windows
   .venv\Scripts\activate
   # On macOS/Linux
   source .venv/bin/activate
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Create a `local.settings.json` file with your configuration.

6. Start the Functions runtime:
   ```bash
   func start
   ```

## Development Guidelines

- Follow TypeScript strict mode
- Use functional React components with hooks
- Document all functions and components
- Write tests for all major functionality
- Follow the established design system

## Environment Configuration

The application uses different environments:
- Development (dev)
- Testing (test)
- Production (prod)

Each environment has its own database and storage configurations.

## Deployment

### Frontend Deployment

1. Build the application:
   ```bash
   npm run build
   ```

2. Deploy to your hosting provider (e.g., Azure Static Web Apps, Vercel)

### Backend Deployment

1. Deploy to Azure Functions:
   ```bash
   func azure functionapp publish <app-name>
   ```

## License

[MIT License](LICENSE)

## Contributors

- Jouni Leskinen