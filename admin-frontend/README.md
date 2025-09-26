# MagFlow ERP - Admin Dashboard

A modern, responsive admin dashboard for MagFlow ERP built with React, TypeScript, and Ant Design.

## 🚀 Features

### 📊 Dashboard Overview

- **Real-time metrics** - Sales, orders, customers, inventory
- **Interactive charts** - Sales trends, product performance, inventory levels
- **eMAG integration status** - Sync status, product counts, recent updates
- **Quick actions** - Fast access to common tasks

### 🔗 eMAG Integration

- **Live sync status** - Real-time synchronization monitoring
- **Product management** - View and manage eMAG products
- **Sync history** - Complete audit trail of all synchronizations
- **Manual sync control** - Trigger synchronizations on demand

### 🎨 Modern UI/UX

- **Responsive design** - Works on desktop, tablet, and mobile
- **Dark/Light theme** - Professional appearance
- **Intuitive navigation** - Easy to find and use features
- **Fast performance** - Optimized for speed and efficiency

## 🛠️ Technology Stack

### Frontend

- **React 18** - Modern React with hooks and functional components
- **TypeScript** - Type-safe development
- **Vite** - Fast build tool and development server
- **Ant Design** - Enterprise-grade UI components
- **Recharts** - Beautiful, customizable charts
- **React Router** - Client-side routing
- **Axios** - HTTP client for API calls

### Backend Integration

- **FastAPI** - High-performance async API framework
- **SQLAlchemy** - Database ORM with async support
- **PostgreSQL** - Robust database with JSON support
- **WebSocket** - Real-time data updates (planned)

## 📁 Project Structure

```
admin-frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── Layout.tsx      # Main layout with navigation
│   │   └── ...
│   ├── pages/              # Page components
│   │   ├── Dashboard.tsx   # Main dashboard page
│   │   ├── EmagSync.tsx    # eMAG integration page
│   │   ├── Products.tsx    # Products management
│   │   ├── Users.tsx       # User management
│   │   ├── Settings.tsx    # Settings page
│   │   └── Login.tsx       # Authentication page
│   ├── services/           # API services and utilities
│   ├── types/              # TypeScript type definitions
│   ├── utils/              # Utility functions
│   └── styles/             # CSS styles and themes
├── public/                 # Static assets
├── package.json           # Dependencies and scripts
├── vite.config.ts         # Vite configuration
├── tsconfig.json          # TypeScript configuration
└── index.html             # Main HTML template
```

## 🚀 Quick Start

### Prerequisites

- Node.js 16+ and npm (or yarn)
- Python 3.8+ with FastAPI backend running

### Installation

1. **Install dependencies:**

   ```bash
   cd admin-frontend
   npm install
   # or
   yarn install
   ```

1. **Start development server:**

   ```bash
   npm run dev
   # or
   yarn dev
   ```

1. **Open browser:**
   Navigate to `http://localhost:3000`

### Backend Setup

Ensure your FastAPI backend is running on `http://localhost:8000`:

```bash
cd /path/to/magflow
uvicorn app.main:app --reload --port 8000
```

## 📖 Usage

### Dashboard Navigation

- **Dashboard** (`/`) - Main overview with key metrics
- **eMAG Integration** (`/emag`) - Manage eMAG synchronization
- **Products** (`/products`) - Product inventory management
- **Users** (`/users`) - User management and permissions
- **Settings** (`/settings`) - System configuration

### API Integration

The dashboard communicates with the FastAPI backend through REST APIs:

- `GET /api/v1/admin/dashboard` - Dashboard metrics
- `POST /api/v1/admin/sync-emag` - Trigger eMAG sync
- `GET /api/v1/emag/status` - eMAG integration status
- `GET /api/v1/emag/products` - eMAG products list

## 🎨 Customization

### Theming

The dashboard uses Ant Design's theming system. Customize colors and styles in `src/styles/index.css`:

```css
:root {
  --primary-color: #1890ff;
  --success-color: #52c41a;
  --warning-color: #fa8c16;
  --error-color: #ff4d4f;
}
```

### Adding New Pages

1. Create component in `src/pages/`
1. Add route in `src/App.tsx`
1. Add navigation item in `src/components/Layout.tsx`

### API Integration

1. Add API endpoint in FastAPI backend
1. Create service function in `src/services/`
1. Use service in component with proper error handling

## 🔧 Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking

### Code Quality

- **ESLint** - JavaScript/TypeScript linting
- **TypeScript** - Type checking
- **Prettier** - Code formatting (recommended)

### Best Practices

- Use **TypeScript** for all new code
- Follow **React hooks** patterns
- Use **custom hooks** for reusable logic
- Implement **error boundaries** for robust error handling
- Use **loading states** for better UX

## 📱 Responsive Design

The dashboard is fully responsive and works on:

- Desktop computers (1200px+)
- Tablets (768px - 1199px)
- Mobile phones (\< 768px)

Key responsive features:

- Collapsible sidebar navigation
- Responsive charts and tables
- Mobile-optimized touch interactions
- Adaptive layout for different screen sizes

## 🔐 Authentication

The dashboard includes a login system with:

- JWT token-based authentication
- Protected routes
- User session management
- Role-based access control (extensible)

**Demo Credentials:**

- Username: `admin`
- Password: `admin123`

## 🚀 Deployment

### Production Build

```bash
npm run build
```

The build artifacts will be stored in the `dist/` directory.

### Environment Variables

Create `.env` file for configuration:

```env
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
REACT_APP_ENVIRONMENT=development
```

## 🤝 Contributing

1. Follow the established code structure
1. Use TypeScript for all new features
1. Add proper error handling
1. Write meaningful commit messages
1. Test on multiple screen sizes
1. Update documentation as needed

## 📄 License

This project is part of MagFlow ERP and follows the same licensing terms.

______________________________________________________________________

**🎉 Happy coding! The admin dashboard is ready for development and customization.**
