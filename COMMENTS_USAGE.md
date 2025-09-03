# Comments Feature Usage

This document explains how to use the new comments feature that has been implemented.

## Backend Implementation

The comments feature includes:
- **Database Model**: `CommentDb` in `src/backend/src/db_models/comments.py`
- **API Models**: `Comment`, `CommentCreate`, `CommentUpdate` in `src/backend/src/models/comments.py`
- **Repository**: `CommentsRepository` in `src/backend/src/repositories/comments_repository.py`
- **Manager**: `CommentsManager` in `src/backend/src/controller/comments_manager.py`
- **Routes**: Comment API endpoints in `src/backend/src/routes/comments_routes.py`

## API Endpoints

- `POST /api/entities/{entity_type}/{entity_id}/comments` - Create comment
- `GET /api/entities/{entity_type}/{entity_id}/comments` - List comments for entity
- `GET /api/comments/{comment_id}` - Get specific comment
- `PUT /api/comments/{comment_id}` - Update comment
- `DELETE /api/comments/{comment_id}` - Delete comment (soft delete by default)
- `GET /api/comments/{comment_id}/permissions` - Check comment permissions

## Frontend Implementation

### Components
- **CommentSidebar**: Main reusable component in `src/frontend/src/components/comments/comment-sidebar.tsx`

### Hooks
- **useComments**: Custom hook for comment operations in `src/frontend/src/hooks/use-comments.ts`

### Types
- Comment-related TypeScript types in `src/frontend/src/types/comments.ts`

## Usage Examples

### Basic Usage in a React Component

```tsx
import React, { useState } from 'react';
import { CommentSidebar } from '@/components/comments';

const MyDataProductPage = () => {
  const [isCommentSidebarOpen, setIsCommentSidebarOpen] = useState(false);
  
  return (
    <div className="flex">
      <div className="flex-1">
        {/* Your main content */}
        <h1>Data Product Details</h1>
        <p>Product information...</p>
      </div>
      
      <div className="ml-4">
        <CommentSidebar
          entityType="data_product"
          entityId="product-123"
          isOpen={isCommentSidebarOpen}
          onToggle={() => setIsCommentSidebarOpen(!isCommentSidebarOpen)}
        />
      </div>
    </div>
  );
};
```

### Using the Comments Hook

```tsx
import { useComments } from '@/hooks/use-comments';

const MyComponent = () => {
  const {
    comments,
    totalCount,
    visibleCount,
    loading,
    fetchComments,
    createComment,
    updateComment,
    deleteComment
  } = useComments('data_product', 'product-123');

  const handleCreateComment = async () => {
    await createComment({
      entity_type: 'data_product',
      entity_id: 'product-123',
      comment: 'This is a great data product!',
      title: 'Feedback',
      audience: ['data-consumers'] // Only visible to data-consumers group
    });
  };

  // ... rest of component
};
```

## Features

### Comment Visibility (Audience)
Comments can be restricted to specific user groups:
- `audience: null` or `audience: []` - Visible to all users with access to the entity
- `audience: ['group1', 'group2']` - Only visible to users in specified groups

### Permissions
- **Create**: Any user with READ_WRITE access to the feature
- **Edit**: Comment author or admin users
- **Delete**: Comment author or admin users
- **View**: Based on comment audience and user's entity access

### Soft Delete
Comments are soft-deleted by default (marked as `status: 'deleted'`), but admins can perform hard deletes.

## Entity Types

The comment system works with any entity type. Common entity types:
- `data_product`
- `data_contract`
- `data_domain`
- `business_glossary_term`
- etc.

## Database Schema

Comments table includes:
- `id`: UUID primary key
- `entity_id`: ID of the entity being commented on
- `entity_type`: Type of entity (data_product, data_contract, etc.)
- `title`: Optional comment title
- `comment`: Comment content (required)
- `audience`: JSON array of group names (optional)
- `status`: 'active' or 'deleted'
- `created_by`: Email of comment author
- `updated_by`: Email of last updater
- `created_at`/`updated_at`: Timestamps

## Adding to Existing Views

To add comments to any existing entity view:

1. Import the CommentSidebar component
2. Add state for sidebar open/close
3. Place the component in your JSX with appropriate entityType and entityId
4. The component handles all comment CRUD operations internally

The sidebar appears as a slide-out panel from the right side of the screen, similar to Google Docs comments.