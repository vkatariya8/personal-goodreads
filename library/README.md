# Personal Goodreads Library

This directory contains your book library in markdown format.

## Structure

- `books/` - Individual book files with metadata and notes
- `attachments/` - Cover images and other media
- `shelves/` - Shelf definitions and book collections

## Usage

- Edit markdown files directly in Obsidian, Logseq, or any text editor
- Changes sync automatically to the web app database
- Use the web app to browse, search, and manage your library

## File Format

Each book is stored as a markdown file with YAML frontmatter:

```markdown
---
title: "Book Title"
author: "Author Name"
isbn13: "9781234567890"
status: "read"
rating: 5
shelves: [Fiction, Favorites]
---

# Review
Your review text here...

# Private Notes
Your private notes here...
```
