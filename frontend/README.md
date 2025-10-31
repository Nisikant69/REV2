# REV2 Frontend

A modern React + Next.js dashboard for monitoring and managing AI-powered code reviews.

## Overview

The REV2 frontend provides a comprehensive web interface for:
- **Real-time Dashboard**: Monitor key metrics and recent reviews
- **Reviews Management**: Browse, search, filter, and export code reviews
- **Analytics**: Detailed insights into model performance and API usage
- **Settings**: Configure REV2 behavior and preferences

## Technology Stack

- Next.js 14 (React 18)
- TypeScript
- Tailwind CSS
- React Query (@tanstack/react-query)
- Sonner (toast notifications)
- Lucide Icons

## Quick Start

```bash
# Install dependencies
npm install

# Set environment variables
cp .env.example .env.local

# Development
npm run dev

# Build for production
npm run build
npm start
```

## Project Structure

```
frontend/
├── src/
│   ├── pages/
│   │   ├── _app.tsx          # App wrapper
│   │   ├── index.tsx         # Dashboard
│   │   ├── reviews.tsx       # Reviews list
│   │   ├── analytics.tsx     # Analytics
│   │   └── settings.tsx      # Settings
│   ├── components/
│   │   ├── Layout.tsx        # Main layout
│   │   ├── MetricCard.tsx    # KPI card
│   │   └── ReviewsTable.tsx  # Reviews table
│   ├── lib/
│   │   └── api.ts           # API client
│   └── styles/
│       └── globals.css      # Global styles
└── public/
```

## Pages

### Dashboard
- Key metrics (total reviews, latency, cache hits, success rate)
- Time range selector (24h, 7d, 30d)
- Recent reviews table

### Reviews
- Full-text search
- Filter by status and sorting options
- Bulk export to CSV
- Pagination support

### Analytics
- Model performance comparison
- Top repositories statistics
- API usage breakdown

### Settings
- LLM model selection
- Processing configuration
- Rate limiting controls

## Environment Variables

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_TIMEOUT=30000
```

## API Integration

The `src/lib/api.ts` file exports methods for all backend endpoints:

```typescript
api.getMetrics(timeRange)
api.getReviews(options)
api.getAnalytics(timeRange)
api.getSettings()
api.updateSettings(settings)
api.exportReviews(options)
```

All API calls are fully typed with TypeScript.
