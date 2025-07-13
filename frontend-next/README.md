# SQL Agent Chat - Next.js Frontend

A modern, responsive web application built with Next.js, TypeScript, and Tailwind CSS that provides an intuitive interface for interacting with the SQL Agent API.

## Features

- **Modern UI/UX**: Beautiful, responsive design with smooth animations and transitions
- **Real-time Chat**: Interactive chat interface with the SQL Agent
- **Query Approval System**: Human-in-the-loop SQL query approval workflow
- **Memory Management**: User conversation history and entity tracking
- **System Monitoring**: Health checks and user management
- **Authentication**: Simple username-based authentication system
- **Command System**: Quick access to memory and system commands

## Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **State Management**: React Context API
- **HTTP Client**: Native fetch API

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Backend API server running on `http://localhost:8001`

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── login/             # Login page
│   ├── register/          # Registration page
│   ├── globals.css        # Global styles
│   ├── layout.tsx         # Root layout
│   └── page.tsx           # Home page
├── components/            # React components
│   ├── ChatInterface.tsx  # Main chat interface
│   ├── ChatMessage.tsx    # Individual message component
│   ├── SqlQueryDisplay.tsx # SQL query and results display
│   └── ApprovalInterface.tsx # Query approval interface
├── contexts/              # React contexts
│   └── AuthContext.tsx    # Authentication context
└── lib/                   # Utility libraries
    ├── api.ts            # API service layer
    └── utils.ts          # Utility functions
```

## API Integration

The frontend communicates with the backend API through the following endpoints:

- `POST /api/v1/query` - Send questions and get responses
- `POST /api/v1/query/approve` - Approve SQL queries for execution
- `POST /api/v1/query/regenerate` - Regenerate queries with feedback
- `POST /api/v1/memory/command` - Execute memory commands
- `GET /api/v1/health` - Check system health
- `GET /api/v1/users` - Get all active users

## Key Components

### ChatInterface
The main chat component that handles:
- Message sending and receiving
- Query approval workflow
- Memory commands
- System commands
- Real-time updates

### ApprovalInterface
Handles the human-in-the-loop approval process:
- Display generated SQL queries
- Provide feedback for regeneration
- Approve or reject queries
- Show query context and results

### SqlQueryDisplay
Formatted display of SQL queries and results:
- Syntax highlighting
- Copy to clipboard functionality
- Responsive design
- Error handling

## Available Commands

### Memory Commands
- `/history` - View conversation history
- `/entities` - Show known entities
- `/summary` - Get conversation summary
- `/clear` - Clear user memory

### System Commands
- `/health` - Check system health
- `/users` - List all active users

## Development

### Running in Development Mode
```bash
npm run dev
```

### Building for Production
```bash
npm run build
```

### Starting Production Server
```bash
npm start
```

### Linting
```bash
npm run lint
```

## Environment Variables

Create a `.env.local` file in the root directory:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8001/api/v1
```

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is part of the SQL Agent Chat application.
